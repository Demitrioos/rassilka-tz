import json
import os

class DataHandler:
    @staticmethod
    def load_recipients():
        with open('data/recipients.json', 'r', encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def load_products():
        with open('data/products.json', 'r', encoding='utf-8') as f:
            return json.load(f)