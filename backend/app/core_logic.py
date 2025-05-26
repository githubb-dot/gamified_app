# Core game logic for "Alone, I Level Up" App

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from models import User, Stat, Quest, XPEvent, QuestCreate # Assuming models.py is in the same directory or accessible

# --- XP and Stat Engine --- 

XP_PER_STAT_POINT = 100
MAX_STAT_VALUE = 99
MIN_STAT_VALUE = -99

async def adjust_xp_and_stats(user_id: str, quest_reward_xp: int, quest_completed: bool, current_stats: Stat) -> (Stat, int, str):
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
    
    # For simplicity, we'll assume a direct mapping of XP to a general stat pool first
    # and then distribute it or link it to specific stats later if needed.
    # The spec says "Each 100 XP increments a stat by +1; –100 XP decrements by –1."
    # It doesn't specify WHICH stat. For now, let's assume a general pool or apply to a default stat.
    # For MVP, let's assume XP directly influences a hidden "level progress" and stats are affected by specific quest types or user choices (not yet implemented).
    # Re-reading FR-05: "Each 100 XP increments a stat by +1; –100 XP decrements by –1."
    # Re-reading FR-08: "Completing quest adjusts XP and corresponding stat."
    # This implies quests should be linked to stats. This is not in the current Quest model explicitly.
    # For now, let's assume XP is generic and we need a mechanism to decide which stat to update.
    # Let's simplify for MVP: apply change to a *primary* stat or distribute. The spec is a bit vague here.
    # Let's assume for now that the XP gain/loss translates to potential stat points, and these points are then applied.
    # For now, we'll just record XP and update a *generic* stat like 'discipline' as a placeholder.

    # Simplified: Let's say Discipline is the stat affected by all quests for now.
    # This needs refinement based on how quests are tied to specific stats.
    stat_points_change = xp_change // XP_PER_STAT_POINT

    current_stats.discipline = max(MIN_STAT_VALUE, min(MAX_STAT_VALUE, current_stats.discipline + stat_points_change))
    # In a real scenario, we'd update specific stats based on quest type or user allocation.
    
    current_stats.last_updated = datetime.utcnow()

    # Determine title based on new stats
    new_title = determine_user_title(current_stats, False) # Neglect status false for now

    return current_stats, xp_change, new_title

# --- Quest Lifecycle Management --- 

async def complete_quest(quest: Quest, user_stats: Stat) -> (Quest, Stat, int, str):
    """
    Marks a quest as completed and updates XP/stats.
    """
    if quest.status != "pending":
        raise ValueError("Quest is not pending and cannot be completed.")
    
    quest.status = "completed"
    quest.completed_at = datetime.utcnow()
    
    updated_stats, xp_awarded, new_title = await adjust_xp_and_stats(
        user_id=str(quest.user_id), 
        quest_reward_xp=quest.reward_xp, 
        quest_completed=True, 
        current_stats=user_stats
    )
    return quest, updated_stats, xp_awarded, new_title

async def fail_quest(quest: Quest, user_stats: Stat) -> (Quest, Stat, int, str):
    """
    Marks a quest as failed and updates XP/stats.
    """
    if quest.status != "pending":
        raise ValueError("Quest is not pending and cannot be failed.")
        
    quest.status = "failed"
    # No completed_at for failed quests, or use a different field like 'processed_at'
    
    updated_stats, xp_deducted, new_title = await adjust_xp_and_stats(
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

def determine_user_title(stats: Stat, is_neglected: bool, last_quest_completion_time: Optional[datetime] = None, stats_positive_streak_days: int = 0) -> str:
    """
    Determines the user's title based on their stats and activity.
    Refers to Spec FR-06, FR-07, FR-11, Spec 8.3, Appendix B1.
    """
    # FR-11: Title switches to “Level Down” when any stat < 0 OR 72 h inactivity.
    # Spec 8.3: After 72 h with no completed quests, trigger Title change regardless of stats.
    
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
    elif is_neglected: # Fallback if explicit neglect status is passed
        neglected_by_time = True

    if any_stat_negative or neglected_by_time:
        return TITLE_LEVEL_DOWN
    
    # FR-07: Title shall revert to “Level Up” after all stats ≥0 for 7 consecutive days.
    # This implies the current title also matters. If current title is Level Down, then we check this condition.
    # For simplicity in this function, we assume if not Level Down, it's Level Up, 
    # but the actual state transition might need to know the *previous* title.
    # Let's assume if conditions for Level Down are not met, and stats_positive_streak_days >= 7, it's Level Up.
    # This part is tricky as it implies state. The `stats_positive_streak_days` would need to be tracked elsewhere.
    # For now, if not Level Down, it's Level Up.
    # The logic for FR-07 (reverting to Level Up) needs a separate process that tracks the 7-day streak.
    # This function primarily decides if it *should* be Level Down.
    
    return TITLE_LEVEL_UP

# --- Quest Generation (Placeholder - to be expanded based on Spec 8.1) ---

async def generate_daily_quests_for_user(user: User, goals: List[Any]) -> List[QuestCreate]:
    """
    Generates daily quests for a user based on their goals.
    Placeholder - needs to implement logic from Spec 8.1 and FR-02.
    The current main.py uses an AI for this, which could be integrated here.
    """
    quests_to_create = []
    if not goals:
        # Maybe a default generic quest if no goals?
        default_quest_text = "Complete a 15-minute self-reflection session."
        quests_to_create.append(
            QuestCreate(
                text=default_quest_text,
                difficulty=2, # Medium
                reward_xp=20, # (10 + 2*5)
                due_date=datetime.utcnow() + timedelta(days=1) # Due by end of next day
            )
        )
    else:
        for goal in goals:
            # FR-02: App shall generate at least 1 and at most 5 daily quests per goal.
            # Spec 8.1: difficulty = sigmoid((goal_priority × timebox) / user_streak)
            # reward_xp = round (10 + difficulty × 5)
            # This requires more info on goal_priority, timebox, user_streak, and sigmoid function.
            # For now, create one simple quest per goal.
            quests_to_create.append(
                QuestCreate(
                    text=f"Work towards your goal: {goal.description} for 30 minutes.",
                    difficulty=3, # Placeholder
                    reward_xp=25, # Placeholder (10 + 3*5)
                    goal_id=goal.id,
                    due_date=datetime.utcnow() + timedelta(days=1)
                )
            )
    return quests_to_create


