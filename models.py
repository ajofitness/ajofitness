from datetime import datetime, date, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    gender = db.Column(db.String(10), nullable=False, default='M')
    height_cm = db.Column(db.Float, nullable=False, default=175)
    birth_date = db.Column(db.Date, nullable=False, default=date(1990, 1, 1))
    activity_level = db.Column(db.String(20), nullable=False, default='moderate')
    target_weight_kg = db.Column(db.Float, nullable=False, default=75.0)
    deficit_kcal = db.Column(db.Integer, nullable=False, default=500)
    start_date = db.Column(db.Date, nullable=False, default=date.today)
    created_at = db.Column(db.DateTime, default=utcnow)
    is_demo = db.Column(db.Boolean, default=False)
    onboarding_done = db.Column(db.Boolean, default=False)
    dark_mode = db.Column(db.Boolean, default=True)
    diet_type = db.Column(db.String(20), default='balanced')
    macro_protein_pct = db.Column(db.Float, nullable=True)
    macro_carbs_pct = db.Column(db.Float, nullable=True)
    macro_fat_pct = db.Column(db.Float, nullable=True)

    google_access_token = db.Column(db.Text, nullable=True)
    google_refresh_token = db.Column(db.Text, nullable=True)
    google_token_expiry = db.Column(db.DateTime, nullable=True)
    last_sync_at = db.Column(db.DateTime, nullable=True)
    approved = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)

    weight_logs = db.relationship('WeightLog', backref='user', lazy='dynamic',
                                  cascade='all, delete-orphan')
    meal_entries = db.relationship('MealEntry', backref='user', lazy='dynamic',
                                   cascade='all, delete-orphan')
    workout_entries = db.relationship('WorkoutEntry', backref='user', lazy='dynamic',
                                      cascade='all, delete-orphan')
    water_entries = db.relationship('WaterEntry', backref='user', lazy='dynamic',
                                    cascade='all, delete-orphan')
    measurements = db.relationship('Measurement', backref='user', lazy='dynamic',
                                   cascade='all, delete-orphan')
    custom_foods = db.relationship('CustomFood', backref='user', lazy='dynamic',
                                   cascade='all, delete-orphan')
    goals = db.relationship('Goal', backref='user', lazy='dynamic',
                            cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def age(self):
        today = date.today()
        return today.year - self.birth_date.year - (
            (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
        )

    @property
    def current_weight(self):
        latest = self.weight_logs.order_by(WeightLog.date.desc()).first()
        return latest.weight if latest else None

    @property
    def starting_weight(self):
        first = self.weight_logs.order_by(WeightLog.date.asc()).first()
        return first.weight if first else None

    @property
    def bmi(self):
        w = self.current_weight
        if not w:
            return None
        h = self.height_cm / 100
        return round(w / (h * h), 1)

    def __repr__(self):
        return f'<User {self.email}>'


class WeightLog(db.Model):
    __tablename__ = 'weight_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    weight = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    note = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=utcnow)

    __table_args__ = (db.UniqueConstraint('user_id', 'date', name='_user_date_uc'),)


class Food(db.Model):
    __tablename__ = 'foods'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, index=True)
    category = db.Column(db.String(40), nullable=False)
    kcal_per_100g = db.Column(db.Float, nullable=False)
    protein_g = db.Column(db.Float, nullable=False, default=0)
    carbs_g = db.Column(db.Float, nullable=False, default=0)
    fat_g = db.Column(db.Float, nullable=False, default=0)
    fiber_g = db.Column(db.Float, nullable=False, default=0)
    default_portion_g = db.Column(db.Float, nullable=False, default=100)


class CustomFood(db.Model):
    __tablename__ = 'custom_foods'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(40), nullable=False, default='Altro')
    kcal_per_100g = db.Column(db.Float, nullable=False)
    protein_g = db.Column(db.Float, nullable=False, default=0)
    carbs_g = db.Column(db.Float, nullable=False, default=0)
    fat_g = db.Column(db.Float, nullable=False, default=0)
    fiber_g = db.Column(db.Float, nullable=False, default=0)
    default_portion_g = db.Column(db.Float, nullable=False, default=100)
    created_at = db.Column(db.DateTime, default=utcnow)


class MealEntry(db.Model):
    __tablename__ = 'meal_entries'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    food_id = db.Column(db.Integer, db.ForeignKey('foods.id'), nullable=True)
    custom_food_id = db.Column(db.Integer, db.ForeignKey('custom_foods.id'), nullable=True)
    quantity_g = db.Column(db.Float, nullable=False)
    meal_type = db.Column(db.String(20), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    created_at = db.Column(db.DateTime, default=utcnow)

    food = db.relationship('Food', foreign_keys=[food_id])
    custom_food = db.relationship('CustomFood', foreign_keys=[custom_food_id])

    @property
    def display_name(self):
        if self.food:
            return self.food.name
        if self.custom_food:
            return self.custom_food.name
        return 'Sconosciuto'

    @property
    def kcal(self):
        if self.food:
            return round(self.food.kcal_per_100g * self.quantity_g / 100, 1)
        if self.custom_food:
            return round(self.custom_food.kcal_per_100g * self.quantity_g / 100, 1)
        return 0

    @property
    def protein(self):
        if self.food:
            return round(self.food.protein_g * self.quantity_g / 100, 1)
        if self.custom_food:
            return round(self.custom_food.protein_g * self.quantity_g / 100, 1)
        return 0

    @property
    def carbs(self):
        if self.food:
            return round(self.food.carbs_g * self.quantity_g / 100, 1)
        if self.custom_food:
            return round(self.custom_food.carbs_g * self.quantity_g / 100, 1)
        return 0

    @property
    def fat(self):
        if self.food:
            return round(self.food.fat_g * self.quantity_g / 100, 1)
        if self.custom_food:
            return round(self.custom_food.fat_g * self.quantity_g / 100, 1)
        return 0


class WaterEntry(db.Model):
    __tablename__ = 'water_entries'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount_ml = db.Column(db.Integer, nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    created_at = db.Column(db.DateTime, default=utcnow)


class Measurement(db.Model):
    __tablename__ = 'measurements'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    waist_cm = db.Column(db.Float, nullable=True)
    hips_cm = db.Column(db.Float, nullable=True)
    chest_cm = db.Column(db.Float, nullable=True)
    arm_cm = db.Column(db.Float, nullable=True)
    thigh_cm = db.Column(db.Float, nullable=True)
    note = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=utcnow)

    __table_args__ = (db.UniqueConstraint('user_id', 'date', name='_meas_user_date_uc'),)


class WorkoutEntry(db.Model):
    __tablename__ = 'workout_entries'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    activity_type = db.Column(db.String(40), nullable=False)
    duration_min = db.Column(db.Integer, nullable=False)
    distance_km = db.Column(db.Float, default=0)
    intensity = db.Column(db.String(20), default='moderate')
    calories_burned = db.Column(db.Float, nullable=False, default=0)
    date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    note = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=utcnow)


