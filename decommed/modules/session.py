import os
import json
import datetime

class SessionManager:
    def __init__(self, directory="sessions"):
        self.directory = directory
        os.makedirs(self.directory, exist_ok=True)
        self.current_session = None

    def create_new_session(self):
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        self.current_session = {
            "id": f"session_{timestamp}",
            "messages": [],
            "created_at": timestamp,
            "updated_at": timestamp
        }
        self.save_session()

    def save_session(self):
        if not self.current_session:
            return
        self.current_session["updated_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        filepath = os.path.join(self.directory, f"{self.current_session['id']}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.current_session, f, indent=2)

    def load_sessions(self):
        sessions = []
        for file in os.listdir(self.directory):
            if file.endswith(".json"):
                with open(os.path.join(self.directory, file), "r", encoding="utf-8") as f:
                    sessions.append(json.load(f))
        return sessions

    def delete_session(self, session_id):
        filepath = os.path.join(self.directory, f"{session_id}.json")
        if os.path.exists(filepath):
            os.remove(filepath)

    def export_session(self, session_id, export_path):
        filepath = os.path.join(self.directory, f"{session_id}.json")
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
