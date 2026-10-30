import asyncio
import os
import time
import logging
import sys
from telegram import Update, ReplyKeyboardMarkup, error as telegram_error
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes
from dotenv import load_dotenv
from ai_service import AIService
from email_service import EmailService
from data_handler import DataHandler
from logger import Logger
from recipient_manager import RecipientManager

load_dotenv()

# Состояния
ADDING_COUNT, ADDING_FULL_NAME, ADDING_POSITION, ADDING_EMAIL, ADDING_PREFERENCES, SELECT_DELETE_INDEX, WAITING_FOR_MESSAGE, WAITING_FOR_CONFIRMATION = range(8)

class TelegramBot:
    def __init__(self):
        self.ai_service = AIService()
        self.email_service = EmailService()
        self.data_handler = DataHandler()
        self.recipient_manager = RecipientManager()
        self.logger = Logger()
        self.recipients = self.recipient_manager.load_recipients()
        self.products = self.data_handler.load_products()
        self.pending_emails = []  # Список (email, subject, body) для отправки

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            ["/send", "/addrecipients"],
            ["/listrecipients", "/clearrecipients"],
            ["/menu"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
        await update.message.reply_text(
            "Привет! Выберите действие из меню ниже или используйте команды.",
            reply_markup=reply_markup
        )

    async def menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            ["/send", "/addrecipients"],
            ["/listrecipients", "/clearrecipients"],
            ["/start"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
        await update.message.reply_text(
            "Меню команд:\n"
            "/send - Начать рассылку\n"
            "/addrecipients - Добавить получателей\n"
            "/listrecipients - Посмотреть список\n"
            "/clearrecipients - Очистить список\n"
            "/menu - Показать это меню",
            reply_markup=reply_markup
        )

    async def send_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Отправь текст сообщения для рассылки.")
        return WAITING_FOR_MESSAGE

    async def add_recipients_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['new_recipients'] = []
        context.user_data['recipient_count'] = 0
        context.user_data['current_index'] = 0
        context.user_data['current_recipient'] = {}
        await update.message.reply_text("Сколько получателей вы хотите добавить? Введите число.")
        return ADDING_COUNT

    async def receive_recipient_count(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text.strip()
        if not text.isdigit() or int(text) <= 0:
            await update.message.reply_text("Введите корректное положительное число получателей.")
            return ADDING_COUNT

        context.user_data['recipient_count'] = int(text)
        context.user_data['current_index'] = 1
        context.user_data['current_recipient'] = {}
        await update.message.reply_text(f"Введите ФИО получателя {context.user_data['current_index']}:")
        return ADDING_FULL_NAME

    async def receive_full_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['current_recipient']['full_name'] = update.message.text.strip()
        await update.message.reply_text("Введите должность получателя:")
        return ADDING_POSITION

    async def receive_position(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['current_recipient']['position'] = update.message.text.strip()
        await update.message.reply_text("Введите email получателя:")
        return ADDING_EMAIL

    async def receive_email(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        email = update.message.text.strip()
        if '@' not in email or '.' not in email:
            await update.message.reply_text("Введите корректный email.")
            return ADDING_EMAIL

        context.user_data['current_recipient']['email'] = email
        await update.message.reply_text(
            "Введите интересы получателя через запятую, например: CRM, аналитика, автоматизация"
        )
        return ADDING_PREFERENCES

    async def receive_preferences(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        preferences = [item.strip() for item in update.message.text.split(',') if item.strip()]
        context.user_data['current_recipient']['preferences'] = preferences

        new_recipient = context.user_data['current_recipient'].copy()
        context.user_data['new_recipients'].append(new_recipient)

        if context.user_data['current_index'] >= context.user_data['recipient_count']:
            self.recipients = self.recipient_manager.add_recipients(context.user_data['new_recipients'])
            await update.message.reply_text(
                f"Добавлено {len(context.user_data['new_recipients'])} получателей. Всего в списке: {len(self.recipients)}."
            )
            return ConversationHandler.END

        context.user_data['current_index'] += 1
        context.user_data['current_recipient'] = {}
        await update.message.reply_text(f"Введите ФИО получателя {context.user_data['current_index']}:" )
        return ADDING_FULL_NAME

    async def list_recipients(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.recipients = self.recipient_manager.load_recipients()
        if not self.recipients:
            await update.message.reply_text(
                "Список получателей пуст. Добавьте новых получателей командой /addrecipients."
            )
            return ConversationHandler.END

        items = []
        for idx, recipient in enumerate(self.recipients, start=1):
            prefs = ", ".join(recipient.get('preferences', [])) or "нет"
            items.append(
                f"{idx}. {recipient['full_name']}\nДолжность: {recipient['position']}\nEmail: {recipient['email']}\nИнтересы: {prefs}"
            )

        await self._send_chunked_message(update, "Список получателей:\n\n" + "\n\n".join(items))
        await update.message.reply_text(
            "Введите номер получателя для удаления или /cancel для выхода."
        )
        return SELECT_DELETE_INDEX

    async def delete_recipient_by_index(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text.strip()
        if not text.isdigit():
            await update.message.reply_text("Введите номер получателя числом.")
            return SELECT_DELETE_INDEX

        index = int(text)
        self.recipients = self.recipient_manager.load_recipients()
        if index < 1 or index > len(self.recipients):
            await update.message.reply_text("Неверный номер. Введите номер из списка.")
            return SELECT_DELETE_INDEX

        removed = self.recipients.pop(index - 1)
        self.recipient_manager.save_recipients(self.recipients)
        await update.message.reply_text(
            f"Удален получатель {removed['full_name']} ({removed['email']}). Всего в списке: {len(self.recipients)}."
        )
        return ConversationHandler.END

    async def clear_recipients(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.recipient_manager.save_recipients([])
        self.recipients = []
        await update.message.reply_text("Список получателей очищен.")

    async def receive_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_message = update.message.text
        context.user_data['user_message'] = user_message

        self.recipients = self.recipient_manager.load_recipients()
        if not self.recipients:
            await update.message.reply_text(
                "Список получателей пуст. Добавьте получателей командой /addrecipients."
            )
            return ConversationHandler.END

        self.pending_emails = []
        for recipient in self.recipients:
            try:
                generated_email = await asyncio.to_thread(
                    self.ai_service.generate_personalized_email,
                    recipient['full_name'], recipient['position'], recipient.get('preferences', []),
                    user_message, self.products
                )
                subject = f"Персональное предложение для {recipient['full_name']}"
                self.pending_emails.append((recipient['email'], subject, generated_email))

                preview_text = (
                    f"Получатель: {recipient['full_name']} ({recipient['email']})\n"
                    f"Должность: {recipient['position']}\n"
                    f"Интересы: {', '.join(recipient.get('preferences', [])) or 'нет'}\n\n"
                    f"{generated_email}"
                )
                await self._send_chunked_message(update, preview_text)
                await update.message.reply_text("---")
            except Exception as e:
                await update.message.reply_text(
                    f"Ошибка для {recipient['full_name']}: {str(e)}"
                )

        await update.message.reply_text("Предпросмотр всех писем завершен. Подтверди отправку: /confirm или /cancel")
        return WAITING_FOR_CONFIRMATION

    async def _send_chunked_message(self, update: Update, text: str):
        max_length = 4000
        if len(text) <= max_length:
            await update.message.reply_text(text)
            return

        chunks = []
        current = []
        current_len = 0
        for part in text.split('\n\n'):
            part_text = part.strip()
            if not part_text:
                continue
            part_len = len(part_text) + 2
            if current_len + part_len > max_length:
                chunks.append("\n\n".join(current))
                current = [part_text]
                current_len = len(part_text)
            else:
                current.append(part_text)
                current_len += part_len
        if current:
            chunks.append("\n\n".join(current))

        for chunk in chunks:
            await update.message.reply_text(chunk)

    async def confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_message = context.user_data.get('user_message')
        sent_count = 0
        for email, subject, body in self.pending_emails:
            try:
                await asyncio.to_thread(self.email_service.send_email, email, subject, body)
                # Логировать успех
                recipient = next(r for r in self.recipients if r['email'] == email)
                selected_products = self.ai_service._select_relevant_products(recipient.get('preferences', []), self.products)
                await asyncio.to_thread(
                    self.logger.log_result,
                    user_message,
                    recipient,
                    recipient.get('preferences', []),
                    selected_products,
                    body,
                    "sent"
                )
                sent_count += 1
                await asyncio.sleep(5)  # Ограничение скорости
            except Exception as e:
                recipient = next(r for r in self.recipients if r['email'] == email)
                selected_products = self.ai_service._select_relevant_products(recipient.get('preferences', []), self.products)
                await asyncio.to_thread(
                    self.logger.log_result,
                    user_message,
                    recipient,
                    recipient.get('preferences', []),
                    selected_products,
                    body,
                    "error",
                    str(e)
                )

        await update.message.reply_text(f"Отправлено {sent_count} писем.")
        return ConversationHandler.END

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Рассылка отменена.")
        return ConversationHandler.END

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger = logging.getLogger(__name__)
        logger.error(msg="Exception while handling an update:", exc_info=context.error)

        if isinstance(context.error, telegram_error.Conflict):
            logger.error("Conflict detected: terminated by other getUpdates request. Only one bot instance should be running. Exiting.")
            sys.exit(1)

        if isinstance(context.error, telegram_error.NetworkError):
            logger.warning(
                "Telegram network error: %s. This may be transient; the bot will continue polling.",
                context.error
            )
            return

        logger.error("Unhandled Telegram error: %s", context.error)

    def run(self):
        application = (
            Application.builder()
            .token(os.getenv('TELEGRAM_BOT_TOKEN'))
            .get_updates_connect_timeout(10)
            .get_updates_read_timeout(20)
            .get_updates_write_timeout(10)
            .get_updates_pool_timeout(5)
            .build()
        )

        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler("send", self.send_command),
                CommandHandler("addrecipients", self.add_recipients_command),
                CommandHandler("listrecipients", self.list_recipients),
            ],
            states={
                ADDING_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.receive_recipient_count)],
                ADDING_FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.receive_full_name)],
                ADDING_POSITION: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.receive_position)],
                ADDING_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.receive_email)],
                ADDING_PREFERENCES: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.receive_preferences)],
                SELECT_DELETE_INDEX: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.delete_recipient_by_index)],
                WAITING_FOR_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.receive_message)],
                WAITING_FOR_CONFIRMATION: [
                    CommandHandler("confirm", self.confirm),
                    CommandHandler("cancel", self.cancel)
                ],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)],
        )

        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("menu", self.menu))
        application.add_handler(CommandHandler("clearrecipients", self.clear_recipients))
        application.add_handler(conv_handler)

        application.add_error_handler(self.error_handler)

        application.run_polling(poll_interval=0.5, timeout=20)

if __name__ == '__main__':
    bot = TelegramBot()
    bot.run()