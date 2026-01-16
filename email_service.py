import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv()

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

def send_otp_email(email: str, name: str, otp: str):
    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = f"CRM System <{SMTP_USERNAME}>"
        msg['To'] = email
        msg['Subject'] = "Your Verification OTP"
        
        html = f"""
        <html>
            <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 20px; background-color: #f4f7f6;">
                <div style="max-width: 500px; margin: 0 auto; background: #ffffff; padding: 30px; border-radius: 12px; border: 1px solid #e1e4e8; text-align: center;">
                    <h2 style="color: #1a1a1b;">Verification Required</h2>
                    <p style="color: #4a4a4a; font-size: 16px;">Hello {name}, use the code below to verify your account:</p>
                    <div style="background: #007bff; color: #ffffff; padding: 20px; margin: 25px 0; font-size: 32px; font-weight: bold; border-radius: 8px; letter-spacing: 8px;">
                        {otp}
                    </div>
                    <p style="color: #7f8c8d; font-size: 13px;">This code will expire in 30 minutes for security reasons.</p>
                </div>
            </body>
        </html>
        """
        msg.attach(MIMEText(html, 'html'))
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"--- [ERROR] OTP Email Failure: {e} ---")
        return False

def send_ai_response_email(email: str, lead_name: str, ai_message: str, message_id: str = None):
    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = f"AI Solutions Team <{SMTP_USERNAME}>"
        msg['To'] = email
        msg['Subject'] = "Re: Your Project Inquiry"
        
        if message_id:
            msg.add_header('In-Reply-To', message_id)
            msg.add_header('References', message_id)

        formatted_message = ai_message.replace("\n", "<br>")

        html = f"""
        <html>
            <body style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; padding: 20px; background-color: #fdfdfd;">
                <div style="max-width: 650px; margin: 0 auto; background: #ffffff; padding: 40px; border: 1px solid #eeeeee; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
                    <div style="font-size: 16px; color: #2c3e50; line-height: 1.8;">
                        {formatted_message}
                    </div>
                    <div style="margin-top: 30px; padding-top: 20px; border-top: 2px solid #f8f9fa;">
                        <p style="margin: 0; color: #34495e; font-weight: bold;">Best regards,</p>
                        <p style="margin: 5px 0; color: #007bff; font-size: 15px;">AI Solutions Executive Team</p>
                        <p style="margin: 0; color: #bdc3c7; font-size: 12px;">Automated Business Intelligence Division</p>
                    </div>
                </div>
            </body>
        </html>
        """
        msg.attach(MIMEText(html, 'html'))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"--- [ERROR] AI Response Email Failure: {e} ---")
        return False