import json
import os
import uuid
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class Logger:
    def __init__(self):
        self.log_dir = os.getenv('LOG_DIR', 'logs')

    def log_result(self, user_message, recipient, preferences, selected_products, generated_email, status, error=None):
        log_entry = {
            "request_id": str(uuid.uuid4()),
            "created_at": datetime.now().isoformat(),
            "user_message": user_message,
            "recipient": recipient,
            "preferences": preferences,
            "selected_products": selected_products,
            "generated_email": generated_email,
            "status": status,
            "error": error
        }

        filename = f"{self.log_dir}/log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(log_entry, f, ensure_ascii=False, indent=4)