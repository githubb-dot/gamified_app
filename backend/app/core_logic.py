# backend/app/core_logic.py

from datetime import datetime, timedelta
from typing import List, Optional

from models import User, Stat, Quest, XPEvent, QuestCreate  # Models are in models.py

# --- XP and Stat Engine ---

XP_PER_STAT_POINT = 100
MAX_STAT_VALUE = 99
MIN_STAT_VALUE = -99

def adjust_xp_and_stats(
    user_id: str,
    quest_reward_xp: int,
    quest_completed: bool,
    current_stats: Stat
) -> (Stat, int, str):
    """
    Adjusts user XP and stats based on quest completion or failure.

    Args:
        user_id (str): The ID of the user.
        quest_reward_xp (int): The base XP reward for the quest.
        quest_completed (bool): True if the quest was completed, False if failed.
        current_stats (Stat): The current Stat object for the user.

    Returns:
        tuple: (updated_stat_object, xp_change_applied, new_title)
    """
    xp_change = quest_reward_xp if quest_completed else -quest_reward_xp

    # Simplified: apply all XP changes to 'discipline' for now.
    stat_points_change = xp_change // XP_PER_STAT_POINT
    current_stats.discipline = max(
        MIN_STAT_VALUE,
        min(MAX_STAT_VALUE, current_stats.discipline + stat_points_change)
    )
    current_stats.last_updated = datetime.utcnow()

    # Determine title based on new stats
    new_title = determine_user_title(current_stats, False)
    return current_stats, xp_change, new_title


def complete_quest(
    quest: Quest,
    user_stats: Stat
) -> (Quest, Stat, int, str):
    """
    Marks a quest as completed and updates XP/stats.
    """
    if quest.status != "pending":
        raise ValueError("Quest is not pending and cannot be completed.")

    quest.status = "completed"
    quest.completed_at = datetime.utcnow()

    updated_stats, xp_awarded, new_title = adjust_xp_and_stats(
        user_id=str(quest.user_id),
        quest_reward_xp=quest.reward_xp,
        quest_completed=True,
        current_stats=user_stats
    )
    return quest, updated_stats, xp_awarded, new_title


def fail_quest(
    quest: Quest,
    user_stats: Stat
) -> (Quest, Stat, int, str):
    """
    Marks a quest as failed and updates XP/stats.
    """
    if quest.status != "pending":
        raise ValueError("Quest is not pending and cannot be failed.")

    quest.status = "failed"
    # We’re not setting a 'completed_at' for failed quests.
    updated_stats, xp_deducted, new_title = adjust_xp_and_stats(
        user_id=str(quest.user_id),
        quest_reward_xp=quest.reward_xp,
        quest_completed=False,
        current_stats=user_stats
    )
    return quest, updated_stats, xp_deducted, new_title


# --- Title Logic Engine ---

TITLE_LEVEL_UP = "Alone, I Level Up"
TITLE_LEVEL_DOWN = "Alone, I Level Down"
NEGLECT_HOURS_THRESHOLD = 72

def determine_user_title(
    stats: Stat,
    is_neglected: bool,
    last_quest_completion_time: Optional[datetime] = None,
    stats_positive_streak_days: int = 0
) -> str:
    """
    Determines the user's title based on their stats and activity.
    """
    any_stat_negative = any([
        stats.strength < 0,
        stats.intelligence < 0,
        stats.discipline < 0,
        stats.focus < 0,
        stats.communication < 0,
        stats.adaptability < 0
    ])

    neglected_by_time = False
    if last_quest_completion_time:
        if datetime.utcnow() - last_quest_completion_time > timedelta(hours=NEGLECT_HOURS_THRESHOLD):
            neglected_by_time = True
    elif is_neglected:
        neglected_by_time = True

    if any_stat_negative or neglected_by_time:
        return TITLE_LEVEL_DOWN

    # FR-07: Revert to “Level Up” if all stats ≥ 0 for 7 days.
    # (Tracking of the 7-day streak happens elsewhere; default to Level Up.)
    return TITLE_LEVEL_UP


# --- Quest Generation (Placeholder) ---

def generate_daily_quests_for_user(
    user: User,
    goals: List[User]  # or whatever type goal is
) -> List[QuestCreate]:
    """
    Generates daily quests for a user based on their goals.
    Placeholder – this can be called from an async endpoint if needed.
    """
    quests_to_create: List[QuestCreate] = []
    if not goals:
        default_quest_text = "Complete a 15-minute self-reflection session."
        quests_to_create.append(
            QuestCreate(
                text=default_quest_text,
                difficulty=2,  # Medium
                reward_xp=20,  # (10 + 2*5)
                due_date=datetime.utcnow() + timedelta(days=1)
            )
        )
    else:
        for goal in goals:
            quests_to_create.append(
                QuestCreate(
                    text=f"Work towards your goal: {goal.description} for 30 minutes.",
                    difficulty=3,     # Placeholder
                    reward_xp=25,     # Placeholder (10 + 3*5)
                    goal_id=goal.id,  # If your QuestCreate model has a goal_id field
                    due_date=datetime.utcnow() + timedelta(days=1)
                )
            )
    return quests_to_create
