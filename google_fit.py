import requests
import base64
import hashlib
import os
from datetime import datetime, timedelta, date, timezone
from urllib.parse import urlencode
from config import Config


GOOGLE_AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
GOOGLE_FIT_BASE = 'https://www.googleapis.com/fitness/v1/users/me'

SCOPES = [
    'https://www.googleapis.com/auth/fitness.activity.read',
    'https://www.googleapis.com/auth/fitness.body.read',
    'https://www.googleapis.com/auth/fitness.heart_rate.read',
    'https://www.googleapis.com/auth/fitness.sleep.read',
]

FIT_ACTIVITY_MAP = {
    'walking': 'walking_brisk',
    'running': 'running_moderate',
    'cycling': 'cycling_moderate',
    'swimming': 'swimming_moderate',
    'strength_training': 'strength',
    'yoga': 'yoga',
    'rowing': 'rowing',
    'elliptical': 'elliptical',
    'hiking': 'walking_brisk',
    'dancing': 'running_easy',
    'biking': 'cycling_moderate',
    'stretching': 'stretching',
    'pilates': 'yoga',
    'walking_fitness': 'walking_brisk',
}

FIT_ACTIVITY_CODES = {
    8: 'running',
    9: 'walking',
    1: 'cycling',
    2: 'cycling',
    3: 'cycling',
    17: 'strength_training',
    16: 'swimming',
    18: 'stretching',
    19: 'yoga',
    20: 'elliptical',
    21: 'rowing',
    22: 'hiking',
    35: 'dancing',
    54: 'pilates',
    41: 'walking_fitness',
    7: 'walking',
}


def get_config():
    client_id = Config.GOOGLE_CLIENT_ID
    client_secret = Config.GOOGLE_CLIENT_SECRET
    redirect_uri = Config.GOOGLE_REDIRECT_URI
    if not client_id or not client_secret or not redirect_uri:
        raise ValueError(
            'Google OAuth non configurato. '
            'Imposta GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET e GOOGLE_REDIRECT_URI nel file .env'
        )
    return client_id, client_secret, redirect_uri


def generate_auth_url(state=None):
    client_id, _, redirect_uri = get_config()
    state = state or os.urandom(16).hex()
    params = {
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': ' '.join(SCOPES),
        'access_type': 'offline',
        'prompt': 'consent',
        'state': state,
    }
    return GOOGLE_AUTH_URL + '?' + urlencode(params), state


def exchange_code(code):
    client_id, client_secret, redirect_uri = get_config()
    resp = requests.post(GOOGLE_TOKEN_URL, data={
        'code': code,
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code',
    })
    data = resp.json()
    if 'error' in data:
        raise ValueError(f"Google OAuth error: {data.get('error_description', data['error'])}")
    return data


def refresh_access_token(refresh_token):
    client_id, client_secret, _ = get_config()
    resp = requests.post(GOOGLE_TOKEN_URL, data={
        'refresh_token': refresh_token,
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'refresh_token',
    })
    data = resp.json()
    if 'error' in data:
        raise ValueError(f"Google token refresh error: {data.get('error_description', data['error'])}")
    return data


def _headers(access_token):
    return {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }


def _nanos_to_datetime(nanos):
    return datetime.fromtimestamp(nanos / 1e9, tz=timezone.utc)


def _date_from_nanos(nanos):
    return _nanos_to_datetime(int(nanos)).date()


def fetch_steps(access_token, start_date, end_date):
    body = {
        'aggregateBy': [{
            'dataTypeName': 'com.google.step_count.delta',
            'dataSourceId': 'derived:com.google.step_count.delta:com.google.android.gms:estimated_steps',
        }],
        'bucketByTime': {'durationMillis': 86400000},
        'startTimeMillis': int(datetime.combine(start_date, datetime.min.time()).timestamp() * 1000),
        'endTimeMillis': int(datetime.combine(end_date, datetime.max.time()).timestamp() * 1000),
    }
    resp = requests.post(
        f'{GOOGLE_FIT_BASE}/dataset:aggregate',
        headers=_headers(access_token),
        json=body,
    )
    if resp.status_code != 200:
        return {}
    data = resp.json()
    results = {}
    for bucket in data.get('bucket', []):
        day = _date_from_nanos(int(bucket['startTimeMillis']) * 1e6)
        total = sum(
            p['value'][0]['intVal']
            for p in bucket.get('dataset', [{}])[0].get('point', [])
            if p.get('value') and 'intVal' in p['value'][0]
        )
        results[day] = total
    return results


