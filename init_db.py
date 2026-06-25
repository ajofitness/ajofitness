import os
import sys
import random
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, User, WeightLog, Food, MealEntry, WorkoutEntry, WaterEntry, Measurement, Goal
from foods_data import populate_foods


def create_demo_user():
    demo_email = 'demo@ajo.app'
    if User.query.filter_by(email=demo_email).first():
        print('Demo user already exists, skipping.')
        return

    user = User(
        email=demo_email,
        name='Marco Demo',
        gender='M',
        height_cm=183,
        birth_date=date(1990, 5, 15),
        activity_level='moderate',
        target_weight_kg=75.0,
        deficit_kcal=500,
        start_date=date.today() - timedelta(days=30),
        is_demo=True,
        onboarding_done=True,
    )
    user.set_password('demo1234')
    db.session.add(user)
    db.session.commit()

    start_w = 90.0
    target_w = 86.5
    days = 30
    for i in range(days):
        base = start_w - (start_w - target_w) * (i / (days - 1))
        noise = random.uniform(-0.4, 0.4)
        if i < 5:
            base -= i * 0.15
        weight = round(base + noise, 1)
        d = date.today() - timedelta(days=days - 1 - i)
        wl = WeightLog(
            user_id=user.id,
            weight=weight,
            date=d,
            note='Demo' if i % 5 == 0 else None,
        )
        db.session.add(wl)
    db.session.commit()

    food_ids = [f.id for f in Food.query.all()]
    def food_id_by_name(name):
        f = Food.query.filter_by(name=name).first()
        return f.id if f else None

    templates = {
        'breakfast': [
            ('Uovo sodo', 120), ('Yogurt greco 0%', 150), ('Fiocchi d\'avena', 50),
            ('Pane integrale', 50), ('Mandorle', 20), ('Banana', 120),
        ],
        'lunch': [
            ('Petto di pollo ai ferri', 150), ('Riso integrale cotto', 200),
            ('Pasta integrale cotta', 180), ('Insalata mista', 150),
            ('Olio extravergine d\'oliva', 10), ('Pomodori', 100),
            ('Fagioli borlotti in scatola', 150), ('Farro cotto', 200),
        ],
        'snack': [
            ('Yogurt greco 0%', 100), ('Mela', 150), ('Mandorle', 15),
            ('Fiocchi di latte', 100), ('Pera', 150),
        ],
        'dinner': [
            ('Salmone al forno', 180), ('Merluzzo al vapore', 200),
            ('Broccoli', 200), ('Spinaci', 200), ('Zucchine', 150),
            ('Olio extravergine d\'oliva', 10), ('Pane integrale', 40),
            ('Petto di pollo ai ferri', 120),
        ],
    }

    for d_offset in range(7):
        d = date.today() - timedelta(days=d_offset)
        for meal_type, options in templates.items():
            chosen = random.sample(options, k=min(2, len(options)))
            for name, qty in chosen:
                fid = food_id_by_name(name)
                if not fid:
                    continue
                entry = MealEntry(
                    user_id=user.id, food_id=fid,
                    quantity_g=qty + random.randint(-20, 20),
                    meal_type=meal_type, date=d,
                )
                db.session.add(entry)

    for d_offset in range(7):
        d = date.today() - timedelta(days=d_offset)
        for _ in range(random.randint(3, 6)):
            we = WaterEntry(user_id=user.id, amount_ml=random.choice([200, 250, 300, 350]), date=d)
            db.session.add(we)
    db.session.commit()

    for d_offset in [0, 7, 14, 21, 28]:
        d = date.today() - timedelta(days=d_offset)
        m = Measurement(
            user_id=user.id, date=d,
            waist_cm=round(94 - d_offset * 0.15, 1),
            hips_cm=round(106 - d_offset * 0.1, 1),
        )
        db.session.add(m)
    db.session.commit()

    activities = [
        ('running_moderate', 35, 6),
        ('running_easy', 30, 5),
        ('running_moderate', 40, 7),
        ('strength', 20, 0),
        ('walking_brisk', 45, 4),
    ]
    for d_offset in range(28):
        d = date.today() - timedelta(days=d_offset)
        if d.weekday() in (0, 2, 4):
            act, dur, dist = random.choice(activities)
            intensity = 'moderate' if 'moderate' in act else ('easy' if 'easy' in act or 'walking' in act else 'hard')
            from nutrition import calories_burned
            weight = user.current_weight or 88
            kcal = calories_burned(act, dur, weight)
            wo = WorkoutEntry(
                user_id=user.id, activity_type=act,
                duration_min=dur, distance_km=dist,
                intensity=intensity, calories_burned=kcal,
                date=d, note='Demo workout',
            )
            db.session.add(wo)
    db.session.commit()

    goal = Goal(
        user_id=user.id,
        goal_type='workouts',
        target=4,
        current=2,
        week_start=date.today() - timedelta(days=date.today().weekday()),
    )
    db.session.add(goal)
    db.session.commit()

    print(f'Demo user created: {demo_email} / demo1234')
    print(f'  - 30 days of weight logs')
    print(f'  - 7 days of meal entries')
    print(f'  - ~12 workouts in last 4 weeks')
    print(f'  - Water entries and measurements')
    print(f'  - Active weekly goal')


def main():
    with app.app_context():
        db.create_all()
        print('Tables created.')

        n = populate_foods(db)
        print(f'Foods populated: {n} foods inserted (total: {Food.query.count()}).')

        create_demo_user()

    print('\nDatabase ready! Run: python app.py')
    print('Then visit: http://localhost:5000')


if __name__ == '__main__':
    main()
