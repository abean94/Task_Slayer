
import json
import os

SAVE_FILE = "game_save.json"

def save_progress(hero_name, hero_class, effort_points, gold, inventory):
    data = {
        "hero_name": hero_name,
        "hero_class": hero_class,
        "effort_points": effort_points,
        "gold": gold,
        "inventory": inventory
    }
    with open(SAVE_FILE, "w") as f:
        json.dump(data, f, indent=2)

def load_progress():
    if not os.path.exists(SAVE_FILE):
        return None
    with open(SAVE_FILE, "r") as f:
        data = json.load(f)
    return data

def delete_save():
    if os.path.exists(SAVE_FILE):
        os.remove(SAVE_FILE)
