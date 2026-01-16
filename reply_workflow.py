from database import SessionLocal
import models
from langgraph_workflow_service import process_lead_reply
from email_service import send_ai_response_email

def handle_incoming_reply(lead_id: int, lead_name: str, lead_email: str, message_body: str):
    db = SessionLocal()
    try:
        lead_reply_note = models.LeadNote(
            lead_id=lead_id,
            note=message_body,
            sender="lead"
        )
        db.add(lead_reply_note)
        db.flush()  

        history_objs = db.query(models.LeadNote).filter(
            models.LeadNote.lead_id == lead_id
        ).order_by(models.LeadNote.created_at.desc()).limit(10).all()
        
        history = [
            {"sender": n.sender, "message": n.note} 
            for n in reversed(history_objs)
        ]

        lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
        
        lead_data = {
            "name": lead_name,
            "budget": lead.budget if lead else 0,
            "service_type": lead.service_type if lead else "AI Services",
            "last_message": message_body
        }
        
        ai_reply_text = process_lead_reply(lead_data, history)

        email_success = send_ai_response_email(
            email=lead_email,
            lead_name=lead_name,
            ai_message=ai_reply_text
        )

        if email_success:
            ai_note = models.LeadNote(
                lead_id=lead_id,
                note=ai_reply_text,
                sender="ai"
            )
            db.add(ai_note)
            
            if lead:
                lead.status = models.LeadStatus.contacted
                lead.email_reply_received = True
            
            db.commit()
            print(f"--- [SUCCESS] AI Reply sent and saved for {lead_email} ---")
        else:
            print(f"--- [WARNING] AI reply generated but email failed to send to {lead_email} ---")

    except Exception as e:
        db.rollback()
        print(f"--- [ERROR] Reply Workflow Failed: {e} ---")
    finally:
        db.close()