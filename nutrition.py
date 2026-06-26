import json
import math
from dataclasses import dataclass
from typing import Optional
from dataclasses import replace as dataclass_replace


ACTIVITY_FACTORS = {
    'sedentary': 1.2,
    'light': 1.375,
    'moderate': 1.55,
    'active': 1.725,
    'very_active': 1.9,
}

ACTIVITY_LABELS = {
    'sedentary': 'Sedentario (nessun esercizio)',
    'light': 'Leggero (1-3 volte/settimana)',
    'moderate': 'Moderato (3-5 volte/settimana)',
    'active': 'Attivo (6-7 volte/settimana)',
    'very_active': 'Molto attivo (lavoro fisico + sport)',
}

DEFICIT_PRESETS = {
    250: 'Leggero (-0.2 kg/settimana)',
    500: 'Moderato (-0.5 kg/settimana)',
    750: 'Spinto (-0.7 kg/settimana)',
    1000: 'Aggressivo (-1 kg/settimana)',
}

DIET_PRESETS = {
    'balanced': {'protein_pct': 30, 'carbs_pct': 40, 'fat_pct': 30, 'label': 'Bilanciata'},
    'keto': {'protein_pct': 20, 'carbs_pct': 5, 'fat_pct': 75, 'label': 'Cheto'},
    'low_carb': {'protein_pct': 35, 'carbs_pct': 20, 'fat_pct': 45, 'label': 'Low Carb'},
    'high_protein': {'protein_pct': 40, 'carbs_pct': 30, 'fat_pct': 30, 'label': 'Alto Proteico'},
    'mediterranean': {'protein_pct': 20, 'carbs_pct': 45, 'fat_pct': 35, 'label': 'Mediterranea'},
}

def get_macro_ratios(diet_type='balanced', custom_pct=None):
    preset = DIET_PRESETS.get(diet_type, DIET_PRESETS['balanced'])
    if custom_pct and len(custom_pct) == 3:
        p, c, f = custom_pct
        total = p + c + f
        if abs(total - 100) < 1 and p > 0 and c > 0 and f > 0:
            return (p, c, f)
    return (preset['protein_pct'], preset['carbs_pct'], preset['fat_pct'])


@dataclass
class NutritionPlan:
    bmr: float
    tdee: float
    target_kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float
    weekly_loss_kg: float
    days_to_target: int
    deficit_used: int = 500


def calculate_bmr(weight_kg: float, height_cm: float, age: int, gender: str) -> float:
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    if gender.upper() == 'M':
        return round(base + 5, 1)
    else:
        return round(base - 161, 1)


def calculate_tdee(bmr: float, activity_level: str) -> float:
    factor = ACTIVITY_FACTORS.get(activity_level, 1.55)
    return round(bmr * factor, 1)


def calculate_bmi(weight_kg: float, height_cm: float) -> float:
    h = height_cm / 100
    return round(weight_kg / (h * h), 1)


def bmi_category(bmi: float) -> str:
    if bmi < 18.5:
        return 'Sottopeso'
    elif bmi < 25:
        return 'Normale'
    elif bmi < 30:
        return 'Sovrappeso'
    else:
        return 'Obesità'


def build_plan(weight_kg: float, target_weight_kg: float, height_cm: float,
               age: int, gender: str, activity_level: str,
               deficit_kcal_day: int = 500,
               diet_type: str = 'balanced',
               custom_macros: tuple | None = None) -> NutritionPlan:
    bmr = calculate_bmr(weight_kg, height_cm, age, gender)
    tdee = calculate_tdee(bmr, activity_level)

    max_safe_deficit = int(tdee * 0.30)
    deficit_kcal_day = min(deficit_kcal_day, max_safe_deficit)

    min_calories = max(int(bmr * 1.1), 1500)
    target_kcal = max(min_calories, tdee - deficit_kcal_day)

    actual_deficit = tdee - target_kcal
    weekly_loss_kg = round(actual_deficit * 7 / 7700, 2)

    protein_pct, carbs_pct, fat_pct = get_macro_ratios(diet_type, custom_macros)
    protein_g = round(target_kcal * protein_pct / 100 / 4)
    carbs_g = round(target_kcal * carbs_pct / 100 / 4)
    fat_g = round(target_kcal * fat_pct / 100 / 9)
    fiber_g = 32

    kg_to_lose = max(0, weight_kg - target_weight_kg)
    if weekly_loss_kg > 0:
        days_to_target = int(kg_to_lose / weekly_loss_kg * 7)
    else:
        days_to_target = 0

    return NutritionPlan(
        bmr=bmr,
        tdee=tdee,
        target_kcal=round(target_kcal, 0),
        protein_g=protein_g,
        carbs_g=carbs_g,
        fat_g=fat_g,
        fiber_g=fiber_g,
        weekly_loss_kg=weekly_loss_kg,
        days_to_target=days_to_target,
        deficit_used=deficit_kcal_day,
    )


