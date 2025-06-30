from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from habit_data import add_habit, get_habits, mark_habit, get_agenda, get_monthly_completion, edit_habit, remove_habit
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

@app.route('/chat', methods=['POST'])
def chat():
    if not get_current_user():
        return jsonify({'response': 'Not logged in'})
    user_message = request.json['message']
    user_data_path = get_user_data_path(get_current_user())
    if not os.path.exists(user_data_path):
        habits_data = '{}'
    else:
        with open(user_data_path, 'r') as f:
            habits_data = f.read()
    prompt = f"""
You are a helpful assistant for a habit tracker app. The user will ask questions about their schedule. Here is their current habit data (in JSON):
{habits_data}

User question: {user_message}
"""
    client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-nano-2025-04-14",
            messages=[{"role": "system", "content": "You are a helpful assistant for a habit tracker app."},
                      {"role": "user", "content": prompt}]
        )
        answer = response.choices[0].message.content
    except Exception as e:
        answer = f"Error: {e}"
    return jsonify({'response': answer})

@app.route('/smart_add', methods=['POST'])
def smart_add():
    if not get_current_user():
        return jsonify({'success': False, 'status': 'Not logged in'})
    user_message = request.json['message']
    openai_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    prompt = (
        "You are a helpful assistant for a habit tracker app. "
        "The user may want to add or remove a habit. "
        "If the user wants to add a habit, extract the habit name (as exactly stored), schedule (Daily, Weekly, Bi-daily, Bi-weekly, Monthly), and start date (YYYY-MM-DD, optional). "
        "If the user wants to remove a habit, extract the habit name (as exactly stored) and set action to 'remove'. "
        "Always include the action field as either 'add' or 'remove'. "
        "Respond in JSON: {\"action\": \"add\" or \"remove\", \"name\":..., \"schedule\":..., \"start_date\":...}. "
        "If you can't extract, respond with an empty JSON.\n"
        f"Message: {user_message}"
    )
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4.1-nano-2025-04-14",
            messages=[{"role": "system", "content": "You are a helpful assistant for a habit tracker app."},
                      {"role": "user", "content": prompt}]
        )
        content = response.choices[0].message.content
        data = json.loads(content)
        action = data.get("action", "add")
        name = data.get("name")
        schedule = data.get("schedule")
        start_date = data.get("start_date")
        print(f"[SMART_ADD DEBUG] action: {action}, name: {name}, schedule: {schedule}, start_date: {start_date}")
        # Fuzzy/case-insensitive match for removal
        if action == "remove" and name:
            user_habits = get_habits(get_current_user())
            match = next((h["name"] for h in user_habits if h["name"].lower() == name.lower()), None)
            if match:
                remove_habit(match, username=get_current_user())
                return jsonify({"success": True, "status": f"Habit '{match}' removed."})
            else:
                return jsonify({"success": False, "status": f"No habit found matching '{name}' for removal."})
        elif action == "add" and name and schedule:
            add_habit(name, schedule, start_date, username=get_current_user())
            return jsonify({"success": True, "status": f"Habit '{name}' added with schedule '{schedule}'."})
        else:
            return jsonify({"success": False, "status": "Could not extract habit details from your message."})
    except Exception as e:
        return jsonify({"success": False, "status": f"Error: {e}"})

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
