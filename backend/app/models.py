# Pydantic models and SQLAlchemy ORM models for "Alone, I Level Up" App

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime, date
import uuid

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Integer, Text, Enum as SQLAlchemyEnum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID # For PostgreSQL specific UUID type
from sqlalchemy.types import UUID as SQLAlchemy_UUID # Generic UUID type

from database import Base # Import Base from database.py

# --- SQLAlchemy ORM Models ---

class DBUser(Base):
    __tablename__ = "users"

    id = Column(SQLAlchemy_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False) # For storing hashed passwords
    name = Column(String, nullable=True)
    locale = Column(String, default="en_US")
    title = Column(String, default="Alone, I Level Up")
    created_at = Column(DateTime, default=datetime.utcnow)

    goals = relationship("DBGoal", back_populates="owner")
    quests = relationship("DBQuest", back_populates="owner")
    stats = relationship("DBStat", back_populates="owner", uselist=False) # One-to-one
    xp_events = relationship("DBXPEvent", back_populates="owner")
    reports = relationship("DBReport", back_populates="owner")

class DBGoal(Base):
    __tablename__ = "goals"

    id = Column(SQLAlchemy_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(SQLAlchemy_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    description = Column(Text, nullable=False)
    frequency = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("DBUser", back_populates="goals")
    quests = relationship("DBQuest", back_populates="goal")

class DBQuest(Base):
    __tablename__ = "quests"

    id = Column(SQLAlchemy_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(SQLAlchemy_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    goal_id = Column(SQLAlchemy_UUID(as_uuid=True), ForeignKey("goals.id"), nullable=True)
    text = Column(Text, nullable=False)
    difficulty = Column(Integer, default=3)
    reward_xp = Column(Integer, default=10)
    status = Column(String, default="pending") # pending, completed, failed
    due_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    owner = relationship("DBUser", back_populates="quests")
    goal = relationship("DBGoal", back_populates="quests")
    xp_events = relationship("DBXPEvent", back_populates="quest")

class DBStat(Base):
    __tablename__ = "stats"

    id = Column(SQLAlchemy_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(SQLAlchemy_UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False) # Ensure one-to-one via unique
    strength = Column(Integer, default=0)
    intelligence = Column(Integer, default=0)
    discipline = Column(Integer, default=0)
    focus = Column(Integer, default=0)
    communication = Column(Integer, default=0)
    adaptability = Column(Integer, default=0)
    last_updated = Column(DateTime, default=datetime.utcnow)

    owner = relationship("DBUser", back_populates="stats")

class DBXPEvent(Base):
    __tablename__ = "xp_events"

    id = Column(SQLAlchemy_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(SQLAlchemy_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    quest_id = Column(SQLAlchemy_UUID(as_uuid=True), ForeignKey("quests.id"), nullable=True)
    delta_xp = Column(Integer, nullable=False)
    reason = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    owner = relationship("DBUser", back_populates="xp_events")
    quest = relationship("DBQuest", back_populates="xp_events")

class DBReport(Base):
    __tablename__ = "reports"

    id = Column(SQLAlchemy_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(SQLAlchemy_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    week_start_date = Column(DateTime, nullable=False) # Changed to DateTime for consistency, can store date part
    content_json = Column(Text, nullable=True) # Storing as Text, assuming JSON string
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("DBUser", back_populates="reports")


# --- Pydantic Schemas (for API request/response validation) ---

class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    locale: Optional[str] = "en_US"

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: uuid.UUID
    title: str = "Alone, I Level Up"
    created_at: datetime

    class Config:
        from_attributes = True # Changed from orm_mode

class GoalBase(BaseModel):
    description: str
    frequency: Optional[str] = None
    is_active: bool = True

class GoalCreate(GoalBase):
    pass

class Goal(GoalBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True

class QuestBase(BaseModel):
    text: str
    difficulty: int = Field(default=3, ge=1, le=5)
    reward_xp: int = Field(default=10, gt=0)
    status: str = "pending"

class QuestCreate(QuestBase):
    goal_id: Optional[uuid.UUID] = None
    due_date: datetime

class Quest(QuestBase):
    id: uuid.UUID
    user_id: uuid.UUID
    goal_id: Optional[uuid.UUID] = None
    due_date: datetime
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class StatBase(BaseModel):
    strength: int = Field(default=0, ge=-99, le=99)
    intelligence: int = Field(default=0, ge=-99, le=99)
    discipline: int = Field(default=0, ge=-99, le=99)
    focus: int = Field(default=0, ge=-99, le=99)
    communication: int = Field(default=0, ge=-99, le=99)
    adaptability: int = Field(default=0, ge=-99, le=99)

class StatCreate(StatBase):
    pass

class Stat(StatBase):
    id: uuid.UUID
    user_id: uuid.UUID
    last_updated: datetime

    class Config:
        from_attributes = True

class XPEventBase(BaseModel):
    delta_xp: int
    reason: Optional[str] = None

class XPEventCreate(XPEventBase):
    quest_id: Optional[uuid.UUID] = None

class XPEvent(XPEventBase):
    id: uuid.UUID
    user_id: uuid.UUID
    quest_id: Optional[uuid.UUID] = None
    timestamp: datetime

    class Config:
        from_attributes = True

class ReportBase(BaseModel):
    week_start_date: date # Pydantic can use date type here
    content_json: dict

class ReportCreate(ReportBase):
    pass

class Report(ReportBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True

# For API responses that might combine data
class DashboardInfo(BaseModel):
    title: str
    stats: Stat # This should be the Pydantic Stat model
    active_quests: List[Quest] # This should be a list of Pydantic Quest models

    class Config:
        from_attributes = True