ACTIVITY_METS = {
    'running_easy': 9.8,
    'running_moderate': 11.0,
    'running_fast': 13.5,
    'cycling_moderate': 7.5,
    'cycling_easy': 5.0,
    'swimming_moderate': 8.0,
    'walking_brisk': 5.0,
    'walking_easy': 3.5,
    'strength': 6.0,
    'hiit': 8.0,
    'yoga': 3.0,
    'rowing': 8.5,
    'elliptical': 5.0,
    'stretching': 2.5,
}

ACTIVITY_LABELS_IT = {
    'running_easy': 'Corsa leggera',
    'running_moderate': 'Corsa moderata',
    'running_fast': 'Corsa veloce',
    'cycling_moderate': 'Ciclismo',
    'cycling_easy': 'Ciclismo tranquillo',
    'swimming_moderate': 'Nuoto',
    'walking_brisk': 'Camminata veloce',
    'walking_easy': 'Camminata',
    'strength': 'Rafforzamento',
    'hiit': 'HIIT',
    'yoga': 'Yoga',
    'rowing': 'Canottaggio',
    'elliptical': 'Ellittica',
}


def calories_burned(activity_type: str, duration_min: int, weight_kg: float) -> float:
    met = ACTIVITY_METS.get(activity_type, 6.0)
    return round(met * weight_kg * (duration_min / 60), 0)


def macro_summary_for_meals(meal_entries):
    total = {'kcal': 0, 'protein': 0, 'carbs': 0, 'fat': 0, 'fiber': 0}
    for entry in meal_entries:
        ratio = entry.quantity_g / 100
        total['kcal'] += entry.kcal
        total['protein'] += entry.protein
        total['carbs'] += entry.carbs
        total['fat'] += entry.fat
        if entry.food:
            total['fiber'] += entry.food.fiber_g * ratio
    for k in total:
        total[k] = round(total[k], 1)
    return total


def body_fat_percentage(bmi: float, age: int, gender: str) -> float:
    """Deurenberg formula: BF% = 1.20*BMI + 0.23*Age - 10.8*Gender - 5.4
    Gender: 1 for male, 0 for female."""
    g = 1 if gender.upper() == 'M' else 0
    bf = 1.20 * bmi + 0.23 * age - 10.8 * g - 5.4
    return round(max(3, min(60, bf)), 1)


def adapt_plan_from_history(plan: NutritionPlan, recent_loss_rate: Optional[float]) -> NutritionPlan:
    """Adjust plan based on actual weight loss rate (kg/week). None if insufficient data."""
    if recent_loss_rate is None:
        return plan
    expected = plan.weekly_loss_kg
    ratio = recent_loss_rate / expected if expected > 0 else 1
    if 0.8 < ratio < 1.2:
        return plan
    new_deficit = int(plan.deficit_used * (expected / max(recent_loss_rate, 0.01)))
    new_deficit = max(250, min(1000, new_deficit))
    new_target = max(plan.bmr * 1.1, plan.tdee - new_deficit)
    return dataclass_replace(plan,
        deficit_used=new_deficit,
        target_kcal=int(new_target),
        weekly_loss_kg=round(new_deficit * 7 / 7700, 2),
    )


def calculate_streak(all_dates):
    """Calculate consecutive day streak from a sorted list of unique date objects."""
    if not all_dates:
        return 0
    sorted_dates = sorted(set(all_dates), reverse=True)
    streak = 1
    for i in range(len(sorted_dates) - 1):
        expected = sorted_dates[i] - __import__('datetime').timedelta(days=1)
        if sorted_dates[i + 1] == expected:
            streak += 1
        else:
            break
    if sorted_dates[0] != __import__('datetime').date.today():
        return 0
    return streak


BADGE_DEFINITIONS = {
    'first_log': {'name': 'Primo Passo', 'desc': 'Primo pasto o allenamento registrato', 'icon': '🥇'},
    'streak_3': {'name': 'Costante', 'desc': '3 giorni consecutivi', 'icon': '🔥'},
    'streak_7': {'name': 'On Fire', 'desc': '7 giorni consecutivi', 'icon': '🔥'},
    'streak_14': {'name': 'Imparabile', 'desc': '14 giorni consecutivi', 'icon': '⚡'},
    'streak_30': {'name': 'Leggenda', 'desc': '30 giorni consecutivi', 'icon': '🌟'},
    'water_10l': {'name': 'Aquaman', 'desc': '10 litri d\'acqua totali', 'icon': '💧'},
    'workout_10': {'name': 'Atleta', 'desc': '10 allenamenti completati', 'icon': '🏃'},
    'workout_50': {'name': 'Maratoneta', 'desc': '50 allenamenti completati', 'icon': '🏅'},
    'meals_50': {'name': 'Foodie', 'desc': '50 pasti registrati', 'icon': '🍽️'},
    'weight_1kg': {'name': 'Primo Traguardo', 'desc': '1 kg perso', 'icon': '🎯'},
    'weight_5kg': {'name': 'Metamorfosi', 'desc': '5 kg persi', 'icon': '💪'},
    'weight_10kg': {'name': 'Trasformazione', 'desc': '10 kg persi', 'icon': '🏆'},
    'target_reached': {'name': 'Obiettivo Raggiunto!', 'desc': 'Hai raggiunto il peso target', 'icon': '🎉'},
    'fasting_3': {'name': 'Digiunatore', 'desc': '3 digiuni completati', 'icon': '⏳'},
    'fasting_7': {'name': 'Esperto del Digiuno', 'desc': '7 digiuni completati', 'icon': '⏰'},
    'fasting_14': {'name': 'Maestro del Digiuno', 'desc': '14 digiuni completati', 'icon': '⌛'},
    'fasting_30': {'name': 'Monaco', 'desc': '30 digiuni completati', 'icon': '🧘'},
}


