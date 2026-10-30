import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

class AIService:
    def __init__(self):
        self.client = Groq(api_key=os.getenv('GROQ_API_KEY'))

    def generate_personalized_email(self, full_name, position, preferences, message, products):
        # Подобрать релевантные товары на основе предпочтений
        relevant_products = self._select_relevant_products(preferences, products)

        # Создать промт
        prompt = f"""
Создай персонализированное письмо.

Данные:
ФИО: {full_name}
Должность: {position}
Интересы: {', '.join(preferences)}

Исходный текст:
{message}

Доступные товары:
{chr(10).join([f"- {p['name']}: {p['description']}" for p in relevant_products])}

Сделай письмо:
- коротким
- персональным
- без шаблонности
- естественно интегрируй релевантные товары

Верни только текст письма.
"""

        model_name = os.getenv('GROQ_MODEL', 'llama-3.1-8b-instant')
        try:
            response = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=model_name,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise Exception(f"Ошибка генерации AI: {str(e)}")

    def _select_relevant_products(self, preferences, products):
        # Простая логика подбора: если предпочтение в описании товара
        relevant = []
        for product in products:
            for pref in preferences:
                if pref.lower() in product['description'].lower() or pref.lower() in product['name'].lower():
                    relevant.append(product)
                    break
        return relevant if relevant else products[:2]  # Если нет релевантных, взять первые 2