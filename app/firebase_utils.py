import json
import os
import firebase_admin
from firebase_admin import credentials, db
from django.conf import settings
from pathlib import Path


def get_db():
    if not firebase_admin._apps:
        try:
            # Prefer JSON env variable (production / Railway)
            service_account_json = os.environ.get('FIREBASE_SERVICE_ACCOUNT_JSON')
            if service_account_json:
                cred = credentials.Certificate(json.loads(service_account_json))
            else:
                # Fallback: read from file (local development)
                service_account_path = Path(settings.BASE_DIR) / 'serviceAccountKey.json'
                if not service_account_path.exists():
                    return None
                cred = credentials.Certificate(str(service_account_path))

            firebase_admin.initialize_app(cred, {
                'databaseURL': settings.FIREBASE_DATABASE_URL
            })
        except Exception:
            return None
    return db if firebase_admin._apps else None


def update_active_session(session):
    firebase_db = get_db()
    if not firebase_db:
        return False

    try:
        ref = firebase_db.reference('active_session')
        if session:
            ref.set({
                'session_id': session.id,
                'status': 'OPEN',
                'class': session.classe.name,
                'teacher': session.teacher.name,
                'start_time': str(session.start_time),
            })
        else:
            ref.set({'status': 'CLOSED', 'session_id': None})
    except Exception:
        return False

    return True
