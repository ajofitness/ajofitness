import os
import sys
import tempfile
import pytest
from datetime import date, datetime, timezone

def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def app():
    from app import create_app
    from models import db as _db
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db(app):
    from models import db as _db
    return _db


def test_index_redirects_to_dashboard_when_logged_in(client, app):
    from models import User, db
    with app.app_context():
        user = User(email='test@test.com', name='Test', gender='M',
                    height_cm=175, target_weight_kg=70, birth_date=date(1990, 1, 1))
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        client.post('/login', data={'email': 'test@test.com', 'password': 'password123'})
    resp = client.get('/')
    assert resp.status_code == 302


def test_index_returns_landing(client):
    resp = client.get('/')
    assert resp.status_code == 200
    assert 'Ajò'.encode() in resp.data


def test_register_valid_user(client, app):
    from models import User, db
    resp = client.post('/register', data={
        'email': 'new@test.com', 'password': 'abcdef',
        'name': 'New User', 'gender': 'M', 'height': 175,
        'current_weight': 80, 'target_weight': 70,
        'birth_date': '1990-01-01', 'activity': 'moderate', 'deficit': 500,
    }, follow_redirects=True)
    assert resp.status_code == 200
    # Check what went wrong
    if b'Email non valida' in resp.data:
        pytest.fail("Email validation failed")
    if b'non valido' in resp.data or b'errore' in resp.data:
        pytest.fail(f"Registration failed: {resp.data[:500]}")
    with app.app_context():
        user = db.session.execute(
            db.select(User).filter_by(email='new@test.com')
        ).scalar()
        assert user is not None


