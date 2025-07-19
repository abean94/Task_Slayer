
import random
import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "1"
import time
import pygame
import pandas as pd
from datetime import datetime
from save_load_module import save_progress, load_progress, delete_save
from quest_history import log_quest_completion, view_quest_history
import datetime
import threading

# === Configs ===
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "1"
VICTORY_SOUND = 'adventure-music-164795.mp3'
BREAK_SOUND = 'mixkit-happy-bells-notification-937.wav'
FAIL_SOUND = 'failure-to-success-motivation-157585.mp3'
BOSS_BATTLE = 'evil-boss-appears-short-instrumental-178343.mp3'
BREAK_DURATION = 600
RETRY_DELAY = 300
EXCEL_FILE = 'tickets.xlsx'

# === Game State ===
effort_points = 0
gold = 0
inventory = []
auto_win_initiative = False
double_gold_next = False

# === Hero Classes and Perks ===
character_classes = {
    "Code Knight": {"Strength": 3, "Focus": 5, "Wisdom": 2},
    "Cleric of Clarity": {"Strength": 2, "Focus": 4, "Wisdom": 5},
    "Focus Ranger": {"Strength": 4, "Focus": 5, "Wisdom": 1},
    "Bard of Burnout": {"Strength": 1, "Focus": 3, "Wisdom": 6},
    "Monk of Momentum": {"Strength": 2, "Focus": 6, "Wisdom": 2}
}

class_perks = {
    "Code Knight": {"bonus_xp_boss": 1.2, "gold_multiplier": 1.0, "initiative_bonus": 0},
    "Cleric of Clarity": {"bonus_xp_boss": 1.0, "gold_multiplier": 1.0, "initiative_bonus": 1},
    "Focus Ranger": {"bonus_xp_boss": 1.0, "gold_multiplier": 1.0, "initiative_bonus": 2},
    "Bard of Burnout": {"bonus_xp_boss": 1.0, "gold_multiplier": 1.25, "initiative_bonus": 0},
    "Monk of Momentum": {"bonus_xp_boss": 1.0, "gold_multiplier": 1.0, "initiative_bonus": 0, "streak_bonus": 5}
}

# === Load Tasks ===
task_df = pd.read_excel(EXCEL_FILE, sheet_name='Tickets')
open_tasks = task_df[task_df['Status'].str.lower() == 'open'].reset_index(drop=True)

shop_items = {
    "Focus Potion": {"cost": 20, "effect": "Gain +5 XP next session"},
    "Time Crystal": {"cost": 35, "effect": "Skip initiative once"},
    "Golden Keyboard": {"cost": 50, "effect": "Double gold on next quest"},
    "Productivity Cape": {"cost": 75, "effect": "Auto-complete one task"}
}

def load_hero_name():
    save_file = "hero_name.txt"
    if os.path.exists(save_file):
        with open(save_file, "r") as f:
            return f.read().strip()
    name = input("Enter your hero name: ").strip()
    with open(save_file, "w") as f:
        f.write(name)
    return name

def choose_class():
    print("Choose your character class:")
    for i, (cls, stats) in enumerate(character_classes.items(), start=1):
        print(f"{i}. {cls} — Stats: {stats}")
    while True:
        try:
            choice = int(input("> "))
            if 1 <= choice <= len(character_classes):
                class_name = list(character_classes.keys())[choice - 1]
                return class_name, character_classes[class_name]
        except ValueError:
            continue

def show_character_sheet(hero_name, char_class, stats, xp, level):
    clear_screen()
    print("\n📜 Character Sheet")
    print(f"Name: {hero_name}")
    print(f"Class: {char_class}")
    print(f"Level: {level}")
    print(f"XP: {xp}")
    print("Stats:")
    for stat, val in stats.items():
        print(f"  {stat}: {val}")

def play_notification_sound(audio_file):
    pygame.mixer.init()
    if os.path.exists(audio_file):
        pygame.mixer.music.load(audio_file)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)

def countdown(seconds):
    for i in range(seconds, 0, -1):
        print(f"Retrying in {i}...", end='\r')
        time.sleep(1)

def get_random_task():
    index = random.randint(0, len(open_tasks) - 1)
    task = open_tasks.iloc[index]
    return {'task_id': task['Task ID'], 'subject': task['Subject'], 'is_boss': bool(task['Hard Task']) if not pd.isna(task['Hard Task']) else False}
