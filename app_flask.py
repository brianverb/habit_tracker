from flask import Flask, render_template, request, jsonify, redirect, url_for
from habit_data import add_habit, get_habits, mark_habit, get_agenda, get_monthly_completion, edit_habit, remove_habit
from datetime import datetime
import calendar
import os
import json
import openai
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

@app.route('/')
def index():
    habits = get_habits()
    default_start_date = datetime.now().strftime('%Y-%m-%d')
    return render_template('index.html', habits=habits, default_start_date=default_start_date)

@app.route('/add_habit', methods=['POST'])
def add_habit_route():
    name = request.form['name']
    schedule = request.form['schedule']
    start_date = request.form.get('start_date')
    if not name or not schedule:
        return redirect(url_for('index'))
    add_habit(name, schedule, start_date)
    return redirect(url_for('index'))

@app.route('/agenda')
def agenda():
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    agenda = get_agenda(date)
    return render_template('agenda.html', agenda=agenda, date=date)

@app.route('/mark', methods=['POST'])
def mark():
    habit = request.json['habit']
    date = request.json['date']
    done = request.json['done']
    mark_habit(habit, date, done)
    return jsonify({'success': True})

@app.route('/calendar')
def calendar_view():
    now = datetime.now()
    year = int(request.args.get('year', now.year))
    month = int(request.args.get('month', now.month))
    days = get_monthly_completion(year, month)
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
    data = request.get_json()
    old_name = data['oldName']
    name = data['name']
    schedule = data['schedule']
    start_date = data['start_date']
    edit_habit(old_name, name, schedule, start_date)
    return jsonify({'success': True})

@app.route('/remove_habit', methods=['POST'])
def remove_habit_route():
    data = request.get_json()
    name = data['habit']
    remove_habit(name)
    return jsonify({'success': True})

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json['message']
    with open('habits_data.json', 'r') as f:
        habits_data = f.read()
    prompt = f"""
You are a helpful assistant for a habit tracker app. The user will ask questions about their schedule. Here is their current habit data (in JSON):
{habits_data}

User question: {user_message}
"""
    client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "You are a helpful assistant for a habit tracker app."},
                      {"role": "user", "content": prompt}]
        )
        answer = response.choices[0].message.content
    except Exception as e:
        answer = f"Error: {e}"
    return jsonify({'response': answer})

if __name__ == '__main__':
    app.run(debug=True)
