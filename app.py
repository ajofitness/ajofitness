import os
import sys
import csv
import io
import json
import logging
import base64
from datetime import datetime, date, timedelta
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, Response
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect, generate_csrf
from sqlalchemy import desc, func

from config import Config
from models import db, User, WeightLog, Food, CustomFood, MealEntry, WaterEntry, Measurement, WorkoutEntry, Goal, Badge, ProgressPhoto, FastingEntry, Program, ProgramEnrollment, utcnow
from nutrition import (
    build_plan, calculate_bmr, calculate_tdee, calculate_bmi, bmi_category,
    calories_burned, ACTIVITY_LABELS, ACTIVITY_METS, ACTIVITY_LABELS_IT,
    macro_summary_for_meals, DEFICIT_PRESETS, DIET_PRESETS, body_fat_percentage,
    calculate_streak, check_new_badges, BADGE_DEFINITIONS, adapt_plan_from_history,
    generate_coach_messages, seed_programs, get_program_progress, get_daily_checklist,
)
from foods_data import populate_foods

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('ajo')


def _migrate_schema(engine):
    """Add missing columns to existing tables (for schema upgrades)."""
    import sqlalchemy as sa
    inspector = sa.inspect(engine)

    columns = {c['name'] for c in inspector.get_columns('users')}
    additions = {
        'diet_type': 'VARCHAR(20) DEFAULT "balanced"',
        'macro_protein_pct': 'FLOAT',
        'macro_carbs_pct': 'FLOAT',
        'macro_fat_pct': 'FLOAT',
        'google_access_token': 'TEXT',
        'google_refresh_token': 'TEXT',
        'google_token_expiry': 'DATETIME',
        'last_sync_at': 'DATETIME',
    }
    for col, col_type in additions.items():
        if col not in columns:
            with engine.connect() as conn:
                conn.execute(sa.text(f'ALTER TABLE users ADD COLUMN {col} {col_type}'))
                conn.commit()
                logger.info(f'Added column {col} to users table')


_IT_DAYS = ['lunedì', 'martedì', 'mercoledì', 'giovedì', 'venerdì', 'sabato', 'domenica']
_IT_MONTHS = ['gennaio', 'febbraio', 'marzo', 'aprile', 'maggio', 'giugno', 'luglio', 'agosto', 'settembre', 'ottobre', 'novembre', 'dicembre']

