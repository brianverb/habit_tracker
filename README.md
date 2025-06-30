# Habit Tracker (Flask Version)

## Overview
This is a web-based Habit Tracker app built with Python and Flask. It allows you to add habits, view your daily/weekly agenda, and mark habits as done or not done. Data is stored locally in a JSON file.

## Features
- Add new habits with custom schedules (Daily, Bi-daily, Weekly, Bi-weekly, Monthly)
- View all current habits
- See your agenda for any selected day
- Mark habits as done/not done for a specific day

## Requirements
- Python 3.8+
- Flask
- pandas

## Setup Instructions
1. **Clone or download this repository.**
2. **Create and activate a virtual environment:**
   - Windows:
     ```shell
     python -m venv venv
     venv\Scripts\activate
     ```
   - Linux/Mac:
     ```shell
     python3 -m venv venv
     source venv/bin/activate
     ```
3. **Install dependencies:**
   ```shell
   pip install -r requirements.txt
   ```
4. **Run the app:**
   ```shell
   python app_flask.py
   ```
5. **Open your browser and go to:**
   [http://127.0.0.1:5000/](http://127.0.0.1:5000/)

## File Structure
- `app_flask.py` - Main Flask app
- `habit_data.py` - Data logic (load/save habits, agenda, marking)
- `habits_data.json` - Data storage
- `templates/` - HTML templates for the web interface

## Notes
- All changes and commands are documented in `remake_plan.txt`.
- The app is modular and easy to extend.
