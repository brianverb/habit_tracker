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
    """Return the username of the currently logged-in user from the session, or None if not logged in."""
    return session.get('username')

def get_user_data_path(username):
    """Return the path to the user's data.json file."""
    return f"user_data/{username}/data.json"

def get_user_chat_path(username):
    """Return the path to the user's chat.json file, creating the directory if needed."""
    user_dir = f"user_data/{username}"
    os.makedirs(user_dir, exist_ok=True)
    return f"{user_dir}/chat.json"

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
    """API endpoint to mark a habit as done or not done for a specific date."""
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
    """API endpoint to edit an existing habit's details."""
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
    """API endpoint to remove a habit for the current user."""
    if not get_current_user():
        return jsonify({'success': False, 'error': 'Not logged in'})
    data = request.get_json()
    name = data['habit']
    remove_habit(name, username=get_current_user())
    return jsonify({'success': True})

@app.route('/clear_chat_history', methods=['POST'])
def clear_chat_history():
    """API endpoint to clear the current user's chat history."""
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
    """API endpoint to get the current user's habits as JSON."""
    if not get_current_user():
        return jsonify({'habits': []})
    return jsonify({'habits': get_habits(get_current_user())})

@app.route('/get_chat_history', methods=['GET'])
def get_chat_history():
    """API endpoint to get the current user's chat history as JSON."""
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
    """AI endpoint: Handles user chat, returns AI response, and applies extracted habit actions (add, edit, remove, remove_all)."""
    if not get_current_user():
        return jsonify({'success': False, 'status': 'Not logged in'})
    user_message = request.json['message']
    username = get_current_user()
    openai_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    user_habits = get_habits(username)
    habits_json = json.dumps(user_habits, indent=2)
    chat_path = get_user_chat_path(username)
    # Load chat history
    if os.path.exists(chat_path):
        try:
            with open(chat_path, 'r') as f:
                chat_history = json.load(f)
        except Exception:
            chat_history = []
    else:
        chat_history = []
    # Add the new user message to chat history
    chat_history.append({"sender": "user", "text": user_message})
    # Build OpenAI messages from chat history
    messages = [{"role": "system", "content": "You are a helpful assistant for a habit tracker app."}]
    for msg in chat_history:
        if msg["sender"] == "user":
            messages.append({"role": "user", "content": msg["text"]})
        elif msg["sender"] == "ai":
            messages.append({"role": "assistant", "content": msg["text"]})
    # Add context about habits
    messages.append({"role": "system", "content": f"Here is the user's current habit data (in JSON):\n{habits_json}"})

    # 1. Main assistant: respond conversationally with full context
    chat_response = openai_client.chat.completions.create(
        model="gpt-4.1-nano-2025-04-14",
        messages=messages
    )
    answer = chat_response.choices[0].message.content
    chat_history.append({"sender": "ai", "text": answer})

    # 2. Action extraction assistant: extract and apply actions from the full chat history
    # Forward the entire chat history and habits to the extractor
    extractor_prompt = (
        "You are an expert at extracting structured actions from a chat history. "
        "Given the following chat history and the user's current habits, extract a JSON array of actions to add, edit, remove, or remove all habits. "
        "Each action must be an object with fields: action (add, remove, edit, or remove_all), name, schedule, start_date, old_name (if editing). "
        "For a 'remove_all' action, only the action field is required. Respond ONLY with a JSON array, no explanations, no markdown, no extra text. "
        "If the user requests to remove all habits, output: [ {\"action\": \"remove_all\"} ]\n"
        "If the user confirms, asks you to choose, or refers to a previous suggestion, infer the habits to add from the previous assistant messages and extract them as add actions. "
        "If you can't extract any actions, respond with an empty array: [].\n"
        "Chat history (JSON):\n" + json.dumps(chat_history, indent=2) + "\n"
        "Current habits (JSON):\n" + habits_json + "\n"
    )
    extractor_response = openai_client.chat.completions.create(
        model="gpt-4.1-nano-2025-04-14",
        messages=[{"role": "system", "content": "You extract structured actions from chat history."},
                  {"role": "user", "content": extractor_prompt}]
    )
    raw = extractor_response.choices[0].message.content
    try:
        actions = json.loads(raw)
    except Exception:
        actions = []
    from habit_data import add_habit, edit_habit, remove_habit
    results = []
    for action_obj in actions if isinstance(actions, list) else []:
        action = action_obj.get("action")
        name = action_obj.get("name")
        schedule = action_obj.get("schedule")
        start_date = action_obj.get("start_date")
        old_name = action_obj.get("old_name")
        if action == "remove_all":
            # Remove all habits for the user
            from habit_data import save_data
            save_data({"habits": [], "records": {}}, username=username)
            results.append("All habits have been removed.")
        elif action == "remove" and name:
            match = next((h["name"] for h in user_habits if h["name"].lower() == name.lower()), None)
            if match:
                remove_habit(match, username=username)
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
                edit_habit(match, new_name, new_schedule, new_start_date, username=username)
                results.append(f"Habit '{match}' updated.")
            else:
                results.append(f"No habit found matching '{old_name}' for editing.")
        elif action == "add" and name and schedule:
            add_habit(name, schedule, start_date, username=username)
            results.append(f"Habit '{name}' added with schedule '{schedule}'.")

    # If no actions were extracted but the last AI message was a confirmation, try to parse the previous AI suggestion for habits
    if not results and len(chat_history) > 2:
        last_ai = chat_history[-2]["text"].lower()
        if any(word in last_ai for word in ["added", "set up", "successfully added"]):
            # Try to parse the previous AI suggestion for habits
            import re
            habit_lines = re.findall(r"\d+\.\s*([A-Za-z0-9\s\-]+)[—-](.*)", chat_history[-3]["text"])
            for habit in habit_lines:
                name = habit[0].strip()
                desc = habit[1].strip()
                if name and desc:
                    add_habit(name, "Daily", None, username=username)
                    results.append(f"Habit '{name}' added with schedule 'Daily'.")
    # If any actions were performed, add a summary message to chat history
    if results:
        ai_msg = "<br>".join(results)
        chat_history.append({"sender": "ai", "text": ai_msg})
    # Save chat history
    threading.Thread(target=lambda: save_chat_history(chat_path, chat_history)).start()
    # Return both the main answer and any action summary
    return jsonify({"success": True, "response": answer + ("<br>" + ai_msg if results else "")})

def save_chat_history(chat_path, chat_history):
    """Save the last 100 chat messages to the user's chat file."""
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
        # Ensure users.json exists
        if not os.path.exists('users.json'):
            with open('users.json', 'w') as f:
                json.dump([], f)
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
        # Ensure users.json exists
        if not os.path.exists('users.json'):
            with open('users.json', 'w') as f:
                json.dump([], f)
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
