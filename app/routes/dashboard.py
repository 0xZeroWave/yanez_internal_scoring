from flask import Blueprint, render_template
from dotenv import load_dotenv
import os
import requests

load_dotenv()
dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
def home():
    data = {"latest_scores": []}
    try:
        response = requests.get(
            'http://127.0.0.1:5000/api/yanez/score',
            headers={'X-API-KEY': os.getenv('YANEZ_API_KEY')}
        )
        # Cek jika response sukses dan format json sesuai
        response.raise_for_status()  # <--- ini kuncinya
        data = response.json()
            
    except Exception as e:
        print(f"Can't get data from API, Error: {e}")
    return render_template("dashboard.html", latest_scores=data.get("latest_scores", []))

@dashboard_bp.route('/miner/<string:uid>')
def miner(uid):
    try:
        response = requests.get(
            f'http://127.0.0.1:5000/api/yanez/score?uid={uid}',
            headers={'X-API-KEY': os.getenv('YANEZ_API_KEY')}
        )
        filtered_averages = requests.get(
            f'http://127.0.0.1:5000/api/yanez/avg_score/66',
            headers={'X-API-KEY': os.getenv('YANEZ_API_KEY')}
        )
        response.raise_for_status()
        filtered_averages.raise_for_status()
        data = response.json()
        filtered_averages = filtered_averages.json()
        print(data)
    except Exception as e:
        print(f"Can't get data from API, Error: {e}")
    return render_template(
        'miner_detail.html',
        latest_score_1hr = data.get('latest_score_1hr', 0) or 0,
        latest_score_1hr_created = data.get('latest_score_1hr_created', "-") or "-",
        average_score_latest_1hr = data.get('average_score_latest_1hr', 0) or 0,
        details = data.get('details', []) or [],
        uid = data.get('uid', uid) or uid,
        averages = filtered_averages.get('averages', []) or []
    )