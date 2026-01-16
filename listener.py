import imaplib
import email
import os
import time
from database import SessionLocal
import models
from langgraph_workflow_service import process_lead_reply
from email_service import send_ai_response_email 

def start_email_monitor():
    while True:
        db = SessionLocal()
        try:
            imap_server = os.getenv("IMAP_SERVER", "imap.gmail.com")
            email_user = os.getenv("EMAIL_USER")
            email_pass = os.getenv("EMAIL_PASSWORD")

            if not email_user or not email_pass:
                print("--- [ERROR] IMAP Credentials missing in .env ---")
                time.sleep(60)
                continue

            mail = imaplib.IMAP4_SSL(imap_server)
            mail.login(email_user, email_pass)
            mail.select("inbox")

            _, data = mail.search(None, 'UNSEEN')
            
            for num in data[0].split():
                _, msg_data = mail.fetch(num, '(RFC822)')
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        sender = email.utils.parseaddr(msg['From'])[1]
                        
                        lead = db.query(models.Lead).filter(models.Lead.email == sender).first()
                        
                        if lead:
                            body = extract_email_body(msg)
                            process_and_save_interaction(db, lead, body)
                            
            mail.logout()
        except Exception as e:
            print(f"--- [ERROR] Listener Engine: {e} ---")
        finally:
            db.close()
        
        time.sleep(30)

def extract_email_body(msg):
    try:
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload(decode=True)
                    return payload.decode(errors='ignore') if payload else ""
        else:
            payload = msg.get_payload(decode=True)
            return payload.decode(errors='ignore') if payload else ""
    except Exception:
        return ""
    return ""

def process_and_save_interaction(db, lead, message):
    try:
        safe_name = str(lead.name) if lead.name else "Valued Client"
        safe_budget = int(lead.budget) if lead.budget is not None else 0
        safe_service = str(lead.service_type) if lead.service_type else "AI Services"
        safe_message = str(message) if message else "Hello"

        lead_note = models.LeadNote(lead_id=lead.id, note=safe_message, sender="lead")
        db.add(lead_note)
        db.flush() 

        history_objs = db.query(models.LeadNote).filter(
            models.LeadNote.lead_id == lead.id
        ).order_by(models.LeadNote.created_at.desc()).limit(10).all()
        
        history = [
            {"sender": n.sender if n.sender else "unknown", "message": n.note if n.note else ""} 
            for n in reversed(history_objs)
        ]
        
        lead_info = {
            "name": safe_name,
            "budget": safe_budget,
            "service_type": safe_service,
            "last_message": safe_message
        }
        
        ai_reply_text = process_lead_reply(lead_info, history)
        
        if not ai_reply_text:
            ai_reply_text = "Thank you for your message. We will get back to you shortly."

        email_success = send_ai_response_email(
            email=lead.email,
            lead_name=safe_name,
            ai_message=ai_reply_text
        )

        if email_success:
            ai_note = models.LeadNote(lead_id=lead.id, note=ai_reply_text, sender="ai")
            db.add(ai_note)
            
            lead.status = models.LeadStatus.contacted
            lead.email_reply_received = True
            
            db.commit()
            print(f"--- [SUCCESS] Email sent and interaction saved for: {lead.email} ---")
        else:
            print(f"--- [ERROR] SMTP failed to send email to {lead.email} ---")
        
    except Exception as e:
        db.rollback()
        print(f"--- [ERROR] Failed to save/send interaction: {e} ---")