
import os
from datetime import datetime

QUEST_LOG_FILE = "quest_history.txt"

def log_quest_completion(task_subject, is_boss, sessions, xp, gold):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(QUEST_LOG_FILE, "a") as f:
        f.write(f"=== {timestamp} ===\n")
        f.write(f"Task: {task_subject}\n")
        f.write(f"Boss Fight: {'Yes' if is_boss else 'No'}\n")
        f.write(f"Sessions: {sessions}\n")
        f.write(f"XP Earned: {xp}\n")
        f.write(f"Gold Earned: {gold}\n\n")

def view_quest_history():
    if not os.path.exists(QUEST_LOG_FILE):
        print("📭 No quest history yet.")
        return
    print("\n📜 Quest History Log:")
    with open(QUEST_LOG_FILE, "r") as f:
        print(f.read())