def check_new_badges(user, db_session):
    """Check and award any new badges. Returns list of newly awarded badge definitions."""
    from models import Badge, WeightLog, MealEntry, WaterEntry, WorkoutEntry, FastingEntry
    from datetime import date

    existing = {b.badge_type for b in Badge.query.filter_by(user_id=user.id).all()}
    new_badges = []

    meal_count = MealEntry.query.filter_by(user_id=user.id).count()
    workout_count = WorkoutEntry.query.filter_by(user_id=user.id).count()
    total_water = db_session.query(__import__('sqlalchemy').func.sum(WaterEntry.amount_ml)).filter_by(user_id=user.id).scalar() or 0
    fasting_count = FastingEntry.query.filter_by(user_id=user.id, completed=True).count()

    all_entry_dates = set()
    for row in MealEntry.query.filter_by(user_id=user.id).with_entities(MealEntry.date).all():
        all_entry_dates.add(row[0])
    for row in WorkoutEntry.query.filter_by(user_id=user.id).with_entities(WorkoutEntry.date).all():
        all_entry_dates.add(row[0])
    for row in WeightLog.query.filter_by(user_id=user.id).with_entities(WeightLog.date).all():
        all_entry_dates.add(row[0])

    streak = calculate_streak(list(all_entry_dates))

    checks = {
        'first_log': meal_count + workout_count > 0,
        'streak_3': streak >= 3,
        'streak_7': streak >= 7,
        'streak_14': streak >= 14,
        'streak_30': streak >= 30,
        'water_10l': total_water >= 10000,
        'workout_10': workout_count >= 10,
        'workout_50': workout_count >= 50,
        'meals_50': meal_count >= 50,
        'fasting_3': fasting_count >= 3,
        'fasting_7': fasting_count >= 7,
        'fasting_14': fasting_count >= 14,
        'fasting_30': fasting_count >= 30,
    }

    starting = user.starting_weight
    current = user.current_weight
    if starting and current:
        lost = starting - current
        if lost >= 1:
            checks['weight_1kg'] = True
        if lost >= 5:
            checks['weight_5kg'] = True
        if lost >= 10:
            checks['weight_10kg'] = True
        if current <= user.target_weight_kg:
            checks['target_reached'] = True

    for badge_type, condition in checks.items():
        if condition and badge_type not in existing:
            b = Badge(user_id=user.id, badge_type=badge_type)
            db_session.add(b)
            new_badges.append(BADGE_DEFINITIONS[badge_type].copy())

    if new_badges:
        db_session.commit()

    return new_badges


_COACH_TIPS = [
    "Bere 2 litri d'acqua al giorno aumenta il metabolismo del 24-30%.",
    "Mangiare proteine a colazione riduce le voglie di zucchero per tutto il giorno.",
    "Il sonno è fondamentale: meno di 7 ore aumenta il cortisolo e favorisce l'accumulo di grasso.",
    "Camminare 15 minuti dopo pranzo migliora la digestione e la sensibilità insulinica.",
    "Le proteine richiedono più energia per essere digerite (effetto termico del 20-30%).",
    "Il digiuno intermittente 16:8 è la finestra più studiata e sostenibile.",
    "Aggiungere spezie come curcuma e pepe nero ai pasti ha proprietà antinfiammatorie.",
    "Il 70% del sistema immunitario risiede nell'intestino: mangia fibre e fermentati.",
    "Lo stress cronico aumenta il cortisolo, che favorisce il grasso addominale.",
    "Una camminata di 30 minuti al giorno riduce il rischio cardiovascolare del 30%.",
    "Il muscolo brucia più calorie del grasso anche a riposo: 1 kg di muscolo ~13 kcal/giorno.",
    "Mangiare davanti a schermi porta a consumare il 15% in più senza accorgersene.",
    "Il tè verde contiene catechine che possono aumentare il dispendio energetico del 4-5%.",
    "La fibra solubile (avena, legumi) riduce l'assorbimento di grassi e zuccheri.",
    "Fare stretching per 10 minuti al giorno migliora la circolazione e riduce gli infortuni.",
    "Le noci sono ricche di omega-3: 30g al giorno riducono l'infiammazione.",
    "Il caffè prima dell'allenamento migliora la performance del 5-10%.",
    "Le donne hanno bisogno di più ferro: spinaci, legumi e carni magre sono ottime fonti.",
]

import random as _random

