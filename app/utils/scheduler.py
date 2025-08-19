from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta, timezone
from app.model.score import db, UserUID, ScoreSession, AverageScore


def store_hourly_average_for_all_users():
    """Aggregate the last hour's scores for each user and store the average."""
    print(f"Running scheduled job at {datetime.now(timezone.utc)}")
    now = datetime.now(timezone.utc)
    one_hour_ago = now - timedelta(hours=1)

    users = UserUID.query.all()
    for user in users:
        sessions = ScoreSession.query.filter(
            ScoreSession.user_id == user.id,
            ScoreSession.created_at >= one_hour_ago,
            ScoreSession.created_at <= now,
        ).all()

        if not sessions:
            continue

        avg_score = sum(s.avg_final_score for s in sessions) / len(sessions)
        avg_record = AverageScore(
            score=avg_score,
            timestamp=now,
            user_id=user.id,
        )
        db.session.add(avg_record)

    db.session.commit()
    print("Average scores stored.")


def start_scheduler(app):
    """Start background scheduler to store hourly averages."""
    scheduler = BackgroundScheduler()

    def job():
        # Ensure the job runs within the application context so that
        # database operations work correctly.
        with app.app_context():
            store_hourly_average_for_all_users()

    scheduler.add_job(
        func=job,
        trigger="cron",
        minute=12,  # Only at minute 12 each hour
    )
    scheduler.start()
    print("Scheduler was started")
