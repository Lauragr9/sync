# Sync — Group Travel Planner

A Django web app for planning group trips. Members propose destinations, vote, set availability, and the trip lead confirms a destination and generates an AI-powered day-by-day itinerary.

## Features

- Create trips and invite members via a shareable link
- Propose and vote on destinations (Yes / Maybe / No)
- Availability calendar — see who can make each date
- AI itinerary generation per destination (powered by Groq / LLaMA 3.3)
- Confirm a destination and export the itinerary as a PDF
- Bootstrap 5 UI

## Requirements

- Python 3.12+
- A free [Groq API key](https://console.groq.com) for AI itinerary generation

## Setup

### 1. Clone the repo

```bash
git clone <repo-url>
cd sync
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements/base.txt
```

### 4. Set up the environment

Create a `.env` file in the project root:

```
GROQ_API_KEY=your_groq_api_key_here
SECRET_KEY=any-random-string-for-local-dev
```

The app uses `python-dotenv` to load this automatically.

> AI itinerary generation will silently fail without a valid `GROQ_API_KEY` — all other features work without it.

### 5. Apply migrations

```bash
python manage.py migrate
```

### 6. Create a superuser (optional)

```bash
python manage.py createsuperuser
```

### 7. Run the development server

```bash
python manage.py runserver
```

Visit [http://127.0.0.1:8000](http://127.0.0.1:8000) and sign up for an account.

## Usage walkthrough

1. **Sign up** and create a trip
2. **Share the invite link** with friends so they can join
3. **Propose destinations** — each member can add cities with notes
4. **Vote** on proposals (Yes / Maybe / No)
5. **Set availability** on the calendar grid
6. **Generate itinerary** — the trip lead clicks "Generate with AI" on any destination tab
7. **Confirm destination** — the lead clicks "Confirm ✓" on the winning proposal
8. **Download PDF** — export the itinerary for any destination

## Project structure

```
sync/               Django app (models, views, forms, urls)
templates/          HTML templates
config/             Django project settings and root URLs
requirements/       Python dependencies
manage.py           Django management script
```

## Notes

- The database is SQLite (`db.sqlite3`) — no additional database setup required
- WeasyPrint is used for PDF export and requires system-level dependencies on some platforms — see the [WeasyPrint docs](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation) if PDF export fails
