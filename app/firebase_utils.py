import firebase_admin
from firebase_admin import credentials, db
from django.conf import settings
from pathlib import Path


def get_db():
    if not firebase_admin._apps:
        service_account_path = Path(settings.BASE_DIR) / 'serviceAccountKey.json'
        if not service_account_path.exists():
            return None
        try:
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