def generate_coach_messages(user, today=None):
    """Generate personalized coach messages based on user data."""
    from datetime import date, timedelta
    from models import MealEntry, WorkoutEntry, WaterEntry, WeightLog, FastingEntry

    today = today or date.today()
    yesterday = today - timedelta(days=1)
    messages = []

    # --- Yesterday's protein check ---
    yesterday_meals = MealEntry.query.filter_by(user_id=user.id, date=yesterday).all()
    if yesterday_meals:
        m = macro_summary_for_meals(yesterday_meals)
        w = user.current_weight or 80
        plan = build_plan(
            weight_kg=w, target_weight_kg=user.target_weight_kg,
            height_cm=user.height_cm, age=user.age, gender=user.gender,
            activity_level=user.activity_level, deficit_kcal_day=user.deficit_kcal,
            diet_type=user.diet_type,
        )
        target_p = plan.protein_g
        if m['protein'] < target_p * 0.7:
            messages.append({
                'icon': '🥩',
                'type': 'protein_low',
                'title': 'Proteine basse ieri',
                'body': f'Hai assunto solo {round(m["protein"])}g di proteine ieri. Punta ad almeno {round(target_p)}g per preservare la massa muscolare. Aggiungi pollo, pesce, uova o legumi ai pasti.',
                'priority': 'high',
            })
        elif m['protein'] >= target_p * 0.9:
            messages.append({
                'icon': '💪',
                'type': 'protein_good',
                'title': 'Ottime proteine ieri!',
                'body': f'{round(m["protein"])}g di proteine ieri — hai centrato l\'obiettivo! La massa muscolare è al sicuro.',
                'priority': 'normal',
            })

    # --- Weight trend ---
    logs = WeightLog.query.filter_by(user_id=user.id).order_by(WeightLog.date.desc()).limit(7).all()
    if len(logs) >= 2:
        recent = logs[0].weight
        oldest = logs[-1].weight
        diff = oldest - recent  # positive = lost weight
        if diff > 0.5:
            messages.append({
                'icon': '📉',
                'type': 'weight_down',
                'title': 'Peso in calo!',
                'body': f'Hai perso {diff:.1f}kg nell\'ultima settimana. Ottimo ritmo, continua così!',
                'priority': 'normal',
            })
        elif diff > 0.1:
            messages.append({
                'icon': '✅',
                'type': 'weight_stable',
                'title': 'Leggero calo',
                'body': f'{diff:.1f}kg persi nei giorni recenti. La costanza paga — mantieni il piano.',
                'priority': 'normal',
            })
        elif diff < -0.5:
            messages.append({
                'icon': '⚠️',
                'type': 'weight_up',
                'title': 'Peso in aumento',
                'body': f'Il peso è aumentato di {abs(diff):.1f}kg. Potrebbe essere normale fluttuazione. Controlla le porzioni e l\'idratazione.',
                'priority': 'high',
            })
        elif diff < 0:
            messages.append({
                'icon': '📊',
                'type': 'weight_stable',
                'title': 'Peso stabile',
                'body': f'Leggero aumento di {abs(diff):.1f}kg — potrebbe essere ritenzione idrica. Continua con costanza.',
                'priority': 'normal',
            })

    # --- Workout streak ---
    recent_workouts = WorkoutEntry.query.filter(
        WorkoutEntry.user_id == user.id,
        WorkoutEntry.date >= today - timedelta(days=7),
    ).order_by(WorkoutEntry.date.desc()).all()
    if len(recent_workouts) >= 4:
        messages.append({
            'icon': '🏋️',
            'type': 'workout_streak',
            'title': f'{len(recent_workouts)} allenamenti in 7 giorni!',
            'body': 'Stai mantenendo un\'ottima frequenza. Ricorda che il recupero è importante quanto l\'allenamento.',
            'priority': 'normal',
        })
    elif len(recent_workouts) == 0:
        today_w = WorkoutEntry.query.filter_by(user_id=user.id, date=today).count()
        if today_w == 0:
            messages.append({
                'icon': '🏃',
                'type': 'workout_tip',
                'title': 'Nessun allenamento recente',
                'body': 'Anche 15 minuti di camminata veloce fanno la differenza. Inizia con qualcosa di leggero oggi!',
                'priority': 'low',
            })

    # --- Fasting consistency ---
    recent_fasts = FastingEntry.query.filter_by(user_id=user.id, completed=True).order_by(FastingEntry.date.desc()).limit(5).all()
    if len(recent_fasts) >= 3:
        messages.append({
            'icon': '⏱️',
            'type': 'fasting_good',
            'title': 'Digiuno costante',
            'body': f'{len(recent_fasts)} digiuni completati di recente. Il tuo corpo si sta adattando alla finestra alimentare.',
            'priority': 'normal',
        })

    # --- Water reminder ---
    today_water = WaterEntry.query.filter_by(user_id=user.id, date=today).all()
    total_water = sum(w.amount_ml for w in today_water)
    if total_water < 500 and len(today_water) > 0:
        messages.append({
            'icon': '💧',
            'type': 'water_low',
            'title': 'Bevi di più!',
            'body': f'Solo {total_water}ml oggi. Punta a 2000ml — l\'idratazione aiuta metabolismo e concentrazione.',
            'priority': 'high',
        })
    elif total_water == 0:
        messages.append({
            'icon': '💧',
            'type': 'water_none',
            'title': 'Ancora senza acqua oggi',
            'body': 'Non hai registrato acqua oggi. Inizia subito con un bicchiere! 250ml fanno già la differenza.',
            'priority': 'high',
        })

    # --- Meal logging consistency ---
    recent_meals_count = MealEntry.query.filter(
        MealEntry.user_id == user.id,
        MealEntry.date >= today - timedelta(days=7),
    ).count()
    if recent_meals_count == 0 and WorkoutEntry.query.filter_by(user_id=user.id).count() == 0:
        messages.append({
            'icon': '🚀',
            'type': 'welcome',
            'title': 'Benvenuto!',
            'body': 'Inizia registrando il tuo primo pasto o allenamento. Ogni piccolo passo conta verso il tuo obiettivo!',
            'priority': 'high',
        })

    # --- General tip (always one) ---
    tip = _random.choice(_COACH_TIPS)
    messages.append({
        'icon': '💡',
        'type': 'tip',
        'title': 'Consiglio del giorno',
        'body': tip,
        'priority': 'low',
    })

    # Sort by priority
    priority_order = {'high': 0, 'normal': 1, 'low': 2}
    messages.sort(key=lambda m: priority_order.get(m['priority'], 2))
    return messages


