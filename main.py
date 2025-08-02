from flask import Flask
from app.routes.score import service_bp
from app.routes.dashboard import dashboard_bp
from app.model.score import db
from app.utils.scheduler import start_scheduler
import logging

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
)

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///scores.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
with app.app_context():
    db.create_all()

app.register_blueprint(service_bp)
app.register_blueprint(dashboard_bp)

start_scheduler(app)

if __name__ == '__main__':
    app.run(debug=True)