def initiative_battle(char_class, char_stats):
    global auto_win_initiative, inventory

    print("\n⚔️ You approach the task. Do you want to prepare?")
    if input("Use an item to boost readiness? (Y/N): ").strip().lower().startswith("y"):
        print("\n🎒 Inventory:")
        for i, item in enumerate(inventory, 1):
            print(f"{i}. {item}")
        choice = input("Choose item number or press Enter to cancel: ").strip()
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(inventory):
                item = inventory.pop(idx)
                print(f"✨ You use {item} to boost your focus...")
                if item == "Time Crystal":
                    auto_win_initiative = True
                elif item == "Focus Potion":
                    bonus_from_item = 3
                else:
                    print(f"🔹 {item} has no effect on initiative.")
            else:
                print("❌ Invalid choice.")
        else:
            print("You skip using an item.")
    
    # Auto-win shortcut
    if auto_win_initiative:
        print("🌀 Your Time Crystal activates! You win the initiative.")
        auto_win_initiative = False
        return True

    # Calculate readiness with class bonus + stat bonus + item boost
    bonus_class = class_perks.get(char_class, {}).get("initiative_bonus", 0)
    bonus_stats = char_stats.get("Focus", 0) // 2  # scale if needed
    bonus_from_item = bonus_from_item if 'bonus_from_item' in locals() else 0

    player_roll = random.randint(1, 20) + bonus_class + bonus_stats + bonus_from_item
    dm_roll = random.randint(1, 20)

    print(f"You rolled: {player_roll} (Base + Class + Stats + Items)")
    print(f"Enemy rolled: {dm_roll}")
    time.sleep(2)

    if player_roll > dm_roll:
        return True
    elif player_roll < dm_roll:
        play_notification_sound(FAIL_SOUND)
        print("You are not yet ready, come back when you are more prepared...")
        return False
    else:
        print("It's a tie! Roll again.")
        return None

def apply_class_perks(char_class, is_boss, sessions, base_xp, base_gold, streak):
    global double_gold_next
    perks = class_perks.get(char_class, {})
    xp = int(base_xp * perks.get("bonus_xp_boss", 1.0)) if is_boss else base_xp
    gold_amt = int(base_gold * perks.get("gold_multiplier", 1.0))
    if double_gold_next:
        gold_amt *= 2
    if perks.get("streak_bonus") and streak > 1:
        xp += (streak * perks["streak_bonus"])
    return xp, gold_amt

def reward_player(char_class, is_boss, sessions=1):
    global effort_points, gold, inventory, double_gold_next
    base_xp = (25 if is_boss else 10) * sessions
    base_gold = (15 if is_boss else 5) * sessions
    xp, gold_earned = apply_class_perks(char_class, is_boss, sessions, base_xp, base_gold, sessions)
    effort_points += xp
    gold += gold_earned
    double_gold_next = False
    print(f"\n✅ Quest complete! Earned {xp} XP and {gold_earned} gold.")
    if is_boss:
        for _ in range(sessions):
            item = random.choice(list(shop_items.keys()))
            inventory.append(item)
        print(f"🏆 Boss reward: {sessions} item(s) added to inventory!")
    return xp, gold_earned
    
def use_item():
    global inventory, effort_points, auto_win_initiative, double_gold_next, gold
    if not inventory:
        print("🎒 Your inventory is empty!")
        return
    print("\n🎒 Inventory:")
    for i, item in enumerate(inventory, 1):
        print(f"{i}. {item}")
    choice = input("Choose an item to use or press Enter to cancel: ").strip()
    if not choice:
        return
    try:
        idx = int(choice) - 1
        item = inventory.pop(idx)
        print(f"✨ You used {item}!")
        if item == "Focus Potion":
            effort_points += 5
            print("🧠 +5 XP gained!")
        elif item == "Time Crystal":
            auto_win_initiative = True
        elif item == "Golden Keyboard":
            double_gold_next = True
        elif item == "Productivity Cape":
            effort_points += 10
            gold += 10
            print("⚡ A task was auto-completed!")
    except (ValueError, IndexError):
        print("❌ Invalid selection.")

def visit_shop():
    global gold, inventory
    while True:
        print("\n🛒 Welcome to the Guild Shop!")
        print(f"Gold: {gold}")
        for i, (item, details) in enumerate(shop_items.items(), 1):
            print(f"{i}. {item} — {details['cost']} gold — {details['effect']}")
        print("Type the item name to buy, or press Enter to leave.")
        choice = input("> ").strip()
        if not choice:
            clear_screen()
            break
        if choice not in shop_items:
            print("❌ Invalid item.")
            continue
        if gold >= shop_items[choice]['cost']:
            gold -= shop_items[choice]['cost']
            inventory.append(choice)
            print(f"✅ You purchased: {choice}")
        else:
            print("❌ Not enough gold.")