def date_italian(d):
    return f"{_IT_DAYS[d.weekday()]} {d.day} {_IT_MONTHS[d.month - 1]} {d.year}"


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    with app.app_context():
        db.create_all()
        _migrate_schema(db.engine)

    csrf = CSRFProtect()
    csrf.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = 'login'
    login_manager.login_message = 'Accedi per continuare.'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.context_processor
    def inject_globals():
        return {
            'APP_NAME': 'Ajò',
            'current_year': datetime.now().year,
            'today': date.today,
            'timedelta': timedelta,
            'csrf_token': generate_csrf,
            'date_italian': date_italian,
        }

    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return render_template('landing.html')

    @app.route('/manifest.json')
    def manifest():
        return app.send_static_file('manifest.json')

    @app.route('/sw.js')
    def service_worker():
        return app.send_static_file('sw.js')

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            name = request.form.get('name', '').strip()
            gender = request.form.get('gender', 'M')
            height = float(request.form.get('height', 175))
            target_weight = float(request.form.get('target_weight', 75))
            birth = request.form.get('birth_date', '1990-01-01')
            activity = request.form.get('activity', 'moderate')
            deficit = int(request.form.get('deficit', 500))

            try:
                from email_validator import validate_email, EmailNotValidError
                validate_email(email, check_deliverability=False)
            except EmailNotValidError:
                flash('Email non valida.', 'danger')
                return redirect(url_for('register'))

            if User.query.filter_by(email=email).first():
                flash('Email già registrata. Accedi.', 'warning')
                return redirect(url_for('login'))
            if len(password) < 6:
                flash('Password troppo corta (min 6 caratteri).', 'danger')
                return redirect(url_for('register'))
            if height < 80 or height > 250:
                flash('Altezza non valida.', 'danger')
                return redirect(url_for('register'))
            if target_weight < 30 or target_weight > 400:
                flash('Peso obiettivo non valido.', 'danger')
                return redirect(url_for('register'))

            user = User(
                email=email, name=name, gender=gender,
                height_cm=height, target_weight_kg=target_weight,
                birth_date=date.fromisoformat(birth),
                activity_level=activity, deficit_kcal=deficit,
            )
            user.set_password(password)
            db.session.add(user)
            db.session.commit()

            starting_weight = float(request.form.get('current_weight', 80))
            if 30 <= starting_weight <= 400:
                wl = WeightLog(user_id=user.id, weight=starting_weight, date=date.today())
                db.session.add(wl)
                db.session.commit()

            login_user(user)
            flash(f'Benvenuto {name}! Pronto per iniziare?', 'success')
            return redirect(url_for('onboarding'))
        return render_template('register.html',
                               activity_options=ACTIVITY_LABELS,
                               deficit_options=DEFICIT_PRESETS)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            user = User.query.filter_by(email=email).first()
            if user and user.check_password(password):
                login_user(user)
                flash(f'Bentornato, {user.name}!', 'success')
                next_page = request.args.get('next') or url_for('dashboard')
                return redirect(next_page)
            flash('Credenziali non valide.', 'danger')
        return render_template('login.html')

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('Disconnesso. A presto!', 'info')
        return redirect(url_for('index'))

    @app.route('/login-demo')
    def login_demo():
        user = User.query.filter_by(is_demo=True).first()
        if not user:
            db.create_all()
            from init_db import create_demo_user
            populate_foods(db)
            create_demo_user()
            user = User.query.filter_by(is_demo=True).first()
        if user:
            login_user(user)
            flash('Sei loggato come utente DEMO.', 'success')
            return redirect(url_for('dashboard'))
        flash('Utente demo non trovato. Esegui init_db.py', 'warning')
        return redirect(url_for('login'))

    @app.route('/onboarding')
    @login_required
    def onboarding():
        return render_template('onboarding.html')

    @app.route('/onboarding/done', methods=['POST'])
    @login_required
    def onboarding_done():
        current_user.onboarding_done = True
        db.session.commit()
        flash('Configurazione completata!', 'success')
        return redirect(url_for('dashboard'))

    @app.route('/dashboard')
    @login_required
    def dashboard():
        if not current_user.onboarding_done and not current_user.is_demo:
            return redirect(url_for('onboarding'))

        w = current_user.current_weight
        if not w:
            return redirect(url_for('profile'))

        bmi_val = calculate_bmi(w, current_user.height_cm)

        plan = build_plan(
            weight_kg=w,
            target_weight_kg=current_user.target_weight_kg,
            height_cm=current_user.height_cm,
            age=current_user.age,
            gender=current_user.gender,
            activity_level=current_user.activity_level,
            deficit_kcal_day=current_user.deficit_kcal,
            diet_type=current_user.diet_type,
            custom_macros=(
                current_user.macro_protein_pct,
                current_user.macro_carbs_pct,
                current_user.macro_fat_pct,
            ) if current_user.macro_protein_pct else None,
        )
        today_d = date.today()
        today_meals = MealEntry.query.filter_by(user_id=current_user.id, date=today_d).all()
        today_workouts = WorkoutEntry.query.filter_by(user_id=current_user.id, date=today_d).all()
        macros_today = macro_summary_for_meals(today_meals)
        kcal_burned_today = sum(wo.calories_burned for wo in today_workouts)
        kcal_net = macros_today['kcal'] - kcal_burned_today

        seven_days_ago = today_d - timedelta(days=7)
        weight_history = WeightLog.query.filter(
            WeightLog.user_id == current_user.id,
            WeightLog.date >= seven_days_ago
        ).order_by(WeightLog.date.asc()).all()

        # Full weight history for trend
        all_weight_logs = WeightLog.query.filter_by(user_id=current_user.id).order_by(WeightLog.date.asc()).all()
        recent_loss_rate = None
        if len(all_weight_logs) >= 4:
            oldest = all_weight_logs[-min(len(all_weight_logs), 14)]
            newest = all_weight_logs[-1]
            days_span = (newest.date - oldest.date).days
            if days_span >= 7:
                recent_loss_rate = round((oldest.weight - newest.weight) / (days_span / 7), 2)
                recent_loss_rate = max(0, recent_loss_rate)

        adapted_plan = adapt_plan_from_history(plan, recent_loss_rate)

        progress_pct = 0
        starting = current_user.starting_weight
        if starting and starting != w:
            total_to_lose = starting - current_user.target_weight_kg
            if total_to_lose > 0:
                progress_pct = round((starting - w) / total_to_lose * 100, 1)
                progress_pct = max(0, min(100, progress_pct))

        today_water = WaterEntry.query.filter_by(user_id=current_user.id, date=today_d).all()
        total_water_ml = sum(wa.amount_ml for wa in today_water)

        weekly_goal = Goal.query.filter_by(
            user_id=current_user.id, is_active=True,
        ).order_by(Goal.created_at.desc()).first()

        # Streak
        all_dates = set()
        for row in MealEntry.query.filter_by(user_id=current_user.id).with_entities(MealEntry.date).all():
            all_dates.add(row[0])
        for row in WorkoutEntry.query.filter_by(user_id=current_user.id).with_entities(WorkoutEntry.date).all():
            all_dates.add(row[0])
        for row in WeightLog.query.filter_by(user_id=current_user.id).with_entities(WeightLog.date).all():
            all_dates.add(row[0])
        streak = calculate_streak(list(all_dates))

        # Badges
        new_badges = check_new_badges(current_user, db.session)
        earned_badges = Badge.query.filter_by(user_id=current_user.id).order_by(Badge.earned_at.desc()).all()
        badge_details = [{'type': b.badge_type, **BADGE_DEFINITIONS.get(b.badge_type, {}), 'earned_at': b.earned_at} for b in earned_badges]

        # Body fat
        body_fat = body_fat_percentage(bmi_val, current_user.age, current_user.gender)

        from models import ProgramEnrollment
        active_enrollment = ProgramEnrollment.query.filter_by(
            user_id=current_user.id, is_active=True
        ).first()

        return render_template('dashboard.html',
                               plan=plan, adapted_plan=adapted_plan,
                               weight=w,
                               bmi=bmi_val,
                               bmi_cat=bmi_category(bmi_val),
                               body_fat=body_fat,
                               macros_today=macros_today,
                               kcal_burned_today=kcal_burned_today,
                               kcal_net=kcal_net,
                               progress_pct=progress_pct,
                               weight_history=weight_history,
                               all_weight_logs=all_weight_logs,
                               starting_weight=starting,
                               total_water_ml=total_water_ml,
                               weekly_goal=weekly_goal,
                               streak=streak,
                               badge_details=badge_details,
                               new_badges=new_badges,
                               recent_loss_rate=recent_loss_rate,
                               coach_messages=generate_coach_messages(current_user),
                               active_enrollment=active_enrollment)

    @app.route('/coach')
    @login_required
    def coach():
        messages = generate_coach_messages(current_user)
        return render_template('coach.html', messages=messages)

    @app.route('/api/coach/messages')
    @login_required
    def coach_api():
        messages = generate_coach_messages(current_user)
        return jsonify(messages)

    @app.route('/programs')
    @login_required
    def programs():
        all_programs = Program.query.filter_by(is_active=True).order_by(Program.order).all()
        active_enrollment = ProgramEnrollment.query.filter_by(
            user_id=current_user.id, is_active=True
        ).first()
        return render_template('programs.html', programs=all_programs, active_enrollment=active_enrollment)

    @app.route('/programs/<slug>')
    @login_required
    def program_detail(slug):
        prog = Program.query.filter_by(slug=slug).first_or_404()
        active = ProgramEnrollment.query.filter_by(
            user_id=current_user.id, program_id=prog.id, is_active=True
        ).first()
        return render_template('program_detail.html', program=prog, enrollment=active)

    @app.route('/programs/enroll/<slug>', methods=['POST'])
    @login_required
    def program_enroll(slug):
        prog = Program.query.filter_by(slug=slug).first_or_404()
        existing = ProgramEnrollment.query.filter_by(
            user_id=current_user.id, program_id=prog.id, is_active=True
        ).first()
        if existing:
            flash('Sei già iscritto a questo programma.', 'info')
        else:
            # Deactivate any other active enrollments
            ProgramEnrollment.query.filter_by(user_id=current_user.id, is_active=True).update(
                {ProgramEnrollment.is_active: False}
            )
            enrollment = ProgramEnrollment(
                user_id=current_user.id, program_id=prog.id,
                start_date=date.today(),
                end_date=None if prog.duration_days >= 999 else date.today() + timedelta(days=prog.duration_days),
            )
            db.session.add(enrollment)
            # Apply program settings to user
            if prog.diet_type:
                current_user.diet_type = prog.diet_type
            if prog.deficit_kcal is not None:
                current_user.deficit_kcal = prog.deficit_kcal
            db.session.commit()
            flash(f'Iscritto a "{prog.name}"! Buon percorso!', 'success')
        return redirect(url_for('program_my'))

    @app.route('/programs/my')
    @login_required
    def program_my():
        enrollment = ProgramEnrollment.query.filter_by(
            user_id=current_user.id, is_active=True
        ).first()
        if not enrollment:
            return redirect(url_for('programs'))
        prog = enrollment.program
        progress = get_program_progress(enrollment, current_user)
        checklist = get_daily_checklist(prog, current_user)
        return render_template('my_program.html', program=prog, enrollment=enrollment,
                               progress=progress, checklist=checklist)

    @app.route('/programs/unenroll', methods=['POST'])
    @login_required
    def program_unenroll():
        enrollment = ProgramEnrollment.query.filter_by(
            user_id=current_user.id, is_active=True
        ).first()
        if enrollment:
            enrollment.is_active = False
            db.session.commit()
            flash('Programma terminato.', 'info')
        return redirect(url_for('programs'))

    @app.route('/integrations')
    @login_required
    def integrations():
        from models import SyncLog
        sync_logs = SyncLog.query.filter_by(user_id=current_user.id).order_by(SyncLog.started_at.desc()).limit(10).all()
        return render_template('integrations.html',
                               has_google=bool(current_user.google_access_token),
                               last_sync=current_user.last_sync_at,
                               sync_logs=sync_logs)

    @app.route('/auth/google')
    @login_required
    def auth_google():
        try:
            auth_url, state = generate_auth_url()
            from flask import session as flask_session
            flask_session['google_oauth_state'] = state
            return redirect(auth_url)
        except ValueError as e:
            flash(str(e), 'danger')
            return redirect(url_for('integrations'))

    @app.route('/auth/google/callback')
    @login_required
    def auth_google_callback():
        error = request.args.get('error')
        if error:
            flash(f'Accesso Google negato: {error}', 'danger')
            return redirect(url_for('integrations'))
        from flask import session as flask_session
        state = request.args.get('state')
        saved_state = flask_session.pop('google_oauth_state', None)
        if not state or not saved_state or state != saved_state:
            flash('Errore di sicurezza: state mismatch', 'danger')
            return redirect(url_for('integrations'))
        code = request.args.get('code')
        if not code:
            flash('Nessun codice ricevuto da Google', 'danger')
            return redirect(url_for('integrations'))
        try:
            tokens = exchange_code(code)
            current_user.google_access_token = tokens['access_token']
            current_user.google_refresh_token = tokens.get('refresh_token', current_user.google_refresh_token)
            current_user.google_token_expiry = utcnow() + timedelta(seconds=tokens.get('expires_in', 3600))
            db.session.commit()
            flash('Google Fit collegato con successo!', 'success')
        except ValueError as e:
            flash(str(e), 'danger')
        return redirect(url_for('integrations'))

    @app.route('/auth/google/disconnect', methods=['POST'])
    @login_required
    def auth_google_disconnect():
        current_user.google_access_token = None
        current_user.google_refresh_token = None
        current_user.google_token_expiry = None
        current_user.last_sync_at = None
        db.session.commit()
        flash('Google Fit disconnesso.', 'info')
        return redirect(url_for('integrations'))

    @app.route('/api/sync/google-fit', methods=['POST'])
    @login_required
    def sync_google_fit_route():
        if not current_user.google_access_token:
            flash('Collega prima Google Fit nelle integrazioni.', 'warning')
            return redirect(url_for('integrations'))
        stats = sync_google_fit(current_user, db.session)
        flash(f'Sincronizzazione completata: {stats["workouts"]} allenamenti, {stats["weights"]} pesi importati.', 'success')
        if 'steps' in stats:
            pass
        return redirect(url_for('integrations'))

    @app.route('/water/add', methods=['POST'])
    @login_required
    def water_add():
        amount = int(request.form.get('amount_ml', 250))
        if amount < 50 or amount > 2000:
            flash('Quantità non valida.', 'danger')
            return redirect(url_for('dashboard'))
        we = WaterEntry(user_id=current_user.id, amount_ml=amount, date=date.today())
        db.session.add(we)
        db.session.commit()
        return redirect(url_for('dashboard'))

    @app.route('/diary')
    @login_required
    def diary():
        selected_date_str = request.args.get('date')
        if selected_date_str:
            try:
                selected_date = date.fromisoformat(selected_date_str)
            except ValueError:
                selected_date = date.today()
        else:
            selected_date = date.today()

        meals = MealEntry.query.filter_by(
            user_id=current_user.id, date=selected_date
        ).order_by(MealEntry.created_at.asc()).all()

        meals_by_type = {
            'breakfast': [m for m in meals if m.meal_type == 'breakfast'],
            'lunch': [m for m in meals if m.meal_type == 'lunch'],
            'snack': [m for m in meals if m.meal_type == 'snack'],
            'dinner': [m for m in meals if m.meal_type == 'dinner'],
        }
        totals = macro_summary_for_meals(meals)

        search_q = request.args.get('q', '').strip()
        user_custom = CustomFood.query.filter_by(user_id=current_user.id).order_by(CustomFood.name.asc()).all()

        return render_template('diary.html',
                               selected_date=selected_date,
                               prev_date=selected_date - timedelta(days=1),
                               next_date=selected_date + timedelta(days=1),
                               today_str=date.today().isoformat(),
                               meals_by_type=meals_by_type,
                               totals=totals,
                               foods=[],
                               custom_foods=user_custom,
                               search_q=search_q,
                               categories=[],
                               meal_labels={
                                   'breakfast': 'Colazione',
                                   'lunch': 'Pranzo',
                                   'snack': 'Spuntino',
                                   'dinner': 'Cena',
                               })

    @app.route('/diary/add', methods=['POST'])
    @login_required
    def diary_add():
        food_id = request.form.get('food_id')
        custom_food_id = request.form.get('custom_food_id')
        off_name = request.form.get('off_name', '').strip()
        quantity = float(request.form.get('quantity'))
        meal_type = request.form.get('meal_type')
        meal_date = request.form.get('date')

        if quantity <= 0 or quantity > 5000:
            flash('Quantità non valida.', 'danger')
            return redirect(url_for('diary'))
        if meal_type not in ('breakfast', 'lunch', 'snack', 'dinner'):
            flash('Tipo pasto non valido.', 'danger')
            return redirect(url_for('diary'))

        # If no local food is selected but we have OFF data, create a custom food
        if not food_id and not custom_food_id and off_name:
            cf = CustomFood(
                user_id=current_user.id,
                name=off_name,
                kcal_per_100g=float(request.form.get('off_kcal', 0)),
                protein_g=float(request.form.get('off_protein', 0)),
                carbs_g=float(request.form.get('off_carbs', 0)),
                fat_g=float(request.form.get('off_fat', 0)),
            )
            db.session.add(cf)
            db.session.flush()
            custom_food_id = str(cf.id)

        entry = MealEntry(
            user_id=current_user.id,
            food_id=int(food_id) if food_id else None,
            custom_food_id=int(custom_food_id) if custom_food_id else None,
            quantity_g=quantity,
            meal_type=meal_type,
            date=date.fromisoformat(meal_date) if meal_date else date.today(),
        )
        db.session.add(entry)
        db.session.commit()
        flash('Pasto aggiunto.', 'success')
        return redirect(url_for('diary', date=meal_date))

    @app.route('/diary/delete/<int:entry_id>', methods=['POST'])
    @login_required
    def diary_delete(entry_id):
        entry = MealEntry.query.get_or_404(entry_id)
        if entry.user_id != current_user.id:
            flash('Non autorizzato.', 'danger')
            return redirect(url_for('diary'))
        meal_date = entry.date
        db.session.delete(entry)
        db.session.commit()
        flash('Pasto rimosso.', 'info')
        return redirect(url_for('diary', date=meal_date.isoformat()))

    @app.route('/custom-food/add', methods=['POST'])
    @login_required
    def custom_food_add():
        name = request.form.get('name', '').strip()
        if not name or len(name) < 2:
            flash('Nome alimento non valido.', 'danger')
            return redirect(url_for('diary'))
        existing = CustomFood.query.filter_by(user_id=current_user.id, name=name).first()
        if existing:
            flash('Hai già un alimento con questo nome.', 'warning')
            return redirect(url_for('diary'))
        food = CustomFood(
            user_id=current_user.id,
            name=name,
            category=request.form.get('category', 'Altro'),
            kcal_per_100g=float(request.form.get('kcal', 0)),
            protein_g=float(request.form.get('protein', 0)),
            carbs_g=float(request.form.get('carbs', 0)),
            fat_g=float(request.form.get('fat', 0)),
            fiber_g=float(request.form.get('fiber', 0)),
            default_portion_g=float(request.form.get('portion', 100)),
        )
        db.session.add(food)
        db.session.commit()
        flash(f'Alimento "{name}" creato!', 'success')
        return redirect(url_for('diary'))

    @app.route('/custom-food/delete/<int:food_id>', methods=['POST'])
    @login_required
    def custom_food_delete(food_id):
        food = CustomFood.query.get_or_404(food_id)
        if food.user_id != current_user.id:
            flash('Non autorizzato.', 'danger')
            return redirect(url_for('diary'))
        db.session.delete(food)
        db.session.commit()
        flash('Alimento rimosso.', 'info')
        return redirect(url_for('diary'))

    @app.route('/training')
    @login_required
    def training():
        selected_date_str = request.args.get('date')
        if selected_date_str:
            try:
                selected_date = date.fromisoformat(selected_date_str)
            except ValueError:
                selected_date = date.today()
        else:
            selected_date = date.today()

        workouts = WorkoutEntry.query.filter_by(
            user_id=current_user.id, date=selected_date
        ).order_by(WorkoutEntry.created_at.asc()).all()

        thirty_days_ago = selected_date - timedelta(days=30)
        history = WorkoutEntry.query.filter(
            WorkoutEntry.user_id == current_user.id,
            WorkoutEntry.date >= thirty_days_ago,
            WorkoutEntry.date <= selected_date,
        ).order_by(WorkoutEntry.date.asc()).all()

        return render_template('training.html',
                               selected_date=selected_date,
                               prev_date=selected_date - timedelta(days=1),
                               next_date=selected_date + timedelta(days=1),
                               today_str=date.today().isoformat(),
                               workouts=workouts,
                               history=history,
                               activities=ACTIVITY_LABELS_IT)

    @app.route('/training/add', methods=['POST'])
    @login_required
    def training_add():
        activity_type = request.form.get('activity_type')
        duration = int(request.form.get('duration_min'))
        distance = float(request.form.get('distance_km', 0) or 0)
        intensity = request.form.get('intensity', 'moderate')
        note = request.form.get('note', '')
        workout_date = request.form.get('date')

        weight = current_user.current_weight or 80
        kcal = calories_burned(activity_type, duration, weight)

        wo = WorkoutEntry(
            user_id=current_user.id,
            activity_type=activity_type,
            duration_min=duration,
            distance_km=distance,
            intensity=intensity,
            calories_burned=kcal,
            note=note,
            date=date.fromisoformat(workout_date) if workout_date else date.today(),
        )
        db.session.add(wo)
        db.session.commit()
        flash(f'Allenamento registrato. {int(kcal)} kcal bruciate.', 'success')
        return redirect(url_for('training', date=workout_date))

    @app.route('/training/delete/<int:wo_id>', methods=['POST'])
    @login_required
    def training_delete(wo_id):
        wo = WorkoutEntry.query.get_or_404(wo_id)
        if wo.user_id != current_user.id:
            flash('Non autorizzato.', 'danger')
            return redirect(url_for('training'))
        wo_date = wo.date
        db.session.delete(wo)
        db.session.commit()
        flash('Allenamento rimosso.', 'info')
        return redirect(url_for('training', date=wo_date.isoformat()))

    @app.route('/progress')
    @login_required
    def progress():
        all_logs = WeightLog.query.filter_by(user_id=current_user.id)\
            .order_by(WeightLog.date.asc()).all()
        all_measurements = Measurement.query.filter_by(user_id=current_user.id)\
            .order_by(Measurement.date.asc()).all()
        return render_template('progress.html',
                               weight_logs=all_logs,
                               measurements=all_measurements)

    @app.route('/progress/add-weight', methods=['POST'])
    @login_required
    def progress_add_weight():
        weight = float(request.form.get('weight'))
        log_date = request.form.get('date', date.today().isoformat())
        note = request.form.get('note', '')

        if weight < 30 or weight > 400:
            flash('Peso non valido.', 'danger')
            return redirect(url_for('progress'))

        existing = WeightLog.query.filter_by(
            user_id=current_user.id, date=date.fromisoformat(log_date)
        ).first()
        if existing:
            existing.weight = weight
            existing.note = note
            flash('Peso aggiornato per questa data.', 'info')
        else:
            wl = WeightLog(
                user_id=current_user.id, weight=weight,
                date=date.fromisoformat(log_date), note=note,
            )
            db.session.add(wl)
            flash('Peso registrato.', 'success')
        db.session.commit()
        return redirect(url_for('progress'))

    @app.route('/progress/measure', methods=['POST'])
    @login_required
    def progress_measure():
        meas_date = request.form.get('date', date.today().isoformat())
        existing = Measurement.query.filter_by(
            user_id=current_user.id, date=date.fromisoformat(meas_date)
        ).first()
        data = {
            'waist_cm': request.form.get('waist_cm'),
            'hips_cm': request.form.get('hips_cm'),
            'chest_cm': request.form.get('chest_cm'),
            'arm_cm': request.form.get('arm_cm'),
            'thigh_cm': request.form.get('thigh_cm'),
            'note': request.form.get('note', ''),
        }
        for k in ('waist_cm', 'hips_cm', 'chest_cm', 'arm_cm', 'thigh_cm'):
            if data[k] == '':
                data[k] = None
            else:
                data[k] = float(data[k])

        if existing:
            for k, v in data.items():
                setattr(existing, k, v)
            flash('Misure aggiornate.', 'info')
        else:
            m = Measurement(user_id=current_user.id, date=date.fromisoformat(meas_date), **data)
            db.session.add(m)
            flash('Misure registrate.', 'success')
        db.session.commit()
        return redirect(url_for('progress'))

    @app.route('/plan')
    @login_required
    def plan():
        w = current_user.current_weight
        deficit_str = request.args.get('deficit', '')
        deficit = int(deficit_str) if deficit_str and deficit_str.isdigit() else current_user.deficit_kcal

        if not w:
            return redirect(url_for('profile'))
        plan = build_plan(
            weight_kg=w,
            target_weight_kg=current_user.target_weight_kg,
            height_cm=current_user.height_cm,
            age=current_user.age,
            gender=current_user.gender,
            activity_level=current_user.activity_level,
            deficit_kcal_day=deficit,
            diet_type=current_user.diet_type,
            custom_macros=(
                current_user.macro_protein_pct,
                current_user.macro_carbs_pct,
                current_user.macro_fat_pct,
            ) if current_user.macro_protein_pct else None,
        )
        weeks_to_target = plan.days_to_target // 7 if plan.days_to_target > 0 else 0
        return render_template('plan.html',
                               plan=plan,
                               weeks_to_target=weeks_to_target,
                               activity_label=ACTIVITY_LABELS.get(current_user.activity_level, ''),
                               deficit_options=DEFICIT_PRESETS,
                               diet_options=DIET_PRESETS,
                               current_deficit=deficit,
                               current_diet=current_user.diet_type,
                               custom_protein=current_user.macro_protein_pct,
                               custom_carbs=current_user.macro_carbs_pct,
                               custom_fat=current_user.macro_fat_pct)

    @app.route('/plan/save-deficit', methods=['POST'])
    @login_required
    def plan_save_deficit():
        deficit = int(request.form.get('deficit', 500))
        if deficit not in (250, 500, 750, 1000):
            flash('Deficit non valido.', 'danger')
            return redirect(url_for('plan'))
        current_user.deficit_kcal = deficit
        db.session.commit()
        flash(f'Deficit impostato a {deficit} kcal/giorno.', 'success')
        return redirect(url_for('plan'))

    @app.route('/plan/save-diet', methods=['POST'])
    @login_required
    def plan_save_diet():
        diet_type = request.form.get('diet_type', 'balanced')
        if diet_type not in DIET_PRESETS:
            flash('Tipo di dieta non valido.', 'danger')
            return redirect(url_for('plan'))
        current_user.diet_type = diet_type
        if request.form.get('custom_macros'):
            try:
                p = float(request.form.get('protein_pct', 0))
                c = float(request.form.get('carbs_pct', 0))
                f = float(request.form.get('fat_pct', 0))
                if abs(p + c + f - 100) < 1 and p > 0 and c > 0 and f > 0:
                    current_user.macro_protein_pct = p
                    current_user.macro_carbs_pct = c
                    current_user.macro_fat_pct = f
                else:
                    flash('Le percentuali devono sommare a 100.', 'danger')
                    return redirect(url_for('plan'))
            except ValueError:
                flash('Valori non validi.', 'danger')
                return redirect(url_for('plan'))
        else:
            current_user.macro_protein_pct = None
            current_user.macro_carbs_pct = None
            current_user.macro_fat_pct = None
        db.session.commit()
        flash('Impostazioni dieta salvate.', 'success')
        return redirect(url_for('plan'))

    @app.route('/goals')
    @login_required
    def goals():
        active_goals = Goal.query.filter_by(user_id=current_user.id, is_active=True).all()
        past_goals = Goal.query.filter_by(user_id=current_user.id, is_active=False).order_by(Goal.created_at.desc()).limit(10).all()
        today_d = date.today()
        week_start = today_d - timedelta(days=today_d.weekday())
        return render_template('goals.html',
                               active_goals=active_goals,
                               past_goals=past_goals,
                               week_start=week_start)

    @app.route('/goals/add', methods=['POST'])
    @login_required
    def goals_add():
        goal_type = request.form.get('goal_type')
        target = float(request.form.get('target'))
        if target <= 0:
            flash('Target non valido.', 'danger')
            return redirect(url_for('goals'))
        valid_types = {'workouts', 'water_days', 'calorie_days', 'weight_loss'}
        if goal_type not in valid_types:
            flash('Tipo obiettivo non valido.', 'danger')
            return redirect(url_for('goals'))
        today_d = date.today()
        week_start = today_d - timedelta(days=today_d.weekday())
        goal = Goal(
            user_id=current_user.id,
            goal_type=goal_type,
            target=target,
            current=0,
            week_start=week_start,
        )
        db.session.add(goal)
        db.session.commit()
        flash('Obiettivo settimanale creato!', 'success')
        return redirect(url_for('goals'))

    @app.route('/goals/progress/<int:goal_id>', methods=['POST'])
    @login_required
    def goals_progress(goal_id):
        goal = Goal.query.get_or_404(goal_id)
        if goal.user_id != current_user.id:
            flash('Non autorizzato.', 'danger')
            return redirect(url_for('goals'))
        amount = float(request.form.get('amount', 1))
        goal.current += amount
        if goal.current >= goal.target:
            goal.is_active = False
            flash(f'Obiettivo "{goal.goal_type}" raggiunto!', 'success')
        else:
            flash('Progresso aggiornato.', 'info')
        db.session.commit()
        return redirect(url_for('goals'))

    @app.route('/profile', methods=['GET', 'POST'])
    @login_required
    def profile():
        if request.method == 'POST':
            current_user.name = request.form.get('name', current_user.name)
            current_user.gender = request.form.get('gender', current_user.gender)
            current_user.height_cm = float(request.form.get('height', current_user.height_cm))
            current_user.target_weight_kg = float(request.form.get('target_weight', current_user.target_weight_kg))
            current_user.activity_level = request.form.get('activity', current_user.activity_level)
            birth = request.form.get('birth_date')
            if birth:
                current_user.birth_date = date.fromisoformat(birth)
            db.session.commit()
            flash('Profilo aggiornato.', 'success')
            return redirect(url_for('profile'))
        return render_template('profile.html',
                               activity_options=ACTIVITY_LABELS)

    @app.route('/export')
    @login_required
    def export_data():
        return render_template('export.html')

    @app.route('/export/csv/<string:data_type>')
    @login_required
    def export_csv(data_type):
        output = io.StringIO()
        writer = csv.writer(output)

        if data_type == 'weight':
            writer.writerow(['Data', 'Peso (kg)', 'Note'])
            for log in WeightLog.query.filter_by(user_id=current_user.id).order_by(WeightLog.date.asc()).all():
                writer.writerow([log.date.isoformat(), log.weight, log.note or ''])
            filename = 'peso.csv'

        elif data_type == 'measurements':
            writer.writerow(['Data', 'Vita (cm)', 'Fianchi (cm)', 'Petto (cm)', 'Braccio (cm)', 'Coscia (cm)'])
            for m in Measurement.query.filter_by(user_id=current_user.id).order_by(Measurement.date.asc()).all():
                writer.writerow([m.date.isoformat(),
                                m.waist_cm or '', m.hips_cm or '',
                                m.chest_cm or '', m.arm_cm or '', m.thigh_cm or ''])
            filename = 'misure.csv'

        elif data_type == 'meals':
            writer.writerow(['Data', 'Pasto', 'Alimento', 'Quantità (g)', 'Kcal', 'Proteine', 'Carboidrati', 'Grassi'])
            for entry in MealEntry.query.filter_by(user_id=current_user.id).order_by(MealEntry.date.asc()).all():
                writer.writerow([entry.date.isoformat(), entry.meal_type,
                                entry.display_name, entry.quantity_g,
                                entry.kcal, entry.protein, entry.carbs, entry.fat])
            filename = 'pasti.csv'

        elif data_type == 'workouts':
            writer.writerow(['Data', 'Attività', 'Durata (min)', 'Distanza (km)', 'Kcal bruciate', 'Note'])
            for wo in WorkoutEntry.query.filter_by(user_id=current_user.id).order_by(WorkoutEntry.date.asc()).all():
                writer.writerow([wo.date.isoformat(), wo.activity_type,
                                wo.duration_min, wo.distance_km or 0,
                                wo.calories_burned, wo.note or ''])
            filename = 'allenamenti.csv'

        else:
            flash('Tipo di esportazione non valido.', 'danger')
            return redirect(url_for('export_data'))

        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment;filename={filename}'},
        )

    @app.route('/toggle-dark-mode', methods=['POST'])
    @login_required
    def toggle_dark_mode():
        current_user.dark_mode = not current_user.dark_mode
        db.session.commit()
        return redirect(request.referrer or url_for('dashboard'))

    @app.route('/fasting')
    @login_required
    def fasting():
        active_fast = FastingEntry.query.filter_by(
            user_id=current_user.id, end_time=None
        ).order_by(FastingEntry.start_time.desc()).first()

        history = FastingEntry.query.filter_by(
            user_id=current_user.id, completed=True
        ).order_by(FastingEntry.date.desc()).limit(30).all()

        completed_count = FastingEntry.query.filter_by(
            user_id=current_user.id, completed=True
        ).count()

        earned_badges = Badge.query.filter_by(user_id=current_user.id).order_by(Badge.earned_at.desc()).all()
        badge_details = [{'type': b.badge_type, **BADGE_DEFINITIONS.get(b.badge_type, {}), 'earned_at': b.earned_at} for b in earned_badges]

        return render_template('fasting.html',
                               active_fast=active_fast,
                               history=history,
                               completed_count=completed_count,
                               badge_details=badge_details)

    @app.route('/api/fasting/start', methods=['POST'])
    @csrf.exempt
    @login_required
    def api_fasting_start():
        data = request.get_json() or {}
        planned_hours = float(data.get('hours', 16))
        if planned_hours < 1 or planned_hours > 168:
            return jsonify({'ok': False, 'error': 'Durata non valida (1-168 ore)'}), 400

        active = FastingEntry.query.filter_by(
            user_id=current_user.id, end_time=None
        ).first()
        if active:
            return jsonify({'ok': False, 'error': 'Digiuno già attivo'}), 400

        entry = FastingEntry(
            user_id=current_user.id,
            date=date.today(),
            start_time=utcnow(),
            planned_hours=planned_hours,
        )
        db.session.add(entry)
        db.session.commit()
        return jsonify({
            'ok': True,
            'start_time': entry.start_time.isoformat(),
            'planned_hours': planned_hours,
        })

    @app.route('/api/fasting/stop', methods=['POST'])
    @csrf.exempt
    @login_required
    def api_fasting_stop():
        active = FastingEntry.query.filter_by(
            user_id=current_user.id, end_time=None
        ).first()
        if not active:
            return jsonify({'ok': False, 'error': 'Nessun digiuno attivo'}), 400

        now = utcnow()
        active.end_time = now
        active.completed = True
        db.session.commit()

        duration = round((now - active.start_time).total_seconds() / 3600, 1)
        return jsonify({'ok': True, 'duration_hours': duration})

    @app.route('/api/fasting/status')
    @login_required
    def api_fasting_status():
        active = FastingEntry.query.filter_by(
            user_id=current_user.id, end_time=None
        ).first()
        if not active:
            return jsonify({'active': False})
        elapsed = (utcnow() - active.start_time).total_seconds() / 3600
        remaining = max(0, active.planned_hours - elapsed)
        return jsonify({
            'active': True,
            'start_time': active.start_time.isoformat(),
            'planned_hours': active.planned_hours,
            'elapsed_hours': round(elapsed, 2),
            'remaining_hours': round(remaining, 2),
            'progress_pct': min(100, round(elapsed / active.planned_hours * 100, 0)),
        })

    @app.route('/api/fasting/delete/<int:entry_id>', methods=['POST'])
    @csrf.exempt
    @login_required
    def api_fasting_delete(entry_id):
        entry = FastingEntry.query.get_or_404(entry_id)
        if entry.user_id != current_user.id:
            return jsonify({'ok': False, 'error': 'Non autorizzato'}), 403
        db.session.delete(entry)
        db.session.commit()
        return jsonify({'ok': True})

    @app.route('/api/stats')
    @login_required
    def api_stats():
        today_d = date.today()
        all_dates = set()
        for row in MealEntry.query.filter_by(user_id=current_user.id).with_entities(MealEntry.date).all():
            all_dates.add(row[0])
        for row in WorkoutEntry.query.filter_by(user_id=current_user.id).with_entities(WorkoutEntry.date).all():
            all_dates.add(row[0])
        for row in WeightLog.query.filter_by(user_id=current_user.id).with_entities(WeightLog.date).all():
            all_dates.add(row[0])
        streak = calculate_streak(list(all_dates))
        return jsonify({
            'streak': streak,
            'meals_today': MealEntry.query.filter_by(user_id=current_user.id, date=today_d).count(),
            'water_today': sum(wa.amount_ml for wa in WaterEntry.query.filter_by(user_id=current_user.id, date=today_d).all()),
            'workouts_today': WorkoutEntry.query.filter_by(user_id=current_user.id, date=today_d).count(),
            'has_weight_today': WeightLog.query.filter_by(user_id=current_user.id, date=today_d).first() is not None,
        })

    @app.route('/api/badge-notifications')
    @login_required
    def api_badge_notifications():
        new_badges = check_new_badges(current_user, db.session)
        return jsonify([{'type': b.get('badge_type', ''), **b} for b in new_badges])

    @app.route('/api/food/search')
    @login_required
    def api_food_search():
        q = request.args.get('q', '').strip()
        if len(q) < 2:
            return jsonify({'results': []})
        local = Food.query.filter(Food.name.ilike(f'%{q}%')).limit(10).all()
        results = [{'id': f.id, 'name': f.name, 'kcal': f.kcal_per_100g,
                     'protein': f.protein_g, 'carbs': f.carbs_g, 'fat': f.fat_g,
                     'source': 'local'} for f in local]
        try:
            from urllib.request import urlopen
            from urllib.parse import quote
            url = f'https://it.openfoodfacts.org/cgi/search.pl?search_terms={quote(q)}&json=1&page_size=15&lc=it'
            with urlopen(url, timeout=5) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                for product in data.get('products', []):
                    if product.get('product_name'):
                        p = product.get('nutriments', {})
                        # avoid duplicates with local
                        name = product['product_name']
                        if not any(r['name'].lower() == name.lower() for r in results):
                            results.append({
                                'id': None, 'name': name,
                                'kcal': p.get('energy-kcal_100g', 0),
                                'protein': p.get('proteins_100g', 0),
                                'carbs': p.get('carbohydrates_100g', 0),
                                'fat': p.get('fat_100g', 0),
                                'barcode': product.get('code', ''),
                                'source': 'openfoodfacts',
                            })
        except Exception as e:
            logger.warning(f'Open Food Facts search failed: {e}')
        return jsonify({'results': results[:20]})

    @app.route('/api/food/barcode/<barcode>')
    @login_required
    def api_food_barcode(barcode):
        try:
            from urllib.request import urlopen
            url = f'https://it.openfoodfacts.org/api/v0/product/{barcode}.json'
            with urlopen(url, timeout=5) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            if data.get('status') == 1:
                product = data['product']
                name = product.get('product_name', 'Sconosciuto')
                p = product.get('nutriments', {})
                return jsonify({
                    'found': True,
                    'name': name,
                    'kcal': p.get('energy-kcal_100g', 0),
                    'protein': p.get('proteins_100g', 0),
                    'carbs': p.get('carbohydrates_100g', 0),
                    'fat': p.get('fat_100g', 0),
                    'image': product.get('image_url', ''),
                    'barcode': barcode,
                })
            return jsonify({'found': False})
        except Exception as e:
            logger.warning(f'Barcode lookup failed: {e}')
            return jsonify({'found': False, 'error': str(e)})

    @app.route('/api/food/save-barcode-food', methods=['POST'])
    @csrf.exempt
    @login_required
    def api_save_barcode_food():
        name = request.json.get('name', '').strip()
        if not name:
            return jsonify({'saved': False, 'error': 'Nome richiesto'}), 400
        existing = CustomFood.query.filter_by(user_id=current_user.id, name=name).first()
        if existing:
            return jsonify({'saved': True, 'custom_food_id': existing.id, 'existing': True})
        cf = CustomFood(
            user_id=current_user.id,
            name=name,
            kcal_per_100g=float(request.json.get('kcal', 0)),
            protein_g=float(request.json.get('protein', 0)),
            carbs_g=float(request.json.get('carbs', 0)),
            fat_g=float(request.json.get('fat', 0)),
        )
        db.session.add(cf)
        db.session.commit()
        return jsonify({'saved': True, 'custom_food_id': cf.id, 'existing': False})

    @app.route('/photos')
    @login_required
    def photos():
        all_photos = ProgressPhoto.query.filter_by(user_id=current_user.id).order_by(ProgressPhoto.date.desc()).all()
        return render_template('photo.html', photos=all_photos)

    @app.route('/photos/upload', methods=['POST'])
    @login_required
    def photos_upload():
        photo_date = request.form.get('date', date.today().isoformat())
        existing = ProgressPhoto.query.filter_by(user_id=current_user.id, date=date.fromisoformat(photo_date)).first()
        if not existing:
            existing = ProgressPhoto(user_id=current_user.id, date=date.fromisoformat(photo_date))
            db.session.add(existing)

        photo_dir = os.path.join(app.root_path, 'static', 'uploads', str(current_user.id))
        os.makedirs(photo_dir, exist_ok=True)

        for view in ('front', 'side'):
            f = request.files.get(f'photo_{view}')
            if f and f.filename:
                ext = f.filename.rsplit('.', 1)[-1].lower() if '.' in f.filename else 'jpg'
                name = f'{photo_date}_{view}.{ext}'
                path = os.path.join(photo_dir, name)
                f.save(path)
                if view == 'front':
                    existing.photo_front = f'uploads/{current_user.id}/{name}'
                else:
                    existing.photo_side = f'uploads/{current_user.id}/{name}'

        db.session.commit()
        flash('Foto salvate!', 'success')
        return redirect(url_for('photos'))

    @app.route('/photos/delete/<int:photo_id>', methods=['POST'])
    @login_required
    def photos_delete(photo_id):
        photo = ProgressPhoto.query.get_or_404(photo_id)
        if photo.user_id != current_user.id:
            flash('Non autorizzato.', 'danger')
            return redirect(url_for('photos'))
        for attr in ('photo_front', 'photo_side'):
            path = getattr(photo, attr)
            if path:
                try:
                    os.remove(os.path.join(app.root_path, 'static', path))
                except OSError:
                    pass
        db.session.delete(photo)
        db.session.commit()
        flash('Foto rimosse.', 'info')
        return redirect(url_for('photos'))

    @app.route('/api/check-reminder')
    @login_required
    def api_check_reminder():
        today_d = date.today()
        meals = MealEntry.query.filter_by(user_id=current_user.id, date=today_d).count()
        workouts = WorkoutEntry.query.filter_by(user_id=current_user.id, date=today_d).count()
        water = WaterEntry.query.filter_by(user_id=current_user.id, date=today_d).count()
        weight = WeightLog.query.filter_by(user_id=current_user.id, date=today_d).count()
        return jsonify({
            'can_remind': True,
            'missing_meals': meals == 0,
            'missing_water': water == 0,
            'missing_workout': workouts == 0,
            'missing_weight': weight == 0,
            'show_reminder': meals == 0 and water == 0,
        })

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('error.html', code=404,
                               message='Pagina non trovata'), 404

    @app.errorhandler(500)
    def server_error(e):
        logger.error(f'Server error: {e}')
        return render_template('error.html', code=500,
                               message='Errore del server'), 500

    return app


