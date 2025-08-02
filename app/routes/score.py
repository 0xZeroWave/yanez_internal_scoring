import logging
from flask import Blueprint, jsonify, request
from app.service.cal_score import calculate_variation_scores
from app.model.score import db, ScoreSession, NameScore, VariationScore, UserUID, AverageScore
import numpy as np
from datetime import datetime, timezone, timedelta
from app.service.auth import require_api_key

# Setup logging config
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s')
log = logging.getLogger(__name__)

service_bp = Blueprint('service', __name__, url_prefix='/api')

@service_bp.route('/yanez/score', methods=['POST'])
@require_api_key
def input_score():
    log.info("POST /yanez/score accessed")
    try:
        data = request.json
        uid = data.get('uid', 0)
        variation_config = data.get('variation_config', {})
        variation_result = data.get('variation_result', {})
        log.info(f"Received score submission from UID: {uid}")
        user = UserUID.query.filter_by(uid=uid).first()
        if not user:
            user = UserUID(uid=uid)
            db.session.add(user)
            db.session.flush()
            log.info(f"Created new UserUID for uid: {uid}")
        variations_scores = calculate_variation_scores(variation_result, variation_config)
        session = ScoreSession(user_id=user.id, avg_final_score=variations_scores['average_final_score'])
        db.session.add(session)
        db.session.flush()
        for name, scores_detail in variations_scores['scores_data'].items():
            name_score = NameScore(name=name, final_score=scores_detail['final_score'], base_score=scores_detail['base_score'], session_id=session.id)
            db.session.add(name_score)
            db.session.flush()
            first_name_variations = scores_detail['first_name']['metrics']['variations']
            for var in first_name_variations:
                variation_score = VariationScore(
                    variation=var['variation'],
                    phonetic_score=var['phonetic_score'],
                    orthographic_score=var['orthographic_score'],
                    name_part='first',
                    name_id=name_score.id
                )
                db.session.add(variation_score)
                
            if scores_detail.get('last_name', {}):
                last_name_variations = scores_detail.get('last_name', {}).get('metrics', {}).get('variations', [])
                for var in last_name_variations:
                    variation_score = VariationScore(
                        variation=var['variation'],
                        phonetic_score=var['phonetic_score'],
                        orthographic_score=var['orthographic_score'],
                        name_part='last',
                        name_id=name_score.id
                        )
                    db.session.add(variation_score)
        db.session.commit()
        log.info(f"Scores for UID {uid} successfully saved")
        return jsonify({
            "status": True, 
            "data": {
                'Average Final Score': variations_scores['average_final_score']
            }
        })
    except Exception as e:
        log.error(f"Error in input_score: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({"status": False, "message": str(e)}), 500

@service_bp.route('/yanez/score', methods=["GET"])
@require_api_key
def get_score():
    log.info("GET /yanez/score accessed")
    try:
        uid_value = request.args.get('uid', None)
        page = request.args.get('page', 1, type=int)
        size = request.args.get('size', 10, type=int)
        size = min(size, 100)
        now = datetime.now(timezone.utc)
        one_hour_ago = now - timedelta(hours=1)
        if not uid_value:
            # 1. Semua UID & score session terakhir
            all_users = UserUID.query.all()
            result = []
            for user in all_users:
                latest_session = ScoreSession.query.filter_by(user_id=user.id).order_by(ScoreSession.created_at.desc()).first()
                if latest_session:
                    result.append({
                        'uid': user.uid,
                        'latest_score': latest_session.avg_final_score,
                        'created_at': latest_session.created_at.isoformat()
                    })
            log.info(f"Returned latest score for {len(result)} users")
            return jsonify({'status': True, 'latest_scores': result})
        
        user = UserUID.query.filter_by(uid=uid_value).first()
        if not user:
            log.warning(f"UID {uid_value} not found")
            return jsonify({'status': False, 'message': 'UID not found'}), 404

        # a. Score rata-rata 1 jam terakhir
        sessions_1hr = ScoreSession.query.filter(
            ScoreSession.user_id == user.id,
            ScoreSession.created_at >= one_hour_ago,
            ScoreSession.created_at <= now
        ).order_by(ScoreSession.created_at.desc()).all()
        avg_score_1hr = (sum(s.avg_final_score for s in sessions_1hr) / len(sessions_1hr)) if sessions_1hr else None

        # b. Score session terbaru dalam 1 jam terakhir
        latest_1hr = sessions_1hr[0] if sessions_1hr else None
        latest_1hr_score = latest_1hr.avg_final_score if latest_1hr else None
        latest_1hr_created = latest_1hr.created_at.isoformat() if latest_1hr else None

        # c. Table detail session, name, variations
        sessions_query = ScoreSession.query.filter_by(user_id=user.id).order_by(ScoreSession.created_at.desc())
        total_sessions = sessions_query.count()
        paginated_sessions = sessions_query.paginate(
            page=page,
            per_page=size,
            error_out=False
        )
        detail_sessions = []
        for session in paginated_sessions.items:
            session_data = {
                'session_id': session.id,
                'avg_final_score': session.avg_final_score,
                'created_at': session.created_at.isoformat(),
                'names': []
            }
            for name_score in session.names:
                first_name_vars = [var for var in name_score.variations if var.name_part == 'first']
                last_name_vars = [var for var in name_score.variations if var.name_part == 'last']
                name_data = {
                    'name': name_score.name,
                    'final_score': name_score.final_score,
                    'base_score': name_score.base_score,
                    'first_name_variations': [
                        {
                            'variation': var.variation,
                            'phonetic_score': var.phonetic_score,
                            'orthographic_score': var.orthographic_score
                        } for var in first_name_vars
                    ],
                    'last_name_variations': [
                        {
                            'variation': var.variation,
                            'phonetic_score': var.phonetic_score,
                            'orthographic_score': var.orthographic_score
                        } for var in last_name_vars
                    ]
                }
                session_data['names'].append(name_data)
            detail_sessions.append(session_data)
        pagination_info = {
            'current_page': page,
            'per_page': size,
            'total_items': total_sessions,
            'total_pages': paginated_sessions.pages,
            'has_next': paginated_sessions.has_next,
            'has_prev': paginated_sessions.has_prev,
            'next_page': paginated_sessions.next_num if paginated_sessions.has_next else None,
            'prev_page': paginated_sessions.prev_num if paginated_sessions.has_prev else None
        }

        log.info(f"Returned score details for UID {user.uid}")
        return jsonify({
            'status': True,
            'uid': user.uid,
            'average_score_latest_1hr': avg_score_1hr,
            'latest_score_1hr': latest_1hr_score,
            'latest_score_1hr_created': latest_1hr_created,
            'details': detail_sessions,
            'pagination': pagination_info
        })
    except Exception as e:
        log.error(f"Error in get_score: {e}", exc_info=True)
        return jsonify({'status': False, 'message': str(e)}), 500

@service_bp.route('/yanez/modify_variations', methods=['POST'])
@require_api_key
def modify_variations():
    """
    Modify variations to match configuration requirements without calculating scores.
    """
    log.info("POST /yanez/modify_variations accessed")
    try:
        data = request.json
        variation_config = data.get('variation_config', {})
        variation_result = data.get('variation_result', {})
        
        # Modify variations to match config requirements
        from app.utils.var_modifier import modify_variation_result_to_match_config
        modified_variation_result = modify_variation_result_to_match_config(variation_result, variation_config)
        
        log.info(f"Successfully modified variations for {len(modified_variation_result)} seed names")
        return jsonify({
            "status": True,
            "data": {
                'modified_variation_result': modified_variation_result,
                'original_count': sum(len(vars) for vars in variation_result.values()),
                'modified_count': sum(len(vars) for vars in modified_variation_result.values())
            }
        })
    except Exception as e:
        log.error(f"Error in modify_variations: {e}", exc_info=True)
        return jsonify({'status': False, 'message': str(e)}), 500

@service_bp.route('/yanez/avg_score/<string:uid>', methods=['GET'])
@require_api_key
def get_avg_score(uid):
    log.info(f"GET /yanez/avg_score/{uid} accessed")
    try:
        user = UserUID.query.filter_by(uid=uid).first()
        if not user:
            log.warning(f"User {uid} not found")
            return jsonify({'status': False, 'message': 'User not found'}), 404

        # Hitung batas waktu 48 jam terakhir
        window_start = datetime.utcnow() - timedelta(hours=48)
        avg_scores = (
            AverageScore.query
            .filter_by(user_id=user.id)
            .filter(AverageScore.timestamp >= window_start)
            .order_by(AverageScore.timestamp.desc())
            .all()
        )

        data = [
            {'score': row.score, 'timestamp': row.timestamp.isoformat()}
            for row in avg_scores
        ]
        log.info(f"Returned {len(data)} avg scores for UID {uid}")
        return jsonify({'status': True, 'uid': uid, 'averages': data})
    except Exception as e:
        log.error(f"Error in get_avg_score: {e}", exc_info=True)
        return jsonify({'status': False, 'message': str(e)}), 500