def fetch_calories(access_token, start_date, end_date):
    body = {
        'aggregateBy': [{
            'dataTypeName': 'com.google.calories.expended',
            'dataSourceId': 'derived:com.google.calories.expended:com.google.android.gms:from_activities',
        }],
        'bucketByTime': {'durationMillis': 86400000},
        'startTimeMillis': int(datetime.combine(start_date, datetime.min.time()).timestamp() * 1000),
        'endTimeMillis': int(datetime.combine(end_date, datetime.max.time()).timestamp() * 1000),
    }
    resp = requests.post(
        f'{GOOGLE_FIT_BASE}/dataset:aggregate',
        headers=_headers(access_token),
        json=body,
    )
    if resp.status_code != 200:
        return {}
    data = resp.json()
    results = {}
    for bucket in data.get('bucket', []):
        day = _date_from_nanos(int(bucket['startTimeMillis']) * 1e6)
        total = sum(
            p['value'][0]['fpVal']
            for p in bucket.get('dataset', [{}])[0].get('point', [])
            if p.get('value') and 'fpVal' in p['value'][0]
        )
        results[day] = round(total, 0)
    return results


def _find_weight_data_sources(access_token):
    resp = requests.get(
        f'{GOOGLE_FIT_BASE}/dataSources',
        headers=_headers(access_token),
        params={'dataTypeName': 'com.google.weight'},
    )
    if resp.status_code != 200:
        return []
    return [ds['dataStreamId'] for ds in resp.json().get('dataSource', [])
            if ds.get('dataStreamId') and 'merge_weight' in ds['dataStreamId']]


def fetch_weight(access_token, start_date, end_date):
    data_sources = _find_weight_data_sources(access_token)
    if not data_sources:
        data_sources = [
            'derived:com.google.weight:com.google.android.gms:merge_weight',
        ]
    results = {}
    for ds in data_sources:
        body = {
            'aggregateBy': [{
                'dataTypeName': 'com.google.weight',
                'dataSourceId': ds,
            }],
            'bucketByTime': {'durationMillis': 86400000},
            'startTimeMillis': int(datetime.combine(start_date, datetime.min.time()).timestamp() * 1000),
            'endTimeMillis': int(datetime.combine(end_date, datetime.max.time()).timestamp() * 1000),
        }
        resp = requests.post(
            f'{GOOGLE_FIT_BASE}/dataset:aggregate',
            headers=_headers(access_token),
            json=body,
        )
        if resp.status_code != 200:
            continue
        data = resp.json()
        for bucket in data.get('bucket', []):
            day = _date_from_nanos(int(bucket['startTimeMillis']) * 1e6)
            for dataset in bucket.get('dataset', []):
                for point in dataset.get('point', []):
                    if point.get('value') and 'fpVal' in point['value'][0]:
                        results[day] = round(point['value'][0]['fpVal'], 1)
        if results:
            break
    return results


def fetch_sessions(access_token, start_date, end_date):
    params = {
        'startTime': datetime.combine(start_date, datetime.min.time()).isoformat() + 'Z',
        'endTime': datetime.combine(end_date, datetime.max.time()).isoformat() + 'Z',
    }
    resp = requests.get(
        f'{GOOGLE_FIT_BASE}/sessions',
        headers=_headers(access_token),
        params=params,
    )
    if resp.status_code != 200:
        return []
    data = resp.json()
    return data.get('session', [])