app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        populate_foods(db)
        seed_programs(db.session)
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'

    import os.path as _path, socket as _sock, subprocess as _sp, os as _os
    base = _path.dirname(_path.abspath(__file__))
    cert = _path.join(base, 'cert.pem')
    key = _path.join(base, 'key.pem')

    # Auto-generate certs if missing
    if not (_path.exists(cert) and _path.exists(key)):
        print('Genero il certificato SSL...')
        # Try mkcert first
        mkcert = _sp.run(['which', 'mkcert'], capture_output=True, text=True).stdout.strip()
        if mkcert:
            try:
                s = _sock.socket(_sock.AF_INET, _sock.SOCK_DGRAM)
                s.settimeout(1); s.connect(('8.8.8.8', 80)); lan_ip = s.getsockname()[0]; s.close()
            except Exception:
                lan_ip = '127.0.0.1'
            _sp.run([mkcert, '-cert-file', cert, '-key-file', key,
                     'localhost', lan_ip, '*.nip.io'], capture_output=True)
            # Copy root CA to static
            ca_home = _path.join(_path.expanduser('~'), '.local/share/mkcert', 'rootCA.pem')
            if _path.exists(ca_home):
                import shutil as _sh
                _sh.copy2(ca_home, _path.join(base, 'static', 'rootCA.pem'))
                print('Certificato CA disponibile in static/rootCA.pem')
        else:
            # Fallback: openssl
            try:
                s = _sock.socket(_sock.AF_INET, _sock.SOCK_DGRAM)
                s.settimeout(1); s.connect(('8.8.8.8', 80)); lan_ip = s.getsockname()[0]; s.close()
            except Exception:
                lan_ip = '127.0.0.1'
            cfg = _path.join(base, '_openssl.cnf')
            with open(cfg, 'w') as f:
                f.write(f'[req]\ndistinguished_name=dn\nx509_extensions=ext\nprompt=no\n[dn]\nCN=Ajò\n[ext]\nsubjectAltName=DNS:localhost,IP:{lan_ip}\n')
            _sp.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-keyout', key,
                     '-out', cert, '-days', '365', '-nodes', '-config', cfg], capture_output=True)
            _sp.run(['rm', cfg])
        if _path.exists(cert) and _path.exists(key):
            print('Certificato SSL creato.')
        else:
            print('ERRORE: Impossibile creare il certificato SSL.')
            sys.exit(1)

    # Detect LAN IP
    try:
        s = _sock.socket(_sock.AF_INET, _sock.SOCK_DGRAM)
        s.settimeout(1); s.connect(('8.8.8.8', 80)); lan_ip = s.getsockname()[0]; s.close()
    except Exception:
        lan_ip = '127.0.0.1'

    print(f'\nAjò avviato su https://{lan_ip}:{port}', flush=True)
    print(f'CA cert: https://{lan_ip}:{port}/static/rootCA.pem\n', flush=True)

    _os.chdir(base)
    proc = _sp.Popen([sys.executable, '-m', 'gunicorn',
        '--certfile', cert, '--keyfile', key,
        '--bind', f'0.0.0.0:{port}',
        '--access-logfile', '-',
        'app:app'])
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
    sys.exit(proc.returncode)
