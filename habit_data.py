import json
import os
from datetime import datetime, timedelta
import calendar

DATA_FILE = "habits_data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"habits": [], "records": {}}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def add_habit(name, schedule, start_date=None):
    data = load_data()
    if any(h["name"] == name for h in data["habits"]):
        return False
    habit = {"name": name, "schedule": schedule}
    if start_date:
        habit["start_date"] = start_date
    else:
        habit["start_date"] = datetime.now().strftime("%Y-%m-%d")
    data["habits"].append(habit)
    save_data(data)
    return True

def get_habits():
    data = load_data()
    return data["habits"]

def mark_habit(habit_name, date, done):
    data = load_data()
    if habit_name not in data["records"]:
        data["records"][habit_name] = {}
    data["records"][habit_name][date] = done
    save_data(data)
    return True

def get_agenda(selected_date):
    data = load_data()
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

def get_monthly_completion(year, month):
    data = load_data()
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
