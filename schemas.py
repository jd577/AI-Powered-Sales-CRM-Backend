from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import datetime
from typing import Optional, List
from models import Userrole, LeadStatus, MeetingStatus


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: Userrole

class VerifyOTP(BaseModel):
    email: EmailStr
    otp: str

class ResendOTP(BaseModel):
    email: EmailStr

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: Userrole
    is_verified: bool
    model_config = ConfigDict(from_attributes=True)


class LeadCreate(BaseModel):
    name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    service_type: str = "AI services"
    budget: Optional[int] = None

class LeadUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    status: Optional[LeadStatus] = None
    service_type: Optional[str] = None
    budget: Optional[int] = None
    email_reply_received: Optional[bool] = None

class LeadResponse(BaseModel):
    id: int
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    status: LeadStatus
    assigned_to: Optional[int] = None
    service_type: Optional[str] = None
    budget: Optional[int] = None
    email_sent: bool = False
    email_reply_received: bool = False
    last_email_sent_at: Optional[datetime] = None
    created_at: Optional[datetime] = None 
    model_config = ConfigDict(from_attributes=True)

class LeadNoteCreate(BaseModel):
    note: str
    
    sender: str = "sales" 

class LeadNoteResponse(BaseModel):
    id: int
    lead_id: int
    note: str
    sender: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class AIWorkflowResponse(BaseModel):
    """Schema for the LangGraph output used in the UI"""
    note: str
    sender: str = "ai"
    status: str = "success"


class MeetingCreate(BaseModel):
    lead_id: int
    scheduled_time: datetime

class MeetingUpdate(BaseModel):
    scheduled_time: Optional[datetime] = None
    status: Optional[MeetingStatus] = None

class MeetingResponse(BaseModel):
    id: int
    lead_id: int
    manager_id: Optional[int] = None
    scheduled_time: datetime
    status: MeetingStatus
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class AssignLead(BaseModel):
    user_id: int