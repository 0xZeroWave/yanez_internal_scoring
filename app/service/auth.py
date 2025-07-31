from flask import request, current_app, jsonify
from functools import wraps
from dotenv import load_dotenv
load_dotenv()
import os

YANEZ_API_KEY = os.getenv('YANEZ_API_KEY')
def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # You can get key from header or query parameter (choose as needed)
        key = request.headers.get('X-API-KEY') or request.args.get('api_key')
        if not key or key != YANEZ_API_KEY:
            return jsonify({'status': False, 'message': 'Invalid or missing API key'}), 401
        return f(*args, **kwargs)
    return decorated