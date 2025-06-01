# backend/app/routers/quests.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from ..database import get_db
from .. import models, schemas, core_logic

router = APIRouter(prefix="/quests", tags=["quests"])

# --- helpers ---------------------------------------------------------------

def get_quest_or_404(quest_id: UUID, db: Session) -> models.DBQuest:
    quest = db.query(models.DBQuest).filter_by(id=quest_id).first()
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")
    return quest

# --- endpoints -------------------------------------------------------------

@router.post(
    "/", response_model=schemas.QuestOut, status_code=status.HTTP_201_CREATED
)
def create_quest(q: schemas.QuestCreate, db: Session = Depends(get_db)):
    db_quest = models.DBQuest(
        description=q.description,
        reward_xp=q.reward_xp,
        status="pending",
        user_id="demo-user",      # 🚩 TODO: replace with real auth
    )
    db.add(db_quest)
    db.commit()
    db.refresh(db_quest)
    return db_quest


@router.patch("/{quest_id}/complete", response_model=schemas.QuestOut)
def complete(quest_id: UUID, db: Session = Depends(get_db)):
    db_quest = get_quest_or_404(quest_id, db)
    if db_quest.status != "pending":
        raise HTTPException(400, "Quest already processed")

    # load stats row for the user
    stats = (
        db.query(models.DBStat)
        .filter_by(user_id=db_quest.user_id)
        .with_for_update()
        .first()
    )

    # domain logic
    updated_q, updated_stats, xp, new_title = core_logic.complete_quest(
        db_quest, stats
    )

    # persist
    db.add_all([updated_q, updated_stats])
    db.commit()
    return updated_q


@router.patch("/{quest_id}/fail", response_model=schemas.QuestOut)
def fail(quest_id: UUID, db: Session = Depends(get_db)):
    db_quest = get_quest_or_404(quest_id, db)

    stats = (
        db.query(models.DBStat)
        .filter_by(user_id=db_quest.user_id)
        .with_for_update()
        .first()
    )

    updated_q, updated_stats, xp, new_title = core_logic.fail_quest(
        db_quest, stats
    )

    db.add_all([updated_q, updated_stats])
    db.commit()
    return updated_q