def test_register_invalid_email(client):
    resp = client.post('/register', data={
        'email': 'notanemail', 'password': 'abcdef',
        'name': 'Test', 'gender': 'M', 'height': 175,
        'current_weight': 80, 'target_weight': 70,
        'birth_date': '1990-01-01', 'activity': 'moderate', 'deficit': 500,
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b'Email non valida' in resp.data


def test_login_invalid_credentials(client):
    resp = client.post('/login', data={
        'email': 'nonexistent@test.com', 'password': 'wrong',
    }, follow_redirects=True)
    assert b'Credenziali non valide' in resp.data


def test_login_valid_credentials(client, app):
    from models import User, db
    with app.app_context():
        user = User(email='valid@test.com', name='Test', gender='M',
                    height_cm=175, target_weight_kg=70, birth_date=date(1990, 1, 1))
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
    resp = client.post('/login', data={
        'email': 'valid@test.com', 'password': 'password123',
    }, follow_redirects=True)
    assert resp.status_code == 200


def test_dashboard_requires_login(client):
    resp = client.get('/dashboard', follow_redirects=True)
    assert b'Accedi per continuare' in resp.data


def test_nutrition_plan_calculation():
    from nutrition import build_plan
    plan = build_plan(85, 75, 180, 30, 'M', 'moderate', 500)
    assert plan.bmr > 1500
    assert plan.tdee > plan.bmr
    assert plan.target_kcal < plan.tdee
    assert plan.weekly_loss_kg > 0
    assert plan.protein_g > 0
    assert plan.carbs_g > 0
    assert plan.fat_g > 0


def test_bmi_calculation():
    from nutrition import calculate_bmi, bmi_category
    bmi = calculate_bmi(80, 180)
    assert bmi == 24.7
    assert bmi_category(bmi) == 'Normale'
    assert bmi_category(17) == 'Sottopeso'
    assert bmi_category(27) == 'Sovrappeso'
    assert bmi_category(32) == 'Obesità'


def test_calories_burned():
    from nutrition import calories_burned
    kcal = calories_burned('running_moderate', 30, 80)
    assert kcal > 0
    assert kcal < 1000


def test_water_tracking(client, app):
    from models import User, WeightLog, db
    with app.app_context():
        user = User(email='water@test.com', name='Water', gender='M',
                    height_cm=175, target_weight_kg=70, birth_date=date(1990, 1, 1),
                    onboarding_done=True)
        user.set_password('test')
        db.session.add(user)
        db.session.flush()
        db.session.add(WeightLog(user_id=user.id, weight=80, date=date.today()))
        db.session.commit()
    client.post('/login', data={'email': 'water@test.com', 'password': 'test'})
    resp = client.post('/water/add', data={'amount_ml': 250}, follow_redirects=True)
    assert resp.status_code == 200


def test_export_csv(client, app):
    from models import User, WeightLog, db
    with app.app_context():
        user = User(email='export@test.com', name='Export', gender='M',
                    height_cm=175, target_weight_kg=70, birth_date=date(1990, 1, 1),
                    onboarding_done=True)
        user.set_password('test')
        db.session.add(user)
        db.session.flush()
        db.session.add(WeightLog(user_id=user.id, weight=80, date=date.today()))
        db.session.commit()
    client.post('/login', data={'email': 'export@test.com', 'password': 'test'})
    resp = client.get('/export/csv/weight')
    assert resp.status_code == 200
    assert resp.mimetype == 'text/csv'


def test_calculate_streak_empty():
    from nutrition import calculate_streak
    assert calculate_streak([]) == 0


def test_calculate_streak_no_today():
    from nutrition import calculate_streak
    from datetime import timedelta
    d = date.today() - timedelta(days=1)
    assert calculate_streak([d]) == 0


def test_calculate_streak_consecutive():
    from nutrition import calculate_streak
    from datetime import timedelta
    today = date.today()
    dates = [today - timedelta(days=i) for i in range(5)]
    assert calculate_streak(dates) == 5


def test_calculate_streak_broken():
    from nutrition import calculate_streak
    from datetime import timedelta
    today = date.today()
    dates = [today, today - timedelta(days=1), today - timedelta(days=3)]
    assert calculate_streak(dates) == 2


def test_body_fat_percentage():
    from nutrition import body_fat_percentage
    bf = body_fat_percentage(24.7, 30, 'M')
    assert bf > 5
    assert bf < 50
    # Female should be higher
    bf_m = body_fat_percentage(22, 25, 'M')
    bf_f = body_fat_percentage(22, 25, 'F')
    assert bf_f > bf_m
    # Clamped
    assert body_fat_percentage(10, 20, 'M') >= 3
    assert body_fat_percentage(50, 70, 'F') <= 60


def test_diet_presets_sum_to_100():
    from nutrition import DIET_PRESETS
    for key, preset in DIET_PRESETS.items():
        total = preset['protein_pct'] + preset['carbs_pct'] + preset['fat_pct']
        assert total == 100, f'{key}: {preset["protein_pct"]}+{preset["carbs_pct"]}+{preset["fat_pct"]}={total} != 100'


def test_get_macro_ratios_returns_preset():
    from nutrition import get_macro_ratios
    p, c, f = get_macro_ratios('keto')
    assert p == 20 and c == 5 and f == 75


def test_get_macro_ratios_custom_override():
    from nutrition import get_macro_ratios
    p, c, f = get_macro_ratios('balanced', (50, 20, 30))
    assert p == 50 and c == 20 and f == 30


def test_get_macro_ratios_rejects_invalid():
    from nutrition import get_macro_ratios
    p, c, f = get_macro_ratios('balanced', (50, 50, 50))  # sums to 150
    assert p == 30  # falls back to preset


def test_badge_first_log(app, db):
    from models import User, Badge
    from nutrition import check_new_badges
    with app.app_context():
        user = User(email='badge1@test.com', name='B1', gender='M',
                    height_cm=175, target_weight_kg=70, birth_date=date(1990, 1, 1))
        user.set_password('p')
        db.session.add(user)
        db.session.flush()
        # No entries yet → no badge
        assert check_new_badges(user, db.session) == []
        db.session.commit()


def test_badge_first_log_awarded(app, db):
    from models import User, Badge, MealEntry, WeightLog
    from nutrition import check_new_badges
    with app.app_context():
        user = User(email='badge2@test.com', name='B2', gender='M',
                    height_cm=175, target_weight_kg=70, birth_date=date(1990, 1, 1))
        user.set_password('p')
        db.session.add(user)
        db.session.flush()
        db.session.add(MealEntry(user_id=user.id, food_id=None, quantity_g=100,
                                  meal_type='colazione', date=date.today()))
        db.session.add(WeightLog(user_id=user.id, weight=80, date=date.today()))
        db.session.commit()
        new = check_new_badges(user, db.session)
        types = {b['name'] for b in new}
        assert 'Primo Passo' in types
        # Second call should return empty (already awarded)
        assert check_new_badges(user, db.session) == []


def test_badge_streak_7(app, db):
    from models import User, Badge, WeightLog
    from nutrition import check_new_badges
    from datetime import timedelta
    with app.app_context():
        user = User(email='badge3@test.com', name='B3', gender='M',
                    height_cm=175, target_weight_kg=70, birth_date=date(1990, 1, 1))
        user.set_password('p')
        db.session.add(user)
        db.session.flush()
        today = date.today()
        for i in range(7):
            db.session.add(WeightLog(user_id=user.id, weight=80, date=today - timedelta(days=i)))
        db.session.commit()
        new = check_new_badges(user, db.session)
        names = {b['name'] for b in new}
        assert 'Costante' in names
        assert 'On Fire' in names


def test_badge_weight_loss(app, db):
    from models import User, Badge, WeightLog
    from nutrition import check_new_badges
    from datetime import timedelta
    with app.app_context():
        user = User(email='badge4@test.com', name='B4', gender='M',
                    height_cm=175, target_weight_kg=70, birth_date=date(1990, 1, 1))
        user.set_password('p')
        db.session.add(user)
        db.session.flush()
        today = date.today()
        # Start at 85, now 78 → lost 7kg
        db.session.add(WeightLog(user_id=user.id, weight=85, date=today - timedelta(days=30)))
        db.session.add(WeightLog(user_id=user.id, weight=78, date=today))
        db.session.commit()
        new = check_new_badges(user, db.session)
        names = {b['name'] for b in new}
        assert 'Primo Traguardo' in names
        assert 'Metamorfosi' in names
        assert 'Trasformazione' not in names  # need 10kg lost


def test_api_stats_requires_login(client):
    resp = client.get('/api/stats')
    assert resp.status_code == 302  # redirect to login


def test_api_stats_authenticated(client, app):
    from models import User, WeightLog, db
    from datetime import timedelta
    with app.app_context():
        user = User(email='stats@test.com', name='Stats', gender='M',
                    height_cm=175, target_weight_kg=70, birth_date=date(1990, 1, 1),
                    onboarding_done=True)
        user.set_password('p')
        db.session.add(user)
        db.session.flush()
        today = date.today()
        for i in range(3):
            db.session.add(WeightLog(user_id=user.id, weight=80, date=today - timedelta(days=i)))
        db.session.commit()
    client.post('/login', data={'email': 'stats@test.com', 'password': 'p'})
    resp = client.get('/api/stats')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['streak'] == 3
    assert data['has_weight_today'] is True


def test_photos_page_requires_login(client):
    resp = client.get('/photos')
    assert resp.status_code == 302


def test_photos_page_authenticated(client, app):
    from models import User, WeightLog, db
    with app.app_context():
        user = User(email='photo@test.com', name='Photo', gender='M',
                    height_cm=175, target_weight_kg=70, birth_date=date(1990, 1, 1),
                    onboarding_done=True)
        user.set_password('p')
        db.session.add(user)
        db.session.flush()
        db.session.add(WeightLog(user_id=user.id, weight=80, date=date.today()))
        db.session.commit()
    client.post('/login', data={'email': 'photo@test.com', 'password': 'p'})
    resp = client.get('/photos')
    assert resp.status_code == 200
    assert b'Foto Progresso' in resp.data


def test_adapt_plan_preserves_when_on_track():
    from nutrition import build_plan, adapt_plan_from_history
    plan = build_plan(85, 75, 180, 30, 'M', 'moderate', 500)
    adapted = adapt_plan_from_history(plan, plan.weekly_loss_kg)
    assert adapted.deficit_used == plan.deficit_used


def test_adapt_plan_adjusts_when_slow():
    from nutrition import build_plan, adapt_plan_from_history
    plan = build_plan(85, 75, 180, 30, 'M', 'moderate', 500)
    adapted = adapt_plan_from_history(plan, plan.weekly_loss_kg * 0.3)
    assert adapted.deficit_used > plan.deficit_used


def test_check_reminder_requires_login(client):
    resp = client.get('/api/check-reminder')
    assert resp.status_code == 302


def test_check_reminder_authenticated(client, app):
    from models import User, WeightLog, db
    with app.app_context():
        user = User(email='remind@test.com', name='Remind', gender='M',
                    height_cm=175, target_weight_kg=70, birth_date=date(1990, 1, 1),
                    onboarding_done=True)
        user.set_password('p')
        db.session.add(user)
        db.session.flush()
        db.session.add(WeightLog(user_id=user.id, weight=80, date=date.today()))
        db.session.commit()
    client.post('/login', data={'email': 'remind@test.com', 'password': 'p'})
    resp = client.get('/api/check-reminder')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['can_remind'] is True
    assert data['missing_meals'] is True
    assert data['missing_water'] is True


def test_service_worker_served(client):
    resp = client.get('/sw.js')
    assert resp.status_code == 200
    assert b'ajo' in resp.data


def test_adapt_plan_adjusts_when_fast():
    from nutrition import build_plan, adapt_plan_from_history
    plan = build_plan(85, 75, 180, 30, 'M', 'moderate', 500)
    adapted = adapt_plan_from_history(plan, plan.weekly_loss_kg * 2)
    assert adapted.deficit_used < plan.deficit_used


def test_fasting_page_requires_login(client):
    resp = client.get('/fasting')
    assert resp.status_code == 302


def test_fasting_page_authenticated(client, app):
    from models import User, WeightLog, db
    with app.app_context():
        user = User(email='fast@test.com', name='Fast', gender='M',
                    height_cm=175, target_weight_kg=70, birth_date=date(1990, 1, 1),
                    onboarding_done=True)
        user.set_password('p')
        db.session.add(user)
        db.session.flush()
        db.session.add(WeightLog(user_id=user.id, weight=80, date=date.today()))
        db.session.commit()
    client.post('/login', data={'email': 'fast@test.com', 'password': 'p'})
    resp = client.get('/fasting')
    assert resp.status_code == 200
    assert b'Digiuno' in resp.data


def test_fasting_start_stop(client, app):
    from models import User, WeightLog, FastingEntry, db
    from datetime import datetime, timedelta
    with app.app_context():
        user = User(email='fast2@test.com', name='Fast2', gender='M',
                    height_cm=175, target_weight_kg=70, birth_date=date(1990, 1, 1),
                    onboarding_done=True)
        user.set_password('p')
        db.session.add(user)
        db.session.flush()
        db.session.add(WeightLog(user_id=user.id, weight=80, date=date.today()))
        db.session.commit()
        # Create a fast in the past so duration > 0
        past = utcnow() - timedelta(hours=2)
        fe = FastingEntry(user_id=user.id, date=date.today(), start_time=past, planned_hours=16)
        db.session.add(fe)
        db.session.commit()
        fe_id = fe.id
    client.post('/login', data={'email': 'fast2@test.com', 'password': 'p'})
    resp = client.post(f'/api/fasting/stop', json={})
    assert resp.status_code == 200
    data2 = resp.get_json()
    assert data2['ok'] is True
    assert data2['duration_hours'] > 0


def test_fasting_status(client, app):
    from models import User, WeightLog, FastingEntry, db
    from datetime import datetime
    with app.app_context():
        user = User(email='fast3@test.com', name='Fast3', gender='M',
                    height_cm=175, target_weight_kg=70, birth_date=date(1990, 1, 1),
                    onboarding_done=True)
        user.set_password('p')
        db.session.add(user)
        db.session.flush()
        db.session.add(WeightLog(user_id=user.id, weight=80, date=date.today()))
        db.session.commit()
    client.post('/login', data={'email': 'fast3@test.com', 'password': 'p'})

    resp = client.get('/api/fasting/status')
    assert resp.status_code == 200
    assert resp.get_json()['active'] is False

    client.post('/api/fasting/start', json={'hours': 16})
    resp = client.get('/api/fasting/status')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['active'] is True
    assert data['planned_hours'] == 16


def test_fasting_badge_3(app, db):
    from models import User, Badge, FastingEntry
    from nutrition import check_new_badges
    from datetime import datetime
    with app.app_context():
        user = User(email='fgb@test.com', name='FB', gender='M',
                    height_cm=175, target_weight_kg=70, birth_date=date(1990, 1, 1))
        user.set_password('p')
        db.session.add(user)
        db.session.flush()
        now = utcnow()
        for i in range(3):
            db.session.add(FastingEntry(
                user_id=user.id, date=date.today(),
                start_time=now - __import__('datetime').timedelta(hours=20 * (i + 1)),
                end_time=now - __import__('datetime').timedelta(hours=4 * (i + 1)),
                planned_hours=16, completed=True,
            ))
        db.session.commit()
        new = check_new_badges(user, db.session)
        names = {b['name'] for b in new}
        assert 'Digiunatore' in names
