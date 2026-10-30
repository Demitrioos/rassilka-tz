import json
import os

class RecipientManager:
    def __init__(self, path='data/recipients.json'):
        self.path = path
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        directory = os.path.dirname(self.path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        if not os.path.exists(self.path):
            with open(self.path, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=4)

    def load_recipients(self):
        with open(self.path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_recipients(self, recipients):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(recipients, f, ensure_ascii=False, indent=4)

    def add_recipients(self, new_recipients):
        recipients = self.load_recipients()
        recipients.extend(new_recipients)
        self.save_recipients(recipients)
        return recipients
