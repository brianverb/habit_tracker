# Dockerfile for Flask Habit Tracker with AI Planning
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy project files
COPY ./app ./app
COPY .env .

# Expose port
EXPOSE 5000

# Entrypoint
CMD ["python", "app/app_flask.py"]