BUILTIN_PROGRAMS = [
    {
        'name': 'Perdita Peso Rapida',
        'slug': 'weight-loss-rapid',
        'description': 'Programma intensivo di 4 settimane per perdita peso accelerata. Deficit calorico aggressivo, allenamenti frequenti e monitoraggio quotidiano. Ideale per chi ha già esperienza e vuole risultati rapidi.',
        'duration_days': 28,
        'difficulty': 'advanced',
        'goal_type': 'weight_loss',
        'diet_type': 'high_protein',
        'deficit_kcal': 750,
        'workout_freq_per_week': 5,
        'water_target_ml': 2500,
        'fasting_hours': 0,
        'color': '#e74c3c',
        'icon': 'bi-lightning-charge-fill',
        'order': 1,
        'content': json.dumps({
            'example_meals': [
                {'name': 'Colazione', 'description': '2 uova sode, 100g fiocchi di latte, una mela verde, tè verde.'},
                {'name': 'Pranzo', 'description': '200g petto di pollo alla griglia, 200g broccoli al vapore, 150g riso basmati integrale.'},
                {'name': 'Cena', 'description': '200g merluzzo al cartoccio, insalata mista con pomodori e cetrioli, 30g mandorle.'},
                {'name': 'Spuntino pre-allenamento', 'description': 'Una banana con 20g burro d\'arachidi.'},
            ],
            'shopping_list': [
                'Petto di pollo, manzo magro, merluzzo, uova',
                'Fiocchi di latte, yogurt greco 0%',
                'Riso basmati, avena, patate dolci',
                'Broccoli, spinaci, insalata, zucchine, pomodori',
                'Frutta: mele verdi, banane, frutti di bosco',
                'Olio d\'oliva, olio di cocco',
                'Frutta secca: mandorle, noci',
            ],
            'tips': [
                'Mantieni il deficit a 300 kcal — non scendere sotto per non perdere muscolo',
                'Allenamento di forza 4x/sett, cardio moderato 2x/sett',
                'Proteine: almeno 1.8g per kg di peso corporeo',
                'Dormi almeno 7-8 ore — il recupero è metà del risultato',
            ],
        }),
    },
    {
        'name': 'Definizione Muscolare',
        'slug': 'muscle-definition',
        'description': 'Programma di 6 settimane per definire il fisico mantenendo la massa magra. Deficit leggero, alto proteico, con enfasi su allenamento di forza e cardio moderato.',
        'duration_days': 42,
        'difficulty': 'intermediate',
        'goal_type': 'definition',
        'diet_type': 'high_protein',
        'deficit_kcal': 300,
        'workout_freq_per_week': 4,
        'water_target_ml': 2500,
        'fasting_hours': 0,
        'color': '#3498db',
        'icon': 'bi-activity',
        'order': 2,
        'content': json.dumps({
            'example_meals': [
                {'name': 'Colazione', 'description': 'Frullato proteico: 300ml latte scremato, 40g whey, 30g avena, 100g frutti di bosco.'},
                {'name': 'Pranzo', 'description': '200g filetto di maiale magro all\'arancia, 200g carote al forno, 200g quinoa.'},
                {'name': 'Cena', 'description': '200g salmone, 150g patate dolci al forno, 200g spinaci saltati con aglio.'},
                {'name': 'Spuntini', 'description': 'Yogurt greco 0% (200g) con noci, oppure un uovo sodo.'},
            ],
            'shopping_list': [
                'Pollo, filetto di maiale, salmone, uova, manzo magro',
                'Latte scremato, yogurt greco 0%, whey protein',
                'Avena, quinoa, patate dolci',
                'Frutti di bosco, spinaci, carote, insalata, zucchine',
                'Olio extravergine, spezie, aceto di mele',
                'Frutta secca: noci, mandorle',
            ],
            'tips': [
                'Deficit leggero (300 kcal) per bruciare grasso senza sacrificare muscolo',
                'Pasti ogni 3-4 ore per mantenere il metabolismo attivo',
                'Bevi 2.5L di acqua al giorno',
                'Pesati ogni settimana alla stessa ora',
            ],
        }),
    },
    {
        'name': 'Cheto Start',
        'slug': 'keto-start',
        'description': 'Avvio graduale alla dieta chetogenica in 2 settimane. Impara a gestire i macros chetogenici, supera la "keto flu" e entra in chetosi. Pasti esempio e lista della spesa inclusi.',
        'duration_days': 14,
        'difficulty': 'intermediate',
        'goal_type': 'keto',
        'diet_type': 'keto',
        'deficit_kcal': 500,
        'workout_freq_per_week': 3,
        'water_target_ml': 3000,
        'fasting_hours': 14,
        'color': '#9b59b6',
        'icon': 'bi-droplet-half',
        'order': 3,
        'content': json.dumps({
            'example_meals': [
                {'name': 'Colazione', 'description': 'Frittata con 3 uova, 50g formaggio grattugiato, spinaci saltati nel burro. Caffè con panna fresca (no zucchero).'},
                {'name': 'Pranzo', 'description': 'Petto di pollo alla griglia (200g) con insalata mista, 50g parmigiano, olio d\'oliva, avocado (100g).'},
                {'name': 'Cena', 'description': 'Salmone al forno (200g) con asparagi al burro e 50g mandorle tritate. Finire con una tisana.'},
                {'name': 'Spuntini', 'description': 'Noci/mandorle (30g), cetrioli con formaggio spalmabile, olive, sedano con burro d\'arachidi (senza zucchero).'}
            ],
            'shopping_list': [
                'Uova bio',
                'Burro e panna fresca',
                'Formaggi stagionati (parmigiano, pecorino, gouda)',
                'Carne: pollo, manzo, maiale',
                'Pesce: salmone, sgombro, sardine',
                'Olio d\'oliva extravergine',
                'Avocado',
                'Verdure a basso carbo: spinaci, rucola, zucchine, asparagi, cavolfiore',
                'Frutta secca: mandorle, noci, noci pecan',
                'Cocco, farina di mandorle',
                'Caffè e tè (senza zucchero)',
                'Sale, spezie, aglio, limone',
            ],
            'tips': [
                'Bevi almeno 3L di acqua al giorno — la chetogenica disidrata',
                'Integra magnesio, potassio e sale per evitare la "keto flu"',
                'Non superare i 20g di carbo netti al giorno',
                'Misura il peso ogni mattina a digiuno',
            ],
        }),
    },
    {
        'name': 'Fitness Base',
        'slug': 'fitness-base',
        'description': 'Programma completo per principianti di 4 settimane. Crea le basi per uno stile di vita sano con allenamenti semplici, alimentazione bilanciata e abitudini sostenibili.',
        'duration_days': 28,
        'difficulty': 'beginner',
        'goal_type': 'general_fitness',
        'diet_type': 'balanced',
        'deficit_kcal': 400,
        'workout_freq_per_week': 3,
        'water_target_ml': 2000,
        'fasting_hours': 0,
        'color': '#2ecc71',
        'icon': 'bi-graph-up-arrow',
        'order': 4,
        'content': json.dumps({
            'example_meals': [
                {'name': 'Colazione', 'description': 'Porridge di avena (50g) con latte, una mela e 25g mandorle. Tè o caffè senza zucchero.'},
                {'name': 'Pranzo', 'description': '150g pasta integrale al pomodoro con 100g mozzarella light e basilico fresco.'},
                {'name': 'Cena', 'description': '200g orata al cartoccio con patate lesse (150g) e fagiolini saltati in padella.'},
                {'name': 'Spuntini', 'description': 'Uno yogurt bianco con mirtilli, oppure una pera con 20g di cioccolato fondente.'},
            ],
            'shopping_list': [
                'Pasta integrale, riso, avena, pane integrale',
                'Pollo, orata, uova, mozzarella light, yogurt',
                'Patate, carote, zucchine, insalata, pomodori, spinaci',
                'Frutta: mele, pere, banane, mirtilli',
                'Olio extravergine, limone, erbe aromatiche',
                'Legumi: lenticchie, ceci (2-3x/settimana)',
            ],
            'tips': [
                'Deficit moderato (400 kcal) — costanza batte intensità',
                'Inizia con 3 allenamenti a settimana, alterna forza e cardio leggero',
                'Non saltare la colazione: dà il via al metabolismo',
                'Usa la funzione \"Diario\" per registrare ogni pasto — la consapevolezza è il primo passo',
            ],
        }),
    },
    {
        'name': 'Massa Magra',
        'slug': 'lean-mass',
        'description': 'Programma di 8 settimane per aumentare la massa muscolare con minimo accumulo di grasso. Leggero surplus calorico, alto proteico, allenamento di forza progressivo.',
        'duration_days': 56,
        'difficulty': 'intermediate',
        'goal_type': 'muscle_gain',
        'diet_type': 'high_protein',
        'deficit_kcal': 0,
        'workout_freq_per_week': 4,
        'water_target_ml': 2500,
        'fasting_hours': 0,
        'color': '#f39c12',
        'icon': 'bi-heart-pulse',
        'order': 5,
        'content': json.dumps({
            'example_meals': [
                {'name': 'Colazione (post-allenamento)', 'description': '5 uova sode, 150g fiocchi di latte, 50g mandorle, una banana.'},
                {'name': 'Pranzo', 'description': '250g riso basmati con 200g petto di pollo, peperoni saltati e 50g parmigiano grattugiato.'},
                {'name': 'Cena', 'description': '250g bistecca di manzo ai ferri con 300g patate dolci al forno e insalata mista.'},
                {'name': 'Spuntino pre-sonno', 'description': '200g yogurt greco con 50g noci pecan e un cucchiaio di miele.'},
            ],
            'shopping_list': [
                'Manzo, pollo, uova, salmone, latte intero',
                'Yogurt greco, fiocchi di latte, parmigiano',
                'Riso basmati, patate dolci, avena, pane integrale',
                'Banane, miele, frutta secca (noci, mandorle, noci pecan)',
                'Spinaci, peperoni, insalata, broccoli',
                'Olio d\'oliva, burro d\'arachidi, cioccolato fondente',
            ],
            'tips': [
                'Surplus calorico di 300-500 kcal al giorno sopra il TDEE',
                'Proteine almeno 2g per kg di peso corporeo',
                'Allenamento di forza 4x/settimana con sovraccarico progressivo',
                'Mangia il 30% delle calorie entro 60 minuti dall\'allenamento',
                'Dormi 8 ore — il muscolo cresce quando riposi, non quando ti alleni',
            ],
        }),
    },
    {
        'name': 'Digiuno Intermittente',
        'slug': 'intermittent-fasting',
        'description': 'Programma di 4 settimane per integrare il digiuno intermittente 16:8 nella tua routine. Impara la finestra alimentare ottimale, gestisci la fame e combinalo con l\'allenamento.',
        'duration_days': 28,
        'difficulty': 'beginner',
        'goal_type': 'fasting',
        'diet_type': 'balanced',
        'deficit_kcal': 500,
        'workout_freq_per_week': 3,
        'water_target_ml': 2500,
        'fasting_hours': 16,
        'color': '#1abc9c',
        'icon': 'bi-clock',
        'order': 6,
        'content': json.dumps({
            'example_meals': [
                {'name': 'Finestra alimentare (12:00-20:00)', 'description': 'La tua finestra ideale: pranzo alle 12, cena entro le 20. Solo acqua, caffè amaro e tè fuori dalla finestra.'},
                {'name': 'Pranzo (apertura finestra)', 'description': '200g pollo alla griglia con 100g quinoa, 200g zucchine grigliate. Un avocado come grassi sani.'},
                {'name': 'Cena (chiusura finestra)', 'description': '150g salmone al forno, patate dolci (150g), asparagi al limone. Un quadratino cioccolato fondente per concludere.'},
                {'name': 'Bevande consentite a digiuno', 'description': 'Acqua (anche gassata), caffè nero (senza zucchero né latte), tè verde, tisane non zuccherate.'},
            ],
            'shopping_list': [
                'Pollo, salmone, uova, manzo magro',
                'Quinoa, patate dolci, avena, riso integrale',
                'Zucchine, asparagi, spinaci, avocado, insalata',
                'Caffè in grani, tè verde, tisane',
                'Olio d\'oliva, limone, aceto di mele',
                'Cioccolato fondente 85%+',
            ],
            'tips': [
                'Le prime 3-4 giornate sono le più dure — il corpo si adatta al nuovo ritmo',
                'Bevi acqua appena sveglio: aiuta a ridurre la fame mattutina',
                'Caffè nero amaro reprime l\'appetito — sfruttalo',
                'Combina il digiuno con allenamenti a bassa intensità nello stato di fasted',
                'Non abbuffarti nella finestra alimentare: la qualità conta',
            ],
        }),
    },
    {
        'name': 'Mantenimento',
        'slug': 'maintenance',
        'description': 'Programma a tempo indeterminato per mantenere il peso raggiunto. Senza deficit, con flessibilità alimentare e allenamenti di mantenimento. Perfetto dopo un percorso di dimagrimento.',
        'duration_days': 999,
        'difficulty': 'beginner',
        'goal_type': 'maintenance',
        'diet_type': 'balanced',
        'deficit_kcal': 0,
        'workout_freq_per_week': 3,
        'water_target_ml': 2000,
        'fasting_hours': 0,
        'color': '#95a5a6',
        'icon': 'bi-shield-check',
        'order': 7,
        'content': json.dumps({
            'tips': [
                'Mantieni le calorie intorno al tuo TDEE: nessun deficit, nessun surplus',
                'Continua a pesarti 1-2 volte a settimana per monitorare eventuali derive',
                'Flessibilità alimentare: concediti gli sgarri, ma con consapevolezza',
                '3 allenamenti a settimana sono sufficienti per mantenere i risultati',
                'Se vedi il peso salire per 2 settimane consecutive, riduci 100-200 kcal al giorno',
            ],
        }),
    },
]


