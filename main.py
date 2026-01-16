from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta, timezone
import random
import os
import threading
from contextlib import asynccontextmanager
from dotenv import load_dotenv

import models
import schemas
from database import engine, get_db
from auth import hash_password, verify_password, create_access_token, get_current_user
from email_service import send_otp_email, send_ai_response_email
from langgraph_workflow_service import process_lead_reply 
from listener import start_email_monitor

load_dotenv()
models.Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    email_thread = threading.Thread(target=start_email_monitor, daemon=True)
    email_thread.start()
    yield

app = FastAPI(title="PROFESSIONAL SALES CRM API", version="1.3.0", lifespan=lifespan)

def generate_otp():
    return str(random.randint(100000, 999999))

@app.get("/")
def root():
    return {"message": "Welcome to SALES CRM API", "status": "Active"}

@app.post("/register", status_code=status.HTTP_201_CREATED)
def register(user_data: schemas.UserCreate, db: Session = Depends(get_db)): 
    if db.query(models.User).filter(models.User.email == user_data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    otp = generate_otp()
    new_user = models.User(
        name=user_data.name,
        email=user_data.email,
        password=hash_password(user_data.password),
        role=user_data.role,
        otp=otp,
        otp_expiry=datetime.now(timezone.utc) + timedelta(minutes=30),
        is_verified=False
    )
    db.add(new_user)
    db.commit() 
    send_otp_email(user_data.email, user_data.name, otp)
    return {"message": "Check email for OTP verification."}

@app.post("/verify-otp")
def verify_otp(verify_data: schemas.VerifyOTP, db: Session = Depends(get_db)): 
    user = db.query(models.User).filter(models.User.email == verify_data.email).first()
    if not user or user.is_verified or user.otp != verify_data.otp:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    
    user.is_verified = True
    user.otp = None
    db.commit()
    return {"message": "Verified successfully!"}

@app.post("/login", response_model=schemas.TokenResponse)
def login(login_data: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == login_data.email).first()
    if not user or not verify_password(login_data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Please verify email first")
    
    token = create_access_token(data={"user_id": user.id})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/me", response_model=schemas.UserResponse)
def get_me(current_user: models.User = Depends(get_current_user)):
    return current_user

@app.post("/leads", response_model=schemas.LeadResponse, status_code=201)
def create_lead(lead_data: schemas.LeadCreate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    new_lead = models.Lead(**lead_data.model_dump(), status=models.LeadStatus.new)
    db.add(new_lead)
    db.commit()
    db.refresh(new_lead)
    
    if new_lead.budget and new_lead.budget >= 5000:
        lead_info = {
            "name": new_lead.name,
            "budget": new_lead.budget,
            "service_type": new_lead.service_type,
            "last_message": "New Lead Inquiry"
        }
        
        ai_text = process_lead_reply(lead_info, [])
        email_sent = send_ai_response_email(new_lead.email, new_lead.name, ai_text)
        
        if email_sent:
            ai_note = models.LeadNote(lead_id=new_lead.id, note=ai_text, sender="ai")
            db.add(ai_note)
            new_lead.email_sent = True
            new_lead.last_email_sent_at = datetime.now(timezone.utc)
            new_lead.status = models.LeadStatus.contacted
            db.commit()
            
    return new_lead

@app.get("/leads", response_model=List[schemas.LeadResponse])
def get_leads(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role in [models.Userrole.admin, models.Userrole.meeting_manager]:
        return db.query(models.Lead).all()
    return db.query(models.Lead).filter(models.Lead.assigned_to == current_user.id).all()

@app.post("/leads/{lead_id}/notes", status_code=201)
def add_note_and_ai_reply(lead_id: int, note_data: schemas.LeadNoteCreate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    new_note = models.LeadNote(lead_id=lead_id, note=note_data.note, sender=note_data.sender)
    db.add(new_note)
    db.commit()

    ai_reply = None
    if note_data.sender == "lead":
        history_objs = db.query(models.LeadNote).filter(models.LeadNote.lead_id == lead_id).order_by(models.LeadNote.created_at.desc()).limit(10).all()
        history = [{"sender": n.sender, "message": n.note} for n in reversed(history_objs)]
        
        lead_info = {
            "name": lead.name, 
            "budget": lead.budget or 0, 
            "service_type": lead.service_type, 
            "last_message": note_data.note
        }
        
        ai_text = process_lead_reply(lead_info, history)
        ai_note = models.LeadNote(lead_id=lead_id, note=ai_text, sender="ai")
        db.add(ai_note)
        
        send_ai_response_email(lead.email, lead.name, ai_text)
        
        lead.status = models.LeadStatus.contacted
        db.commit()
        ai_reply = ai_text
        
    return {"status": "Note saved", "ai_response": ai_reply}

@app.get("/leads/{lead_id}/notes", response_model=List[schemas.LeadNoteResponse])
def get_lead_notes(lead_id: int, db: Session = Depends(get_db)):
    return db.query(models.LeadNote).filter(models.LeadNote.lead_id == lead_id).all()

@app.post("/meetings", response_model=schemas.MeetingResponse, status_code=201)
def create_meeting(meeting_data: schemas.MeetingCreate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role not in [models.Userrole.admin, models.Userrole.meeting_manager]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    new_meeting = models.Meeting(**meeting_data.model_dump(), manager_id=current_user.id, status=models.MeetingStatus.scheduled)
    db.add(new_meeting)
    db.commit()
    db.refresh(new_meeting)
    return new_meeting

@app.get("/meetings", response_model=List[schemas.MeetingResponse])
def get_meetings(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role in [models.Userrole.admin, models.Userrole.meeting_manager]:
        return db.query(models.Meeting).all()
    return db.query(models.Meeting).join(models.Lead).filter(models.Lead.assigned_to == current_user.id).all()

@app.put("/meetings/{meeting_id}", response_model=schemas.MeetingResponse)
def update_meeting(meeting_id: int, meeting_data: schemas.MeetingUpdate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    meeting = db.query(models.Meeting).filter(models.Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    if meeting_data.status: 
        meeting.status = meeting_data.status
    db.commit()
    db.refresh(meeting)
    return meeting

@app.get("/users", response_model=List[schemas.UserResponse])
def get_users(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != models.Userrole.admin: 
        raise HTTPException(status_code=403)
    return db.query(models.User).all()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)