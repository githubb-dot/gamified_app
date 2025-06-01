# backend/app/schemas.py
from __future__ import annotations
from datetime import datetime, date
from uuid import UUID
from typing import Literal, Optional

from pydantic import BaseModel, Field

class QuestCreate(BaseModel):
    description: str = Field(..., min_length=5, max_length=240)
    reward_xp: int = Field(..., ge=10, le=1_000)

class QuestOut(BaseModel):
    id: UUID
    description: str
    reward_xp: int
    status: Literal["pending", "completed", "failed"]
    created_at: datetime
    due_date: Optional[date]

    class Config:
        from_attributes = True      # Pydantic v2 ⇄ SQLAlchemy