def seed_programs(db_session):
    """Seed built-in programs into the database. Safe to call multiple times."""
    from models import Program
    for pdef in BUILTIN_PROGRAMS:
        existing = Program.query.filter_by(slug=pdef['slug']).first()
        if not existing:
            prog = Program(**pdef)
            db_session.add(prog)
        elif 'content' in pdef:
            existing.content = pdef.get('content')
    db_session.commit()


def get_program_day(enrollment, today=None):
    """Calculate the current day number of a program (1-indexed)."""
    from datetime import date
    today = today or date.today()
    delta = (today - enrollment.start_date).days
    day = min(delta + 1, enrollment.program.duration_days)
    return max(1, day)


def get_daily_checklist(program, user, target_date=None):
    """Return a checklist of daily tasks for a program based on user data."""
    from datetime import date
    from models import MealEntry, WorkoutEntry, WaterEntry, FastingEntry

    target_date = target_date or date.today()

    meals_today = MealEntry.query.filter_by(user_id=user.id, date=target_date).all()
    workouts_today = WorkoutEntry.query.filter_by(user_id=user.id, date=target_date).all()
    water_today = WaterEntry.query.filter_by(user_id=user.id, date=target_date).all()
    total_water = sum(w.amount_ml for w in water_today)

    checklist = []

    # Meals
    meal_count = len(meals_today)
    checklist.append({
        'id': 'meals',
        'label': 'Pasti registrati',
        'done': meal_count >= 3,
        'detail': f'{meal_count}/3 pasti',
        'icon': 'bi-journal-text',
    })

    # Workout
    workout_done = len(workouts_today) > 0
    checklist.append({
        'id': 'workout',
        'label': 'Allenamento completato',
        'done': workout_done,
        'detail': 'Fatto' if workout_done else 'Da fare',
        'icon': 'bi-bicycle',
    })

    # Water
    target = program.water_target_ml or 2000
    water_done = total_water >= target
    checklist.append({
        'id': 'water',
        'label': f'Acqua ({target}ml)',
        'done': water_done,
        'detail': f'{total_water}/{target}ml',
        'icon': 'bi-droplet',
    })

    # Fasting
    if program.fasting_hours and program.fasting_hours > 0:
        today_fasts = FastingEntry.query.filter_by(user_id=user.id, date=target_date, completed=True).all()
        fast_done = len(today_fasts) > 0
        checklist.append({
            'id': 'fasting',
            'label': f'Digiuno {program.fasting_hours}h',
            'done': fast_done,
            'detail': 'Completato' if fast_done else 'Da fare',
            'icon': 'bi-clock',
        })

    # Weight log
    from models import WeightLog
    recent_weight = WeightLog.query.filter_by(user_id=user.id, date=target_date).first()
    checklist.append({
        'id': 'weight',
        'label': 'Peso registrato',
        'done': recent_weight is not None,
        'detail': f'{recent_weight.weight}kg' if recent_weight else 'Da registrare',
        'icon': 'bi-arrow-down-circle',
    })

    return checklist


