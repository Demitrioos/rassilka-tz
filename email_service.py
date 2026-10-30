import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

class EmailService:
    def __init__(self):
        self.smtp_server = os.getenv('SMTP_SERVER')
        self.smtp_port = int(os.getenv('SMTP_PORT'))
        self.username = os.getenv('SMTP_USERNAME')
        self.password = os.getenv('SMTP_PASSWORD')

    def send_email(self, to_email, subject, body):
        try:
            msg = MIMEMultipart()
            msg['From'] = self.username
            msg['To'] = to_email
            msg['Subject'] = subject

            msg.attach(MIMEText(body, 'plain'))

            if self.smtp_port == 465:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=30)
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30)
                server.ehlo()
                server.starttls()
                server.ehlo()

            server.login(self.username, self.password)
            server.sendmail(self.username, to_email, msg.as_string())
            server.quit()
            return True
        except Exception as e:
            raise Exception(f"Ошибка отправки email: {str(e)}")