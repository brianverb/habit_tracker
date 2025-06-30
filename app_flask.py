from flask import Flask, render_template, request, jsonify, redirect, url_for
from habit_data import add_habit, get_habits, mark_habit, get_agenda, get_monthly_completion
from datetime import datetime
import calendar
import os

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
    year, month = now.year, now.month
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
    return render_template('calendar.html', weeks=weeks)

if __name__ == '__main__':
    app.run(debug=True)
