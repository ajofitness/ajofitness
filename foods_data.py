def populate_foods(db):
    from models import Food

    INRN_FOODS = [
        # Cereali e derivati
        Food(name='Pasta di semola integrale', category='Cereali', kcal_per_100g=340, protein_g=12.5, carbs_g=65.0, fat_g=2.5, fiber_g=8.0, default_portion_g=80),
        Food(name='Pasta di semola', category='Cereali', kcal_per_100g=353, protein_g=12.0, carbs_g=72.0, fat_g=1.5, fiber_g=3.0, default_portion_g=80),
        Food(name='Riso basmati integrale', category='Cereali', kcal_per_100g=350, protein_g=8.0, carbs_g=75.0, fat_g=2.0, fiber_g=4.0, default_portion_g=80),
        Food(name='Riso Arborio', category='Cereali', kcal_per_100g=358, protein_g=7.0, carbs_g=79.0, fat_g=1.0, fiber_g=1.5, default_portion_g=80),
        Food(name='Farro perlato', category='Cereali', kcal_per_100g=335, protein_g=12.0, carbs_g=67.0, fat_g=2.0, fiber_g=6.0, default_portion_g=80),
        Food(name='Orzo perlato', category='Cereali', kcal_per_100g=330, protein_g=10.0, carbs_g=70.0, fat_g=1.5, fiber_g=5.5, default_portion_g=80),
        Food(name='Avena in fiocchi', category='Cereali', kcal_per_100g=370, protein_g=13.5, carbs_g=63.0, fat_g=7.0, fiber_g=10.0, default_portion_g=40),
        Food(name='Pane integrale', category='Cereali', kcal_per_100g=240, protein_g=8.5, carbs_g=45.0, fat_g=3.0, fiber_g=6.0, default_portion_g=50),
        Food(name='Pane bianco', category='Cereali', kcal_per_100g=270, protein_g=8.0, carbs_g=52.0, fat_g=2.0, fiber_g=2.5, default_portion_g=50),
        Food(name='Cous cous', category='Cereali', kcal_per_100g=360, protein_g=12.0, carbs_g=72.0, fat_g=1.5, fiber_g=3.0, default_portion_g=80),
        Food(name='Polenta (farina di mais)', category='Cereali', kcal_per_100g=360, protein_g=8.0, carbs_g=78.0, fat_g=1.5, fiber_g=2.0, default_portion_g=80),
        Food(name='Quinoa', category='Cereali', kcal_per_100g=368, protein_g=14.0, carbs_g=64.0, fat_g=6.0, fiber_g=7.0, default_portion_g=80),

        # Legumi
        Food(name='Lenticchie secche', category='Legumi', kcal_per_100g=325, protein_g=24.0, carbs_g=53.0, fat_g=1.5, fiber_g=14.0, default_portion_g=50),
        Food(name='Ceci secchi', category='Legumi', kcal_per_100g=335, protein_g=21.0, carbs_g=55.0, fat_g=5.0, fiber_g=12.0, default_portion_g=50),
        Food(name='Fagioli borlotti secchi', category='Legumi', kcal_per_100g=325, protein_g=22.0, carbs_g=55.0, fat_g=1.5, fiber_g=15.0, default_portion_g=50),
        Food(name='Fagioli cannellini secchi', category='Legumi', kcal_per_100g=320, protein_g=21.0, carbs_g=56.0, fat_g=1.5, fiber_g=14.0, default_portion_g=50),
        Food(name='Piselli freschi', category='Legumi', kcal_per_100g=80, protein_g=5.5, carbs_g=13.0, fat_g=0.5, fiber_g=5.0, default_portion_g=100),
        Food(name='Fave secche', category='Legumi', kcal_per_100g=340, protein_g=26.0, carbs_g=55.0, fat_g=1.5, fiber_g=8.0, default_portion_g=50),

        # Carne e salumi
        Food(name='Petto di pollo', category='Carne', kcal_per_100g=165, protein_g=31.0, carbs_g=0.0, fat_g=3.6, fiber_g=0.0, default_portion_g=150),
        Food(name='Fesa di tacchino', category='Carne', kcal_per_100g=135, protein_g=29.0, carbs_g=0.0, fat_g=1.5, fiber_g=0.0, default_portion_g=150),
        Food(name='Filetto di maiale magro', category='Carne', kcal_per_100g=160, protein_g=28.0, carbs_g=0.0, fat_g=5.0, fiber_g=0.0, default_portion_g=150),
        Food(name='Bistecca di manzo magra', category='Carne', kcal_per_100g=180, protein_g=30.0, carbs_g=0.0, fat_g=6.0, fiber_g=0.0, default_portion_g=150),
        Food(name='Carne macinata di manzo magra', category='Carne', kcal_per_100g=190, protein_g=27.0, carbs_g=0.0, fat_g=9.0, fiber_g=0.0, default_portion_g=100),
        Food(name='Prosciutto crudo sgrassato', category='Carne', kcal_per_100g=195, protein_g=26.0, carbs_g=0.0, fat_g=10.0, fiber_g=0.0, default_portion_g=50),
        Food(name='Prosciutto cotto', category='Carne', kcal_per_100g=140, protein_g=20.0, carbs_g=1.0, fat_g=6.0, fiber_g=0.0, default_portion_g=50),
        Food(name='Bresaola', category='Carne', kcal_per_100g=150, protein_g=32.0, carbs_g=0.5, fat_g=2.0, fiber_g=0.0, default_portion_g=50),
        Food(name='Petto di pollo arrosto', category='Carne', kcal_per_100g=210, protein_g=28.0, carbs_g=1.0, fat_g=10.0, fiber_g=0.0, default_portion_g=100),

        # Pesce
        Food(name='Salmone fresco', category='Pesce', kcal_per_100g=208, protein_g=20.0, carbs_g=0.0, fat_g=13.0, fiber_g=0.0, default_portion_g=150),
        Food(name='Merluzzo fresco', category='Pesce', kcal_per_100g=82, protein_g=18.0, carbs_g=0.0, fat_g=0.7, fiber_g=0.0, default_portion_g=150),
        Food(name='Orata', category='Pesce', kcal_per_100g=96, protein_g=19.0, carbs_g=0.0, fat_g=2.0, fiber_g=0.0, default_portion_g=150),
        Food(name='Tonno al naturale (sgocciolato)', category='Pesce', kcal_per_100g=120, protein_g=25.0, carbs_g=0.0, fat_g=2.0, fiber_g=0.0, default_portion_g=80),
        Food(name='Sgombro', category='Pesce', kcal_per_100g=220, protein_g=19.0, carbs_g=0.0, fat_g=16.0, fiber_g=0.0, default_portion_g=150),
        Food(name='Trota', category='Pesce', kcal_per_100g=145, protein_g=20.0, carbs_g=0.0, fat_g=7.0, fiber_g=0.0, default_portion_g=150),
        Food(name='Gamberetti', category='Pesce', kcal_per_100g=85, protein_g=18.0, carbs_g=0.5, fat_g=1.0, fiber_g=0.0, default_portion_g=100),
        Food(name='Cozze', category='Pesce', kcal_per_100g=85, protein_g=12.0, carbs_g=3.0, fat_g=2.5, fiber_g=0.0, default_portion_g=200),

        # Uova e latticini
        Food(name='Uova di gallina', category='Latticini', kcal_per_100g=140, protein_g=12.5, carbs_g=0.5, fat_g=10.0, fiber_g=0.0, default_portion_g=60),
        Food(name='Latte intero', category='Latticini', kcal_per_100g=65, protein_g=3.3, carbs_g=4.8, fat_g=3.6, fiber_g=0.0, default_portion_g=200),
        Food(name='Latte parzialmente scremato', category='Latticini', kcal_per_100g=48, protein_g=3.5, carbs_g=5.0, fat_g=1.6, fiber_g=0.0, default_portion_g=200),
        Food(name='Latte scremato', category='Latticini', kcal_per_100g=35, protein_g=3.6, carbs_g=5.0, fat_g=0.2, fiber_g=0.0, default_portion_g=200),
        Food(name='Yogurt greco 0%', category='Latticini', kcal_per_100g=59, protein_g=10.0, carbs_g=3.0, fat_g=0.2, fiber_g=0.0, default_portion_g=150),
        Food(name='Yogurt intero', category='Latticini', kcal_per_100g=65, protein_g=4.0, carbs_g=4.5, fat_g=3.5, fiber_g=0.0, default_portion_g=125),
        Food(name='Mozzarella di bufala', category='Latticini', kcal_per_100g=280, protein_g=18.0, carbs_g=1.0, fat_g=22.0, fiber_g=0.0, default_portion_g=100),
        Food(name='Parmigiano Reggiano', category='Latticini', kcal_per_100g=420, protein_g=33.0, carbs_g=0.0, fat_g=30.0, fiber_g=0.0, default_portion_g=30),
        Food(name='Pecorino romano', category='Latticini', kcal_per_100g=390, protein_g=28.0, carbs_g=1.0, fat_g=30.0, fiber_g=0.0, default_portion_g=30),
        Food(name='Ricotta di vacca', category='Latticini', kcal_per_100g=145, protein_g=8.0, carbs_g=4.0, fat_g=11.0, fiber_g=0.0, default_portion_g=100),
        Food(name='Fiocchi di latte', category='Latticini', kcal_per_100g=95, protein_g=12.0, carbs_g=3.0, fat_g=4.0, fiber_g=0.0, default_portion_g=100),

        # Verdura
        Food(name='Spinaci', category='Verdura', kcal_per_100g=23, protein_g=3.0, carbs_g=1.5, fat_g=0.5, fiber_g=2.5, default_portion_g=150),
        Food(name='Broccoli', category='Verdura', kcal_per_100g=34, protein_g=3.0, carbs_g=4.0, fat_g=0.5, fiber_g=3.0, default_portion_g=200),
        Food(name='Zucchine', category='Verdura', kcal_per_100g=17, protein_g=1.5, carbs_g=2.5, fat_g=0.2, fiber_g=1.5, default_portion_g=200),
        Food(name='Pomodori maturi', category='Verdura', kcal_per_100g=18, protein_g=1.0, carbs_g=3.0, fat_g=0.2, fiber_g=1.5, default_portion_g=150),
        Food(name='Peperoni', category='Verdura', kcal_per_100g=26, protein_g=1.0, carbs_g=5.0, fat_g=0.3, fiber_g=2.0, default_portion_g=150),
        Food(name='Melanzane', category='Verdura', kcal_per_100g=24, protein_g=1.0, carbs_g=3.5, fat_g=0.2, fiber_g=3.0, default_portion_g=200),
        Food(name='Carote', category='Verdura', kcal_per_100g=39, protein_g=1.0, carbs_g=8.0, fat_g=0.2, fiber_g=3.0, default_portion_g=100),
        Food(name='Insalata lattuga', category='Verdura', kcal_per_100g=15, protein_g=1.5, carbs_g=2.0, fat_g=0.2, fiber_g=1.5, default_portion_g=80),
        Food(name='Rucola', category='Verdura', kcal_per_100g=25, protein_g=2.5, carbs_g=2.0, fat_g=0.5, fiber_g=1.5, default_portion_g=50),
        Food(name='Cavolfiore', category='Verdura', kcal_per_100g=25, protein_g=2.0, carbs_g=4.0, fat_g=0.3, fiber_g=2.5, default_portion_g=200),
        Food(name='Finocchi', category='Verdura', kcal_per_100g=28, protein_g=1.0, carbs_g=5.0, fat_g=0.2, fiber_g=3.0, default_portion_g=150),
        Food(name='Funghi champignon', category='Verdura', kcal_per_100g=22, protein_g=3.0, carbs_g=1.0, fat_g=0.5, fiber_g=1.5, default_portion_g=100),
        Food(name='Patate', category='Verdura', kcal_per_100g=85, protein_g=2.0, carbs_g=19.0, fat_g=0.1, fiber_g=1.5, default_portion_g=200),
        Food(name='Patate dolci', category='Verdura', kcal_per_100g=105, protein_g=2.0, carbs_g=24.0, fat_g=0.2, fiber_g=3.0, default_portion_g=200),
        Food(name='Asparagi', category='Verdura', kcal_per_100g=20, protein_g=2.5, carbs_g=2.5, fat_g=0.2, fiber_g=2.0, default_portion_g=150),
        Food(name='Fagiolini', category='Verdura', kcal_per_100g=31, protein_g=2.0, carbs_g=5.0, fat_g=0.2, fiber_g=3.0, default_portion_g=150),

        # Frutta
        Food(name='Mela', category='Frutta', kcal_per_100g=52, protein_g=0.3, carbs_g=13.0, fat_g=0.2, fiber_g=2.5, default_portion_g=200),
        Food(name='Pera', category='Frutta', kcal_per_100g=57, protein_g=0.4, carbs_g=14.0, fat_g=0.2, fiber_g=3.0, default_portion_g=200),
        Food(name='Banana', category='Frutta', kcal_per_100g=90, protein_g=1.2, carbs_g=21.0, fat_g=0.3, fiber_g=2.5, default_portion_g=150),
        Food(name='Arancia', category='Frutta', kcal_per_100g=45, protein_g=0.9, carbs_g=10.0, fat_g=0.2, fiber_g=2.0, default_portion_g=200),
        Food(name='Uva', category='Frutta', kcal_per_100g=70, protein_g=0.5, carbs_g=16.0, fat_g=0.2, fiber_g=1.5, default_portion_g=150),
        Food(name='Fragole', category='Frutta', kcal_per_100g=32, protein_g=0.7, carbs_g=6.0, fat_g=0.3, fiber_g=2.0, default_portion_g=150),
        Food(name='Mirtilli', category='Frutta', kcal_per_100g=57, protein_g=0.7, carbs_g=14.0, fat_g=0.3, fiber_g=2.5, default_portion_g=100),
        Food(name='Kiwi', category='Frutta', kcal_per_100g=61, protein_g=1.1, carbs_g=14.0, fat_g=0.5, fiber_g=3.0, default_portion_g=100),
        Food(name='Anguria', category='Frutta', kcal_per_100g=30, protein_g=0.6, carbs_g=7.0, fat_g=0.2, fiber_g=0.5, default_portion_g=250),
        Food(name='Fichi d\'India', category='Frutta', kcal_per_100g=55, protein_g=0.8, carbs_g=13.0, fat_g=0.2, fiber_g=5.0, default_portion_g=100),
        Food(name='Ciliegie', category='Frutta', kcal_per_100g=50, protein_g=1.0, carbs_g=11.0, fat_g=0.3, fiber_g=1.5, default_portion_g=150),

        # Grassi e condimenti
        Food(name='Olio extravergine d\'oliva', category='Grassi', kcal_per_100g=900, protein_g=0.0, carbs_g=0.0, fat_g=100.0, fiber_g=0.0, default_portion_g=10),
        Food(name='Olio di semi di girasole', category='Grassi', kcal_per_100g=900, protein_g=0.0, carbs_g=0.0, fat_g=100.0, fiber_g=0.0, default_portion_g=10),
        Food(name='Burro', category='Grassi', kcal_per_100g=760, protein_g=0.5, carbs_g=0.5, fat_g=84.0, fiber_g=0.0, default_portion_g=10),
        Food(name='Margarina', category='Grassi', kcal_per_100g=720, protein_g=0.2, carbs_g=0.5, fat_g=80.0, fiber_g=0.0, default_portion_g=10),
        Food(name='Mandorle', category='Grassi', kcal_per_100g=580, protein_g=21.0, carbs_g=10.0, fat_g=50.0, fiber_g=12.0, default_portion_g=30),
        Food(name='Noci', category='Grassi', kcal_per_100g=650, protein_g=15.0, carbs_g=7.0, fat_g=65.0, fiber_g=6.5, default_portion_g=30),
        Food(name='Avocado', category='Grassi', kcal_per_100g=160, protein_g=2.0, carbs_g=4.0, fat_g=15.0, fiber_g=6.5, default_portion_g=100),

        # Varie
        Food(name='Cioccolato fondente 85%', category='Varie', kcal_per_100g=600, protein_g=8.0, carbs_g=30.0, fat_g=50.0, fiber_g=10.0, default_portion_g=20),
        Food(name='Miele', category='Varie', kcal_per_100g=305, protein_g=0.3, carbs_g=82.0, fat_g=0.0, fiber_g=0.0, default_portion_g=15),
        Food(name='Zucchero bianco', category='Varie', kcal_per_100g=400, protein_g=0.0, carbs_g=100.0, fat_g=0.0, fiber_g=0.0, default_portion_g=5),
        Food(name='Caffè', category='Varie', kcal_per_100g=2, protein_g=0.1, carbs_g=0.0, fat_g=0.0, fiber_g=0.0, default_portion_g=150),
        Food(name='Tè verde', category='Varie', kcal_per_100g=1, protein_g=0.0, carbs_g=0.0, fat_g=0.0, fiber_g=0.0, default_portion_g=200),
        Food(name='Acqua naturale', category='Varie', kcal_per_100g=0, protein_g=0.0, carbs_g=0.0, fat_g=0.0, fiber_g=0.0, default_portion_g=250),
    ]

    existing_count = Food.query.count()
    if existing_count == 0:
        for food in INRN_FOODS:
            db.session.add(food)
        db.session.commit()
