# Yanez Internal Scoring

Yanez Internal Scoring is a Flask-based service for evaluating and storing name variation scores. It exposes RESTful APIs for submitting scores, retrieving historical data, and modifying name variations. A minimal dashboard lets you inspect miner activity, while a background scheduler aggregates hourly averages for long-term monitoring.

## Features

- **Score submission API** – send name variation results and receive computed metrics.
- **Historical queries** – fetch recent scores, averages over the last hour, and full session details.
- **Variation modifier** – adjust generated variations to match configuration rules without scoring them.
- **Dashboard UI** – view the latest scores per miner and drill down into individual histories.
- **Scheduled aggregation** – an APScheduler job stores hourly average scores for each user.

## Project Structure

```
├── app
│   ├── model          # SQLAlchemy models
│   ├── routes         # API and dashboard blueprints
│   ├── service        # Scoring logic and authentication helpers
│   └── utils          # Scheduler and scoring utilities
├── templates          # HTML templates for the dashboard
├── main.py            # Application entry point
└── requirement.txt    # Python dependencies
```

## Requirements

- Python 3.10+
- [Flask](https://flask.palletsprojects.com/)
- [Flask-SQLAlchemy](https://flask-sqlalchemy.palletsprojects.com/)
- Additional packages listed in `requirement.txt`

## Setup

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd yanez_internal_scoring
   ```
2. **Create and activate a virtual environment** (optional but recommended)
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3. **Install dependencies**
   ```bash
   pip install -r requirement.txt
   ```
4. **Configure environment variables**
   - Create a `.env` file with your API key:
     ```
     YANEZ_API_KEY=<your_key>
     ```

## Running the Application

Start the development server:
```bash
python main.py
```
The API will be available at `http://127.0.0.1:5000/api/` and the dashboard at `http://127.0.0.1:5000/`.

## API Overview

| Method | Endpoint                        | Description |
|--------|---------------------------------|-------------|
| POST   | `/api/yanez/score`              | Submit name variation results and compute scores |
| GET    | `/api/yanez/score`              | Retrieve latest scores or full history for a user |
| POST   | `/api/yanez/modify_variations`  | Normalize variation outputs based on configuration |
| GET    | `/api/yanez/avg_score/<uid>`    | Get hourly average scores for the last 48 hours |

Each request must include `X-API-KEY` header with the value set in your `.env` file.

## Database

The service uses SQLite (`scores.db`) by default. Tables are automatically created on startup using SQLAlchemy models defined in `app/model/score.py`.

## Background Scheduler

A background task stores hourly average scores for all users using APScheduler. It runs within the Flask app context and persists data to the database.

## License

This project is provided for internal use. No specific license has been defined.

