"""All foods come from Open Food Facts — no preloaded database."""


def populate_foods(db):
    """Empty the foods table — all foods come from barcode scan / OFF search."""
    from models import Food
    Food.query.delete()
    db.session.commit()
    return 0


FOOD_CATEGORIES = []
