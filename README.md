# Build Up

A full-stack fitness tracking web app built with Flask, SQLite, HTML, CSS, and JavaScript. The interface follows a minimal, premium black-and-white design with restrained red accents.

## Features
- Account signup/login/logout with hashed passwords and session-based authentication
- Private per-user records
- Workout logging with exercises, sets, reps, weights, duration, notes, and deletion
- Meal tracking for calories, protein, carbs, and fats
- Recovery check-ins for sleep and mood, plus water tracking
- Body-weight history and a Chart.js trend chart
- Goal settings and a rules-based coach that uses logged activity
- Responsive layout and a health-check endpoint (`/health`)

## Run locally (macOS)
1. Install Python 3.11 or newer.
2. Open Terminal in this folder.
3. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
4. Install packages and start the app:
   ```bash
   pip install -r requirements.txt
   python app.py
   ```
5. Open http://127.0.0.1:5000

The database is created automatically at `database/build_up.db`. Set a custom `SECRET_KEY` in your environment for anything beyond local testing.

## Deploy on Render
This repository includes `render.yaml` for a Render web service and a persistent disk. Push the project to a GitHub repository, then in Render choose **New + → Blueprint** and select that repository. Confirm the service and disk settings before deploying. The persistent disk prevents SQLite data from disappearing on normal redeploys; keep in mind a single SQLite database is best suited to a small, single-instance app.

## GitHub
Create a new empty repository on GitHub. In this project folder:
```bash
git init
git add .
git commit -m "Build Up functional fitness app"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
git push -u origin main
```
Replace the URL with your own repository URL. Do not commit `.env`, passwords, API keys, or the live database.

## Important
- The Coach page currently gives rules-based guidance and does not call a paid AI API.
- Calorie and macro entries are user-entered estimates, not medical nutrition advice.
- For production, use HTTPS, a strong secret key, backups, and a persistent database. If the app grows or needs multiple instances, migrate to PostgreSQL.
