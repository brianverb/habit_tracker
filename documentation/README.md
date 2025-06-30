# Habit Tracker (Flask Version)

## Overview
This is a web-based Habit Tracker app built with Python and Flask. It allows you to add, edit, remove, and manage habits, view your agenda, mark habits as done, and interact with an AI assistant for planning and questions. Data is stored per user in their own directory under `user_data/<username>/`.

## Features
- User registration and login (per-user data)
- Add, edit, or remove habits (including start date and schedule)
- View all current habits
- See your agenda for any selected day
- Mark habits as done/not done for a specific day
- Calendar view with color-coded days (green: all done, orange: some done, red: none done)
- **AI Powered Planning & Habit Management:** Add, remove, or change habits using natural language (e.g., "Change my daily meditation to weekly", "Remove reading", "Add daily yoga").
- Chat with an AI assistant about your schedule (uses OpenAI API). All chat history is saved per user and shown in the chatbox, with a button to clear chat history.
- The AI assistant now supports context-dependent actions (e.g., "confirm" after a suggestion, "remove all habits").
- All user data (habits and chat) is now stored in a separate directory for each user under `user_data/<username>/`.

## Requirements
- Python 3.8+
- Flask
- pandas
- openai
- python-dotenv

## Setup Instructions (Local)
1. **Clone or download this repository.**
2. **Create and activate a virtual environment:**
   - Windows:
     ```shell
     python -m venv venv
     venv\Scripts\activate.bat
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
4. **Set your OpenAI API key:**
   - Create a `.env` file in the project root with:
     ```
     OPENAI_API_KEY=your_openai_api_key_here
     FLASK_SECRET_KEY=your_flask_secret_key_here
     ```
5. **Run the app:**
   ```shell
   python app_flask.py
   ```
6. **Open your browser and go to:**
   [http://127.0.0.1:5000/](http://127.0.0.1:5000/)

## Docker Instructions

### 1. Build the Docker image
```sh
docker build -t habit-tracker-ai .
```

### 2. Run the Docker container
```sh
docker run -d -p 5000:5000 --env-file .env -v $(pwd)/user_data:/app/user_data habit-tracker-ai
```
- `--env-file .env` passes your OpenAI and Flask secrets to the container.
- `-v $(pwd)/user_data:/app/user_data` mounts a local folder for persistent user data (create `user_data` if needed).
- On Windows, use `%cd%\user_data:/app/user_data` for the volume path.

### 3. Access the app
Go to [http://localhost:5000/](http://localhost:5000/) in your browser.

### 4. Notes
- All user data and credentials are stored in `/app/user_data` inside the container. This is mapped to your local `user_data` folder for persistence.
- The `.env` file is not included in the image; you must provide it at runtime.
- The container exposes port 5000 by default.

### 5. Dockerfile Environment Variables Explained
- `PYTHONDONTWRITEBYTECODE=1`: Prevents Python from writing `.pyc` files (compiled bytecode) to disk. This keeps the container clean and avoids unnecessary files.
- `PYTHONUNBUFFERED=1`: Forces Python to output logs and print statements immediately (no buffering), so you see real-time logs in `docker logs` and the terminal.

## File Structure
- `app_flask.py` - Main Flask app
- `habit_data.py` - Data logic (per-user habits, agenda, marking)
- `users.json` - User credentials (global, not per-user)
- `user_data/<username>/data.json` - Per-user habit and agenda data (in a separate directory for each user)
- `user_data/<username>/chat.json` - Per-user persistent chat history
- `templates/` - HTML templates for the web interface
- `.env` - Your OpenAI API key and Flask secret (not tracked by git)
- `Dockerfile` - Docker build instructions
- `.dockerignore` - Files/folders excluded from Docker image
- `.gitignore` - Ensures your app code is tracked, but excludes virtual environments, __pycache__, .env, and all .json user data files from git.

## Notes
- All changes and commands are documented in `documentation/changes_and_commands.txt`.
- The app is modular and easy to extend.