def log_journal_entry(task_subject, session_count):
    log_file = "session_journal.txt"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = input("What did you accomplish during this quest?\n> ").strip()
    with open(log_file, "a") as f:
        f.write(f"=== {timestamp} ===\n")
        f.write(f"Task: {task_subject}\n")
        f.write(f"Sessions: {session_count}\n")
        f.write(f"Entry: {entry}\n\n")
    print("✅ Journal saved!")

def view_journal():
    log_file = "session_journal.txt"
    if os.path.exists(log_file):
        print("\n📖 Journal Entries:")
        with open(log_file, "r") as f:
            print(f.read())
    else:
        print("📭 No journal entries yet.")

def remove_task_by_id(task_id):
    global open_tasks
    open_tasks = open_tasks[open_tasks['Task ID'] != task_id].reset_index(drop=True)

def take_break():
    print(f"\n⏳ Taking a {BREAK_DURATION}-minute break...")
    play_notification_sound(BREAK_SOUND)
    time.sleep(2)

def run_quest(char_class, char_stats):
    print("\n🌀 Finding you a quest...\n")
    time.sleep(2)
    task_info = get_random_task()
    print(f"🎯 Task: {task_info['subject']}")
    if task_info['is_boss']:
        print("⚠️ Boss-level task! Prepare for battle!")
        play_notification_sound(BOSS_BATTLE)
    while True:
        result = initiative_battle(char_class, char_stats)
        if result is None:
            continue
        elif result is False:
            countdown(RETRY_DELAY)
        else:
            play_notification_sound(VICTORY_SOUND)
            return task_info
        
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def wait_for_done(done_flag):
    while not done_flag["stop"]:
        user_input = input("> ").strip().lower()
        if user_input == "done":
            done_flag["stop"] = True

def focus_session(duration_seconds):
    done_flag = {"stop": False}
    print(f"⏳ Focus session started. Type 'done' when finished early, or wait {duration_seconds} seconds.")
    start_time = time.time()

    input_thread = threading.Thread(target=wait_for_done, args=(done_flag,))
    input_thread.daemon = True
    input_thread.start()

    while not done_flag["stop"]:
        elapsed = time.time() - start_time
        if elapsed >= duration_seconds:
            print("⏰ Time's up!")
            break
        time.sleep(1)

    end_time = time.time()
    actual_minutes = max(1, round((end_time - start_time) / 60))
    print(f"🧠 You focused for {actual_minutes} minute(s).")
    return actual_minutes

def main_menu():
    print("\n🏰 Taskslayer Hub")
    print("1. Start New Quest")
    print("2. View Character Sheet")
    print("3. Use Item")
    print("4. Visit Guild Shop")
    print("5. View Journal")
    print("6. View Quest History")
    print("7. Exit Game")
    return input("> ").strip()

def main():
    global effort_points
    save_data = load_progress()
    if save_data:
        hero_name = save_data["hero_name"]
        char_class = save_data["hero_class"]
        effort_points = save_data["effort_points"]
        gold = save_data["gold"]
        inventory = save_data["inventory"]
        char_stats = character_classes[char_class]
        print(f"🔄 Loaded save for {hero_name} the {char_class}!")
    else:
        hero_name = load_hero_name()
        char_class, char_stats = choose_class()
        effort_points = 0
        gold = 0
        inventory = []
    clear_screen()
    while True:
        choice = main_menu()
        save_progress(hero_name, char_class, effort_points, gold, inventory)
        if choice == "1":
            clear_screen()
            task = run_quest(char_class, char_stats)
            session_streak = 0
            while True:
                input(f"\nPress any key to begin: {task['subject']} ")
                actual_minutes = focus_session(BREAK_DURATION)
                take_break()
                session_streak += actual_minutes
                if input("Continue same quest? (Y/N): ").strip().lower().startswith("y"):
                    continue
                xp, gold_earned = reward_player(char_class, task['is_boss'], sessions=session_streak)
                log_quest_completion(task['subject'], task['is_boss'], session_streak, xp, gold_earned)
                log_journal_entry(task['subject'], session_streak)
                remove_task_by_id(task['task_id'])
                break
        elif choice == "2":
            level = 1 + effort_points // 100
            show_character_sheet(hero_name, char_class, char_stats, effort_points, level)
        elif choice == "3":
            clear_screen()
            use_item()
        elif choice == "4":
            clear_screen()
            visit_shop()
        elif choice == "5":
            clear_screen()
            view_journal()
        elif choice == "6":
            clear_screen()
            view_quest_history()
        elif choice == "7":
            print("👋 Farewell, brave hero!")
            break
        else:
            print("❌ Invalid option.")

if __name__ == "__main__":
    main()
