from sqlalchemy import Column, Integer, ForeignKey, DateTime, Enum, String, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
from database import Base

class Userrole(enum.Enum):
    admin = "admin"
    sales = "sales"
    meeting_manager = "meeting_manager"

class LeadStatus(enum.Enum):
    new = "new"  
    contacted = "contacted"
    qualified = "qualified"
    closed = "closed"

class MeetingStatus(enum.Enum):
    scheduled = "scheduled"
    complete = "complete"
    cancelled = "cancelled"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(Enum(Userrole), nullable=False)
    
    otp = Column(String, nullable=True)
    otp_expiry = Column(DateTime, nullable=True)
    is_verified = Column(Boolean, default=False)

    leads = relationship("Lead", back_populates="assigned_user")
    meetings = relationship("Meeting", back_populates="manager")

class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, index=True) 
    phone = Column(String)
    status = Column(Enum(LeadStatus), default=LeadStatus.new)
    assigned_to = Column(Integer, ForeignKey("users.id"))
    service_type = Column(String, default="AI-Services")
    budget = Column(Integer, nullable=True)
    email_sent = Column(Boolean, default=False)
    email_reply_received = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_email_sent_at = Column(DateTime, nullable=True)

    assigned_user = relationship("User", back_populates="leads")
    notes = relationship("LeadNote", back_populates="lead", cascade="all, delete-orphan")
    meetings = relationship("Meeting", back_populates="lead", cascade="all, delete-orphan")

class LeadNote(Base):
    __tablename__ = "lead_notes"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"))
    
    note = Column(Text, nullable=False) 
    sender = Column(String, default="system", nullable=True) 
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=True)

    lead = relationship("Lead", back_populates="notes")

class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"))
    manager_id = Column(Integer, ForeignKey("users.id"))
    scheduled_time = Column(DateTime, nullable=False)
    status = Column(Enum(MeetingStatus), default=MeetingStatus.scheduled)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    lead = relationship("Lead", back_populates="meetings")
    manager = relationship("User", back_populates="meetings")