def get_program_progress(enrollment, user):
    """Calculate overall progress stats for an enrollment."""
    from datetime import date, timedelta
    prog = enrollment.program
    today = date.today()

    days_passed = (today - enrollment.start_date).days
    total_days = prog.duration_days
    day_num = min(days_passed + 1, total_days)

    completed_days = sum(
        1 for d in range(days_passed)
        if _day_was_completed(enrollment, user, enrollment.start_date + timedelta(days=d))
    )

    pct = round(completed_days / max(days_passed, 1) * 100, 0) if days_passed > 0 else 0
    overall_pct = round(day_num / total_days * 100, 0)

    return {
        'current_day': day_num,
        'total_days': total_days,
        'days_passed': days_passed,
        'days_completed': completed_days,
        'adherence_pct': pct,
        'overall_pct': overall_pct,
        'remaining_days': max(0, total_days - day_num),
    }


def _day_was_completed(enrollment, user, day_date):
    """Check if a specific day in the program was completed."""
    from models import MealEntry, WorkoutEntry, WaterEntry, FastingEntry
    prog = enrollment.program

    meals = MealEntry.query.filter_by(user_id=user.id, date=day_date).count()
    if meals < 1:
        return False

    workouts = WorkoutEntry.query.filter_by(user_id=user.id, date=day_date).count()
    if workouts < 1:
        return False

    water = WaterEntry.query.filter_by(user_id=user.id, date=day_date).all()
    total_water = sum(w.amount_ml for w in water)
    target = prog.water_target_ml or 2000
    if total_water < target * 0.5:
        return False

    return True
