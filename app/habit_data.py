import json
import os
from datetime import datetime, timedelta
import calendar

# Helper to get user-specific data file

import os

def get_data_file(username=None):
    """Return the path to the user's data file, creating the directory if needed. Defaults to global data if username is None."""
    if username:
        user_dir = f"user_data/{username}"
        os.makedirs(user_dir, exist_ok=True)
        return f"{user_dir}/data.json"
    return "habits_data.json"

def load_data(username=None):
    """Load habit and record data for the given user. Returns default structure if file does not exist."""
    data_file = get_data_file(username)
    if not os.path.exists(data_file):
        return {"habits": [], "records": {}}
    with open(data_file, "r") as f:
        return json.load(f)

def save_data(data, username=None):
    """Save the given data dict to the user's data file."""
    data_file = get_data_file(username)
    with open(data_file, "w") as f:
        json.dump(data, f, indent=2)

def add_habit(name, schedule, start_date=None, username=None):
    """Add a new habit for the user. Returns False if a habit with the same name exists."""
    data = load_data(username)
    if any(h["name"] == name for h in data["habits"]):
        return False
    habit = {"name": name, "schedule": schedule}
    if start_date:
        habit["start_date"] = start_date
    else:
        habit["start_date"] = datetime.now().strftime("%Y-%m-%d")
    data["habits"].append(habit)
    save_data(data, username)
    return True

def edit_habit(old_name, name, schedule, start_date, username=None):
    """Edit an existing habit's details. Updates records if the name changes."""
    data = load_data(username)
    for habit in data["habits"]:
        if habit["name"] == old_name:
            habit["name"] = name
            habit["schedule"] = schedule
            habit["start_date"] = start_date
            break
    # Also update records if name changed
    if old_name != name and old_name in data["records"]:
        data["records"][name] = data["records"].pop(old_name)
    save_data(data, username)
    return True

def remove_habit(name, username=None):
    """Remove a habit and its records for the user."""
    data = load_data(username)
    data["habits"] = [h for h in data["habits"] if h["name"] != name]
    if name in data["records"]:
        del data["records"][name]
    save_data(data, username)
    return True

def get_habits(username=None):
    """Return the list of habits for the user."""
    data = load_data(username)
    return data["habits"]

def mark_habit(habit_name, date, done, username=None):
    """Mark a habit as done or not done for a specific date."""
    data = load_data(username)
    if habit_name not in data["records"]:
        data["records"][habit_name] = {}
    data["records"][habit_name][date] = done
    save_data(data, username)
    return True

def get_agenda(selected_date, username=None):
    """Return a list of (habit, done) tuples for the selected date, based on each habit's schedule and start date."""
    data = load_data(username)
    habits = data["habits"]
    records = data["records"]
    agenda = []
    sel_date = datetime.strptime(selected_date, "%Y-%m-%d")
    for habit in habits:
        name = habit["name"]
        schedule = habit["schedule"]
        start_date = habit.get("start_date", datetime.now().strftime("%Y-%m-%d"))
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        show = False
        if sel_date >= start_dt:
            if schedule == "Daily":
                show = True
            elif schedule == "Bi-daily":
                show = (sel_date - start_dt).days % 2 == 0
            elif schedule == "Weekly":
                show = (sel_date - start_dt).days % 7 == 0
            elif schedule == "Bi-weekly":
                show = (sel_date - start_dt).days % 14 == 0
            elif schedule == "Monthly":
                show = sel_date.day == start_dt.day
        if show:
            done = records.get(name, {}).get(selected_date, False)
            agenda.append((name, done))
    return agenda

def get_monthly_completion(year, month, username=None):
    """Return a list of dicts for each day in the month, indicating completion color for the user's habits."""
    data = load_data(username)
    habits = data["habits"]
    records = data["records"]
    month_days = calendar.monthrange(year, month)[1]
    result = []
    for day in range(1, month_days+1):
        date_str = f"{year:04d}-{month:02d}-{day:02d}"
        agenda = []
        for habit in habits:
            name = habit["name"]
            schedule = habit["schedule"]
            start_date = habit.get("start_date", datetime.now().strftime("%Y-%m-%d"))
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            sel_date = datetime(year, month, day)
            show = False
            if sel_date >= start_dt:
                if schedule == "Daily":
                    show = True
                elif schedule == "Bi-daily":
                    show = (sel_date - start_dt).days % 2 == 0
                elif schedule == "Weekly":
                    show = (sel_date - start_dt).days % 7 == 0
                elif schedule == "Bi-weekly":
                    show = (sel_date - start_dt).days % 14 == 0
                elif schedule == "Monthly":
                    show = sel_date.day == start_dt.day
            if show:
                done = records.get(name, {}).get(date_str, False)
                agenda.append(done)
        if not agenda:
            color = 'gray'  # No tasks for this day
        elif all(agenda):
            color = 'green'
        elif any(agenda):
            color = 'orange'
        else:
            color = 'red'
        result.append({"day": day, "color": color})
    return result
