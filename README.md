# Build Up

A full-stack fitness tracking web app built with Flask, SQLite, HTML, CSS, and JavaScript. It includes a premium night theme plus a pastel day theme, and a Coach that supports dumbbell-only, bodyweight, and full-gym training.

## Features
- Account signup/login/logout with hashed passwords and session-based authentication
- Private per-user records
- Workout logging with exercises, sets, reps, weights, duration, notes, and deletion
- Meal tracking for calories, protein, carbs, and fats
- Recovery check-ins for sleep and mood, plus water tracking
- Body-weight history and a Chart.js trend chart
- Goal settings and a fitness Coach with guided fallback responses; optional OpenAI-powered conversation using recent workout activity
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

## Day / night themes
Use the Day mode / Night mode button in the top navigation. Your preference is saved in that browser.

## Enable the AI Coach
The Coach has built-in guidance even without an API key. For conversational AI, create an API key in the OpenAI developer platform and set it in your local terminal (never commit it to GitHub):

```bash
export OPENAI_API_KEY="paste-your-api-key-here"
export OPENAI_MODEL="gpt-4.1-mini"
python app.py
```

Keep the same terminal open while using the app. API usage may incur separate charges; a ChatGPT subscription does not include API credits. Without `OPENAI_API_KEY`, the Coach automatically uses built-in fitness guidance. The Coach cannot watch a workout live and is not a substitute for medical advice.

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
- Real AI replies require your own `OPENAI_API_KEY`; without it, the built-in Coach remains available.
- Calorie and macro entries are user-entered estimates, not medical nutrition advice.
- For production, use HTTPS, a strong secret key, backups, and a persistent database. If the app grows or needs multiple instances, migrate to PostgreSQL.
