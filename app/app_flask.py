from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from habit_data import add_habit, get_habits, mark_habit, get_agenda, get_monthly_completion, edit_habit, remove_habit
import threading
from datetime import datetime
import calendar
import os
import json
import openai
from dotenv import load_dotenv
import hashlib

load_dotenv()

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev_secret')

def get_current_user():
    return session.get('username')

def get_user_data_path(username):
    return f"user_data_{username}.json"

def get_user_chat_path(username):
    return f"user_data_{username}_chat.json"

@app.route('/')
def index():
    if not get_current_user():
        return redirect(url_for('login'))
    habits = get_habits(get_current_user())
    default_start_date = datetime.now().strftime('%Y-%m-%d')
    return render_template('index.html', habits=habits, default_start_date=default_start_date, username=get_current_user())

@app.route('/add_habit', methods=['POST'])
def add_habit_route():
    if not get_current_user():
        return redirect(url_for('login'))
    name = request.form['name']
    schedule = request.form['schedule']
    start_date = request.form.get('start_date')
    if not name or not schedule:
        return redirect(url_for('index'))
    add_habit(name, schedule, start_date, username=get_current_user())
    return redirect(url_for('index'))

@app.route('/agenda')
def agenda():
    if not get_current_user():
        return redirect(url_for('login'))
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    agenda = get_agenda(date, username=get_current_user())
    return render_template('agenda.html', agenda=agenda, date=date)

@app.route('/mark', methods=['POST'])
def mark():
    if not get_current_user():
        return jsonify({'success': False, 'error': 'Not logged in'})
    habit = request.json['habit']
    date = request.json['date']
    done = request.json['done']
    mark_habit(habit, date, done, username=get_current_user())
    return jsonify({'success': True})

@app.route('/calendar')
def calendar_view():
    if not get_current_user():
        return redirect(url_for('login'))
    now = datetime.now()
    year = int(request.args.get('year', now.year))
    month = int(request.args.get('month', now.month))
    days = get_monthly_completion(year, month, username=get_current_user())
    # Arrange days into weeks for calendar display
    first_weekday, num_days = calendar.monthrange(year, month)
    weeks = []
    week = [None]*first_weekday
    for d in days:
        week.append(d)
        if len(week) == 7:
            weeks.append(week)
            week = []
    if week:
        while len(week) < 7:
            week.append(None)
        weeks.append(week)
    # Month navigation
    prev_month = month - 1
    next_month = month + 1
    prev_year = year
    next_year = year
    if prev_month < 1:
        prev_month = 12
        prev_year -= 1
    if next_month > 12:
        next_month = 1
        next_year += 1
    month_name = calendar.month_name[month]
    return render_template('calendar.html', weeks=weeks, year=year, month=month, month_name=month_name,
                           prev_month=prev_month, next_month=next_month, prev_year=prev_year, next_year=next_year)

@app.route('/edit_habit', methods=['POST'])
def edit_habit_route():
    if not get_current_user():
        return jsonify({'success': False, 'error': 'Not logged in'})
    data = request.get_json()
    old_name = data['oldName']
    name = data['name']
    schedule = data['schedule']
    start_date = data['start_date']
    edit_habit(old_name, name, schedule, start_date, username=get_current_user())
    return jsonify({'success': True})

@app.route('/remove_habit', methods=['POST'])
def remove_habit_route():
    if not get_current_user():
        return jsonify({'success': False, 'error': 'Not logged in'})
    data = request.get_json()
    name = data['habit']
    remove_habit(name, username=get_current_user())
    return jsonify({'success': True})


@app.route('/clear_chat_history', methods=['POST'])
def clear_chat_history():
    if not get_current_user():
        return jsonify({'success': False})
    chat_path = get_user_chat_path(get_current_user())
    try:
        with open(chat_path, 'w') as f:
            json.dump([], f)
        return jsonify({'success': True})
    except Exception:
        return jsonify({'success': False})

@app.route('/get_habits', methods=['GET'])
def get_habits_api():
    if not get_current_user():
        return jsonify({'habits': []})
    return jsonify({'habits': get_habits(get_current_user())})

@app.route('/get_chat_history', methods=['GET'])
def get_chat_history():
    if not get_current_user():
        return jsonify({'history': []})
    chat_path = get_user_chat_path(get_current_user())
    if not os.path.exists(chat_path):
        return jsonify({'history': []})
    with open(chat_path, 'r') as f:
        try:
            history = json.load(f)
        except Exception:
            history = []
    return jsonify({'history': history})

