# Ajò - Web App per Dimagrimento

App web in Python Flask per aiutare a dimagrire in modo sano e personalizzato. Calcoli nutrizionali scientifici, diario alimentare con 114 alimenti italiani, tracking allenamenti e grafici di progresso.

## Funzionalità

- **Autenticazione utenti** con password hashate (Flask-Login + Werkzeug)
- **Dashboard personale** con BMR, TDEE, macros e progresso verso obiettivo
- **Diario alimentare** con 114 alimenti italiani comuni, ricerca e filtro per categoria
- **Tracking allenamenti** con 13 attività sportive e calcolo calorie bruciate (MET values)
- **Grafici di progresso** peso e allenamenti (Chart.js)
- **Piano personalizzato** generato sui tuoi dati con 4 fasi da 4 settimane
- **Gestione profilo** con modifica dati anagrafici e obiettivo
- **Utente demo** precaricato con 30 giorni di dati finti

## Stack tecnologico

| Componente | Tecnologia |
|------------|------------|
| Backend | Python 3.12+ / Flask 3.0 |
| Database | SQLite (sviluppo) / PostgreSQL (produzione) |
| ORM | SQLAlchemy 2.0 |
| Autenticazione | Flask-Login |
| Frontend | Jinja2 + Bootstrap 5 + Chart.js |
| Font | Outfit (Google Fonts) |
| Icone | Bootstrap Icons |

## Installazione

```bash
# 1. Crea virtual environment (opzionale ma consigliato)
python3 -m venv venv
source venv/bin/activate

# 2. Installa dipendenze
pip install -r requirements.txt

# 3. Inizializza database con utente demo
python init_db.py

# 4. Avvia l'app
python app.py
# oppure
./start.sh
```

L'app sarà disponibile su http://localhost:5000

## Account demo

Per provare subito l'app senza registrarsi:

- **URL**: http://localhost:5000/login-demo
- **Email**: `demo@ajo.app`
- **Password**: `demo1234`

L'utente demo ha:
- 30 giorni di misurazioni peso (da 90 kg a 86,5 kg)
- 7 giorni di pasti registrati
- ~12 allenamenti nelle ultime 4 settimane

## Struttura del progetto

```
ajo/
├── app.py              # App Flask principale con tutte le route
├── models.py           # Modelli SQLAlchemy (User, WeightLog, Food, MealEntry, WorkoutEntry)
├── nutrition.py        # Calcoli BMR, TDEE, macros, calorie bruciate
├── foods_data.py       # Database 114 alimenti italiani
├── init_db.py          # Inizializzazione DB + utente demo
├── config.py           # Configurazione Flask
├── requirements.txt    # Dipendenze Python
├── start.sh            # Script avvio rapido
├── ajo.db              # Database SQLite (generato dopo init_db.py)
├── templates/          # Template Jinja2
│   ├── base.html       # Layout base con navbar/footer
│   ├── landing.html    # Homepage pubblica
│   ├── login.html      # Pagina login
│   ├── register.html   # Registrazione
│   ├── dashboard.html  # Dashboard utente
│   ├── diary.html      # Diario alimentare
│   ├── training.html   # Tracking allenamenti
│   ├── progress.html   # Grafici e storico peso
│   ├── plan.html       # Piano personalizzato
│   ├── profile.html    # Profilo utente
│   └── error.html      # Pagina errore 404/500
└── static/
    ├── css/style.css   # Stile dark + arancione (sportivo energico)
    └── js/main.js      # JS di base
```

## Modelli dati

### User
- email, password_hash, name, gender, height_cm, birth_date
- activity_level (sedentary/light/moderate/active/very_active)
- target_weight_kg, start_date, is_demo

### WeightLog
- user_id, weight, date, note
- Vincolo unicit&agrave;: (user_id, date) - una misurazione al giorno

### Food (114 alimenti pre-caricati)
- name, category, kcal_per_100g, protein_g, carbs_g, fat_g, fiber_g
- default_portion_g

### MealEntry
- user_id, food_id, quantity_g, meal_type, date
- meal_type: breakfast/lunch/snack/dinner

### WorkoutEntry
- user_id, activity_type, duration_min, distance_km, intensity, calories_burned, date

## Calcoli nutrizionali

### BMR (Metabolismo Basale)
Formula **Mifflin-St Jeor** (pi&ugrave; accurata della Harris-Benedict):
- Uomini: `BMR = 10&times;peso + 6.25&times;altezza - 5&times;et&agrave; + 5`
- Donne: `BMR = 10&times;peso + 6.25&times;altezza - 5&times;et&agrave; - 161`

### TDEE (Fabbisogno Giornaliero)
`TDEE = BMR &times; fattore_attivit&agrave;`

| Livello | Fattore |
|---------|---------|
| Sedentario | 1.2 |
| Leggero | 1.375 |
| Moderato | 1.55 |
| Attivo | 1.725 |
| Molto attivo | 1.9 |

### Calorie target per dimagrimento
`target = max(BMR &times; 1.1, TDEE - deficit)` con deficit default 750 kcal/giorno.

### Ripartizione macros
- 32% proteine (per preservare massa muscolare)
- 32% carboidrati (per energia corsa)
- 27% grassi (per ormoni e vitamine)
- ~6% fibre

### Calorie bruciate per attivit&agrave;
Formula MET: `kcal = MET &times; peso_kg &times; (minuti / 60)`

Valori MET da Compendium of Physical Activities (esempi):
- Corsa 10 km/h: MET 11.0
- Bici 20 km/h: MET 7.5
- Nuoto moderato: MET 8.0
- Forza: MET 6.0

## Roadmap future

- [x] Coach comportamentale con messaggi motivazionali
- [x] Programmi tematici (Resa dei conti, Forza Rapida, ecc.)
- [x] Integrazione wearable (Google Fit / Health Connect)
- [ ] Sfide tra utenti
- [ ] Ricettario condiviso
- [ ] Community: gruppi di supporto

## Note legali

Quest'app ha scopo educativo e informativo. I consigli nutrizionali sono basati su linee guida generali e **non sostituiscono il parere di un medico o nutrizionista**. Prima di intraprendere qualsiasi programma di dimagrimento, specialmente in caso di patologie preesistenti, consultare un professionista sanitario.

## Licenza

MIT License - libero utilizzo personale e commerciale.
