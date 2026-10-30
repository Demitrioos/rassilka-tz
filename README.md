# Персонализированная Email-рассылка через Telegram-бота

## Описание
Система для генерации и отправки персонализированных email через Telegram-бота с использованием AI.

## Установка
1. Установите зависимости: `pip install -r requirements.txt`
2. Настройте `.env` файл с вашими ключами:
   - TELEGRAM_BOT_TOKEN: Токен Telegram-бота
   - GROQ_API_KEY: Ключ API Groq
   - GROQ_MODEL: `llama-3.1-8b-instant` (по умолчанию)
   - SMTP_SERVER: `smtp.gmail.com`
   - SMTP_PORT: `587` для STARTTLS или `465` для SSL
   - SMTP_USERNAME: ваш email
   - SMTP_PASSWORD: пароль приложения или SMTP-пароль
3. Запустите: `python main.py`

## Использование
- /start: Приветствие и показ меню
- /menu: Показать меню команд
- /addrecipients: Добавить новых получателей и сохранить их в `data/recipients.json`
- /listrecipients: Посмотреть текущий список получателей
- /clearrecipients: Очистить список получателей
- /send: Начать рассылку, затем отправить текст сообщения
- Бот сгенерирует предпросмотр для каждого получателя отдельно
- /confirm: Отправить письма
- /cancel: Отменить

## Данные
- Получатели: `data/recipients.json`
- Товары: `data/products.json`
- Логи: `logs/`

## Безопасность
Не храните ключи в коде, используйте .env.