@app.route('/ai_planning', methods=['POST'])
def ai_planning():
    if not get_current_user():
        return jsonify({'success': False, 'status': 'Not logged in'})
    user_message = request.json['message']
    openai_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    user_habits = get_habits(get_current_user())
    habits_json = json.dumps(user_habits, indent=2)
    chat_path = get_user_chat_path(get_current_user())
    # Load chat history
    if os.path.exists(chat_path):
        try:
            with open(chat_path, 'r') as f:
                chat_history = json.load(f)
        except Exception:
            chat_history = []
    else:
        chat_history = []
    # Try to parse as planning first, fallback to chat if not actionable
    planning_prompt = (
        "You are a helpful assistant for a habit tracker app. "
        "The user may want to add, remove, or change (edit) one or more habits in a single message. "
        "Here is a list of the user's current habits (in JSON):\n" + habits_json + "\n"
        "For each action, extract: action (add, remove, or edit), name, schedule, start_date, and old_name (for edits). "
        "Return a JSON array: [{\"action\":..., \"name\":..., \"schedule\":..., \"start_date\":..., \"old_name\":...}, ...]. "
        "If you can't extract any, respond with an empty array.\n"
        f"Message: {user_message}"
    )
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4.1-nano-2025-04-14",
            messages=[{"role": "system", "content": "You are a helpful assistant for a habit tracker app."},
                      {"role": "user", "content": planning_prompt}]
        )
        content = response.choices[0].message.content
        try:
            data = json.loads(content)
        except Exception:
            data = {}
        user_habits = get_habits(get_current_user())
        chat_history.append({"sender": "user", "text": user_message})
        # If data is a list, process multiple actions
        if isinstance(data, list):
            results = []
            for action_obj in data:
                action = action_obj.get("action")
                name = action_obj.get("name")
                schedule = action_obj.get("schedule")
                start_date = action_obj.get("start_date")
                old_name = action_obj.get("old_name")
                if action == "remove" and name:
                    match = next((h["name"] for h in user_habits if h["name"].lower() == name.lower()), None)
                    if match:
                        remove_habit(match, username=get_current_user())
                        results.append(f"Habit '{match}' removed.")
                    else:
                        results.append(f"No habit found matching '{name}' for removal.")
                elif action == "edit" and old_name:
                    match = next((h["name"] for h in user_habits if h["name"].lower() == old_name.lower()), None)
                    if match:
                        habit = next(h for h in user_habits if h["name"] == match)
                        new_name = name if name else habit["name"]
                        new_schedule = schedule if schedule else habit["schedule"]
                        new_start_date = start_date if start_date else habit.get("start_date")
                        edit_habit(match, new_name, new_schedule, new_start_date, username=get_current_user())
                        results.append(f"Habit '{match}' updated.")
                    else:
                        results.append(f"No habit found matching '{old_name}' for editing.")
                elif action == "add" and name and schedule:
                    add_habit(name, schedule, start_date, username=get_current_user())
                    results.append(f"Habit '{name}' added with schedule '{schedule}'.")
            if results:
                ai_msg = "<br>".join(results)
                chat_history.append({"sender": "ai", "text": ai_msg})
                threading.Thread(target=lambda: save_chat_history(chat_path, chat_history)).start()
                return jsonify({"success": True, "status": ai_msg})
        # If not a planning action, treat as chat
        else:
            user_data_path = get_user_data_path(get_current_user())
            if not os.path.exists(user_data_path):
                habits_data = '{}'
            else:
                with open(user_data_path, 'r') as f:
                    habits_data = f.read()
            chat_prompt = f"""
You are a helpful assistant for a habit tracker app. The user will ask questions about their schedule. Here is their current habit data (in JSON):
{habits_data}

User question: {user_message}
"""
            chat_response = openai_client.chat.completions.create(
                model="gpt-4.1-nano-2025-04-14",
                messages=[{"role": "system", "content": "You are a helpful assistant for a habit tracker app."},
                          {"role": "user", "content": chat_prompt}]
            )
            answer = chat_response.choices[0].message.content
            chat_history.append({"sender": "user", "text": user_message})
            chat_history.append({"sender": "ai", "text": answer})
            threading.Thread(target=lambda: save_chat_history(chat_path, chat_history)).start()
            return jsonify({"success": True, "response": answer})
    except Exception as e:
        return jsonify({"success": False, "status": f"Error: {e}"})

def save_chat_history(chat_path, chat_history):
    try:
        with open(chat_path, 'w') as f:
            json.dump(chat_history[-100:], f, indent=2)  # Keep last 100 messages
    except Exception:
        pass

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with open('users.json', 'r+') as f:
            users = json.load(f)
            if any(u['username'] == username for u in users):
                return render_template('register.html', error='Username already exists')
            hashed = hashlib.sha256(password.encode()).hexdigest()
            users.append({'username': username, 'password': hashed})
            f.seek(0)
            json.dump(users, f)
            f.truncate()
        session['username'] = username
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with open('users.json', 'r') as f:
            users = json.load(f)
            hashed = hashlib.sha256(password.encode()).hexdigest()
            user = next((u for u in users if u['username'] == username and u['password'] == hashed), None)
            if user:
                session['username'] = username
                return redirect(url_for('index'))
            else:
                return render_template('login.html', error='Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