class Goal(db.Model):
    __tablename__ = 'goals'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    goal_type = db.Column(db.String(30), nullable=False)
    target = db.Column(db.Float, nullable=False)
    current = db.Column(db.Float, nullable=False, default=0)
    week_start = db.Column(db.Date, nullable=False, default=date.today)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utcnow)


class Badge(db.Model):
    __tablename__ = 'badges'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    badge_type = db.Column(db.String(40), nullable=False)
    earned_at = db.Column(db.DateTime, default=utcnow)
    __table_args__ = (db.UniqueConstraint('user_id', 'badge_type', name='_user_badge_uc'),)


class ProgressPhoto(db.Model):
    __tablename__ = 'progress_photos'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    photo_front = db.Column(db.String(256), nullable=True)
    photo_side = db.Column(db.String(256), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow)


class FastingEntry(db.Model):
    __tablename__ = 'fasting_entries'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=True)
    planned_hours = db.Column(db.Float, nullable=False, default=16)
    completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=utcnow)

    @property
    def duration_hours(self):
        if self.end_time:
            return round((self.end_time - self.start_time).total_seconds() / 3600, 1)
        return None

    @property
    def progress_pct(self):
        if self.end_time:
            return 100
        elapsed = (utcnow() - self.start_time).total_seconds() / 3600
        return min(100, round(elapsed / self.planned_hours * 100, 0))


class Program(db.Model):
    __tablename__ = 'programs'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=False)
    duration_days = db.Column(db.Integer, nullable=False)
    difficulty = db.Column(db.String(20), nullable=False, default='beginner')
    goal_type = db.Column(db.String(50), nullable=False)
    diet_type = db.Column(db.String(20), nullable=True)
    deficit_kcal = db.Column(db.Integer, nullable=True)
    workout_freq_per_week = db.Column(db.Integer, nullable=True, default=3)
    water_target_ml = db.Column(db.Integer, nullable=True, default=2000)
    fasting_hours = db.Column(db.Integer, nullable=True, default=0)
    color = db.Column(db.String(7), nullable=True, default='#ff6b35')
    icon = db.Column(db.String(50), nullable=True, default='bi-star')
    is_active = db.Column(db.Boolean, default=True)
    order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=utcnow)

    enrollments = db.relationship('ProgramEnrollment', backref='program', lazy='dynamic',
                                  cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Program {self.name}>'


class ProgramEnrollment(db.Model):
    __tablename__ = 'program_enrollments'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    program_id = db.Column(db.Integer, db.ForeignKey('programs.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False, default=date.today)
    end_date = db.Column(db.Date, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    completed = db.Column(db.Boolean, default=False)
    current_day = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=utcnow)

    user = db.relationship('User', backref=db.backref('program_enrollments', lazy='dynamic',
                                                        cascade='all, delete-orphan'))

    def __repr__(self):
        return f'<ProgramEnrollment user={self.user_id} program={self.program_id}>'


class SyncLog(db.Model):
    __tablename__ = 'sync_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    provider = db.Column(db.String(30), nullable=False, default='google_fit')
    status = db.Column(db.String(20), nullable=False, default='success')
    message = db.Column(db.Text, nullable=True)
    workouts_imported = db.Column(db.Integer, default=0)
    weight_logs_imported = db.Column(db.Integer, default=0)
    started_at = db.Column(db.DateTime, default=utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship('User', backref=db.backref('sync_logs', lazy='dynamic',
                                                        cascade='all, delete-orphan'))


class DailyActivity(db.Model):
    __tablename__ = 'daily_activity'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    steps = db.Column(db.Integer, default=0)
    calories_burned = db.Column(db.Float, default=0.0)
    heart_rate_avg = db.Column(db.Float, nullable=True)
    heart_rate_max = db.Column(db.Float, nullable=True)
    heart_rate_min = db.Column(db.Float, nullable=True)
    distance_km = db.Column(db.Float, default=0.0)
    active_minutes = db.Column(db.Integer, default=0)
    source = db.Column(db.String(30), default='google_fit')
    created_at = db.Column(db.DateTime, default=utcnow)

    __table_args__ = (db.UniqueConstraint('user_id', 'date', name='uq_user_date'),)

    user = db.relationship('User', backref=db.backref('daily_activity', lazy='dynamic',
                                                        cascade='all, delete-orphan'))

    def __repr__(self):
        return f'<DailyActivity {self.date} steps={self.steps} kcal={self.calories_burned}>'