def map_activity_type(activity_type):
    from nutrition import ACTIVITY_METS
    if isinstance(activity_type, int):
        mapped = FIT_ACTIVITY_CODES.get(activity_type, '')
        if mapped:
            return FIT_ACTIVITY_MAP.get(mapped, mapped)
        return 'strength'
    atype = str(activity_type).lower().replace(' ', '_') if activity_type else ''
    mapped = FIT_ACTIVITY_MAP.get(atype, atype)
    if mapped in ACTIVITY_METS:
        return mapped
    for eng, fit_key in FIT_ACTIVITY_MAP.items():
        if eng in atype or atype in eng:
            return fit_key
    return 'strength'


def sync_google_fit(user, db_session):
    from datetime import date, timedelta
    from models import WorkoutEntry, WeightLog, SyncLog, utcnow
    import logging

    logger = logging.getLogger('ajo.sync')
    today = date.today()
    start_date = today - timedelta(days=7)
    stats = {'workouts': 0, 'weights': 0, 'steps': 0}

    now = utcnow()
    log = SyncLog(user_id=user.id, provider='google_fit', status='running', started_at=now)
    db_session.add(log)
    db_session.flush()

    try:
        token = None
        if user.google_access_token and user.google_token_expiry:
            if utcnow() >= user.google_token_expiry and user.google_refresh_token:
                new_tokens = refresh_access_token(user.google_refresh_token)
                user.google_access_token = new_tokens['access_token']
                user.google_token_expiry = utcnow() + timedelta(seconds=new_tokens.get('expires_in', 3600))
                if 'refresh_token' in new_tokens:
                    user.google_refresh_token = new_tokens['refresh_token']
                db_session.commit()
            token = user.google_access_token

        if not token:
            raise ValueError('Nessun token Google trovato')

        weight_data = fetch_weight(token, start_date, today)
        logger.info(f'Weight data from Google Fit: {len(weight_data)} entries: {weight_data}')
        for d, w in weight_data.items():
            existing = WeightLog.query.filter_by(user_id=user.id, date=d).first()
            if not existing:
                wl = WeightLog(user_id=user.id, weight=w, date=d, note='Sincronizzato da Google Fit')
                db_session.add(wl)
                stats['weights'] += 1

        sessions = fetch_sessions(token, start_date, today)
        logger.info(f'Sessions from Google Fit: {len(sessions)} total')
        if sessions and len(sessions) > 0:
            logger.info(f'First session: {sessions[0]}')
        existing_sessions = set()
        for wo in WorkoutEntry.query.filter(
            WorkoutEntry.user_id == user.id,
            WorkoutEntry.date >= start_date,
        ).with_entities(WorkoutEntry.note).all():
            if wo[0] and 'Google Fit' in wo[0]:
                existing_sessions.add(wo[0])

        for s in sessions:
            if not s.get('startTimeMillis') or not s.get('endTimeMillis'):
                continue
            session_date = _date_from_nanos(int(s['startTimeMillis']) * 1e6)
            session_name = s.get('name', 'Allenamento')
            note = f'Google Fit: {session_name}'
            if note in existing_sessions:
                continue
            duration_min = int((int(s['endTimeMillis']) - int(s['startTimeMillis'])) / 60000)
            if duration_min < 1:
                continue
            activity_type = map_activity_type(s.get('activityType', ''))
            from nutrition import calories_burned
            w = user.current_weight or 75
            kcal = calories_burned(activity_type, duration_min, w)
            wo = WorkoutEntry(
                user_id=user.id, date=session_date,
                activity_type=activity_type, duration_min=duration_min,
                calories_burned=kcal, note=note,
            )
            db_session.add(wo)
            stats['workouts'] += 1

        user.last_sync_at = utcnow()
        log.status = 'success'
        log.message = f'Importati {stats["workouts"]} allenamenti, {stats["weights"]} pesi'
        log.workouts_imported = stats['workouts']
        log.weight_logs_imported = stats['weights']
        db_session.commit()

    except Exception as e:
        log.status = 'error'
        log.message = str(e)
        log.completed_at = utcnow()
        db_session.commit()
        logger.error(f'Google Fit sync error for user {user.id}: {e}')
        import traceback
        logger.error(traceback.format_exc())

    return stats