from flask import Blueprint, request, jsonify, session
from src.models.user import db, User, Stat, Goal, Quest, XPEvent, UserLevel, Notification, hash_password, check_password
from datetime import datetime, timedelta
import uuid
import json
import requests
import random
import math

user_bp = Blueprint('user', __name__)

# Gemini AI API configuration
GEMINI_API_KEY = "AIzaSyCGenom5_GzoDLBZq-_KujTEodisBWR6OI"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
GEMINI_MODEL = "gemini-2.0-flash"

# Authentication routes
@user_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    # Check if required fields are present
    if not all(k in data for k in ['username', 'email', 'password']):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Check if user already exists
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 400
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already exists'}), 400
    
    # Create new user with SHA-256 hashed password
    hashed_password = hash_password(data['password'])
    new_user = User(
        id=str(uuid.uuid4()),
        username=data['username'],
        email=data['email'],
        password=hashed_password,
        title="Alone, I Level Up",
        created_at=datetime.utcnow(),
        last_active=datetime.utcnow()
    )
    
    # Create initial stats for user
    new_stats = Stat(
        id=str(uuid.uuid4()),
        user_id=new_user.id,
        strength=0,
        intelligence=0,
        discipline=0,
        focus=0,
        communication=0,
        adaptability=0,
        last_updated=datetime.utcnow()
    )
    
    # Create initial level for user
    new_level = UserLevel(
        id=str(uuid.uuid4()),
        user_id=new_user.id,
        level=1,
        total_xp=0,
        available_points=0,
        last_updated=datetime.utcnow()
    )
    
    # Create initial improvement goals if provided
    if 'improvement_goals' in data and isinstance(data['improvement_goals'], list):
        for goal_text in data['improvement_goals']:
            category = map_goal_to_category(goal_text)
            new_goal = Goal(
                id=str(uuid.uuid4()),
                user_id=new_user.id,
                description=goal_text,
                category=category,
                is_active=True,
                created_at=datetime.utcnow()
            )
            db.session.add(new_goal)
            
            # Generate initial quest for this goal
            try:
                quest_data = generate_quest_with_gemini(goal_text)
                if quest_data:
                    # Set due date to end of today
                    today = datetime.utcnow().date()
                    due_date = datetime.combine(today, datetime.max.time())
                    
                    new_quest = Quest(
                        id=str(uuid.uuid4()),
                        user_id=new_user.id,
                        goal_id=new_goal.id,
                        text=quest_data['text'],
                        difficulty=quest_data['difficulty'],
                        reward_xp=quest_data['reward_xp'],
                        status='pending',
                        due_date=due_date,
                        created_at=datetime.utcnow(),
                        is_optional=False,
                        primary_stat=quest_data['primary_stat']
                    )
                    db.session.add(new_quest)
                    
                    # Create notification for new quest
                    new_notification = Notification(
                        id=str(uuid.uuid4()),
                        user_id=new_user.id,
                        quest_id=new_quest.id,
                        title="New Quest Available!",
                        message=f"A new quest has been generated for your goal: {goal_text}",
                        type="info",
                        is_read=False,
                        created_at=datetime.utcnow()
                    )
                    db.session.add(new_notification)
            except Exception as e:
                print(f"Error generating quest: {str(e)}")
    
    db.session.add(new_user)
    db.session.add(new_stats)
    db.session.add(new_level)
    db.session.commit()
    
    # Create session
    session['user_id'] = new_user.id
    
    return jsonify({
        'message': 'User registered successfully',
        'user': {
            'id': new_user.id,
            'username': new_user.username,
            'email': new_user.email,
            'title': new_user.title
        }
    }), 201

@user_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    # Check if required fields are present
    if not all(k in data for k in ['username', 'password']):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Find user
    user = User.query.filter_by(username=data['username']).first()
    
    # Check if user exists and password is correct
    if not user or not check_password(user.password, data['password']):
        return jsonify({'error': 'Invalid username or password'}), 401
    
    # Update last active timestamp
    user.last_active = datetime.utcnow()
    db.session.commit()
    
    # Check title status on login
    check_title_status(user.id)
    
    # Generate quests if needed
    generate_quests_if_needed(user.id)
    
    # Generate random optional quest (25% chance on login)
    if random.random() < 0.25:
        generate_optional_quest(user.id)
    
    # Create session
    session['user_id'] = user.id
    
    return jsonify({
        'message': 'Login successful',
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'title': user.title
        }
    }), 200

@user_bp.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({'message': 'Logout successful'}), 200

@user_bp.route('/me', methods=['GET'])
def get_current_user():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'title': user.title
        }
    }), 200

# Stats routes
@user_bp.route('/stats', methods=['GET'])
def get_stats():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    stats = Stat.query.filter_by(user_id=user_id).first()
    if not stats:
        return jsonify({'error': 'Stats not found'}), 404
    
    return jsonify({
        'stats': {
            'strength': stats.strength,
            'intelligence': stats.intelligence,
            'discipline': stats.discipline,
            'focus': stats.focus,
            'communication': stats.communication,
            'adaptability': stats.adaptability,
            'last_updated': stats.last_updated.isoformat()
        }
    }), 200

# Level routes
@user_bp.route('/level', methods=['GET'])
def get_level():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_level = UserLevel.query.filter_by(user_id=user_id).first()
    if not user_level:
        return jsonify({'error': 'Level not found'}), 404
    
    return jsonify({
        'level': {
            'level': user_level.level,
            'total_xp': user_level.total_xp,
            'available_points': user_level.available_points,
            'next_level_xp': (user_level.level * 1000),
            'progress_percent': min(100, (user_level.total_xp % 1000) / 10)
        }
    }), 200

@user_bp.route('/level/allocate', methods=['POST'])
def allocate_points():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.get_json()
    
    # Check if required fields are present
    if not all(k in data for k in ['stat', 'points']):
        return jsonify({'error': 'Missing required fields'}), 400
    
    stat_name = data['stat']
    points = int(data['points'])
    
    if points <= 0:
        return jsonify({'error': 'Points must be positive'}), 400
    
    # Validate stat name
    valid_stats = ['strength', 'intelligence', 'discipline', 'focus', 'communication', 'adaptability']
    if stat_name not in valid_stats:
        return jsonify({'error': 'Invalid stat name'}), 400
    
    # Get user level and stats
    user_level = UserLevel.query.filter_by(user_id=user_id).first()
    stats = Stat.query.filter_by(user_id=user_id).first()
    
    if not user_level or not stats:
        return jsonify({'error': 'User level or stats not found'}), 404
    
    # Check if user has enough points
    if user_level.available_points < points:
        return jsonify({'error': 'Not enough available points'}), 400
    
    # Update stat and available points
    setattr(stats, stat_name, getattr(stats, stat_name) + points)
    user_level.available_points -= points
    stats.last_updated = datetime.utcnow()
    user_level.last_updated = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({
        'message': f'Successfully allocated {points} points to {stat_name}',
        'stats': {
            'strength': stats.strength,
            'intelligence': stats.intelligence,
            'discipline': stats.discipline,
            'focus': stats.focus,
            'communication': stats.communication,
            'adaptability': stats.adaptability
        },
        'available_points': user_level.available_points
    }), 200

# Goals routes
@user_bp.route('/goals', methods=['GET'])
def get_goals():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    goals = Goal.query.filter_by(user_id=user_id, is_active=True).all()
    
    return jsonify({
        'goals': [{
            'id': goal.id,
            'description': goal.description,
            'category': goal.category,
            'created_at': goal.created_at.isoformat()
        } for goal in goals]
    }), 200

@user_bp.route('/goals', methods=['POST'])
def create_goal():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.get_json()
    
    # Check if required fields are present
    if 'description' not in data:
        return jsonify({'error': 'Missing description field'}), 400
    
    # Map goal to category
    category = data.get('category')
    if not category:
        category = map_goal_to_category(data['description'])
    
    # Create new goal
    new_goal = Goal(
        id=str(uuid.uuid4()),
        user_id=user_id,
        description=data['description'],
        category=category,
        is_active=True,
        created_at=datetime.utcnow()
    )
    
    db.session.add(new_goal)
    db.session.commit()
    
    # Generate a quest for this goal
    try:
        quest_data = generate_quest_with_gemini(data['description'])
        if quest_data:
            # Set due date to end of today
            today = datetime.utcnow().date()
            due_date = datetime.combine(today, datetime.max.time())
            
            new_quest = Quest(
                id=str(uuid.uuid4()),
                user_id=user_id,
                goal_id=new_goal.id,
                text=quest_data['text'],
                difficulty=quest_data['difficulty'],
                reward_xp=quest_data['reward_xp'],
                status='pending',
                due_date=due_date,
                created_at=datetime.utcnow(),
                is_optional=False,
                primary_stat=quest_data['primary_stat']
            )
            db.session.add(new_quest)
            
            # Create notification for new quest
            new_notification = Notification(
                id=str(uuid.uuid4()),
                user_id=user_id,
                quest_id=new_quest.id,
                title="New Quest Available!",
                message=f"A new quest has been generated for your goal: {data['description']}",
                type="info",
                is_read=False,
                created_at=datetime.utcnow()
            )
            db.session.add(new_notification)
            db.session.commit()
    except Exception as e:
        print(f"Error generating quest: {str(e)}")
    
    return jsonify({
        'message': 'Goal created successfully',
        'goal': {
            'id': new_goal.id,
            'description': new_goal.description,
            'category': new_goal.category,
            'created_at': new_goal.created_at.isoformat()
        }
    }), 201

@user_bp.route('/goals/<goal_id>', methods=['DELETE'])
def delete_goal(goal_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    goal = Goal.query.filter_by(id=goal_id, user_id=user_id).first()
    if not goal:
        return jsonify({'error': 'Goal not found'}), 404
    
    # Soft delete by setting is_active to False
    goal.is_active = False
    db.session.commit()
    
    return jsonify({'message': 'Goal deleted successfully'}), 200

# Quests routes
@user_bp.route('/quests', methods=['GET'])
def get_quests():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    status = request.args.get('status', 'pending')
    is_optional = request.args.get('optional', None)
    
    query = Quest.query.filter_by(user_id=user_id, status=status)
    
    if is_optional is not None:
        is_optional = is_optional.lower() == 'true'
        query = query.filter_by(is_optional=is_optional)
    
    quests = query.all()
    
    return jsonify({
        'quests': [{
            'id': quest.id,
            'text': quest.text,
            'difficulty': quest.difficulty,
            'reward_xp': quest.reward_xp,
            'status': quest.status,
            'due_date': quest.due_date.isoformat(),
            'created_at': quest.created_at.isoformat(),
            'completed_at': quest.completed_at.isoformat() if quest.completed_at else None,
            'is_optional': quest.is_optional,
            'expiration_time': quest.expiration_time.isoformat() if quest.expiration_time else None,
            'primary_stat': quest.primary_stat
        } for quest in quests]
    }), 200

@user_bp.route('/quests/<quest_id>/complete', methods=['POST'])
def complete_quest(quest_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    quest = Quest.query.filter_by(id=quest_id, user_id=user_id).first()
    if not quest:
        return jsonify({'error': 'Quest not found'}), 404
    
    if quest.status != 'pending':
        return jsonify({'error': 'Quest already processed'}), 400
    
    # Check if optional quest has expired
    if quest.is_optional and quest.expiration_time and quest.expiration_time < datetime.utcnow():
        return jsonify({'error': 'Quest has expired'}), 400
    
    # Mark quest as completed
    quest.status = 'completed'
    quest.completed_at = datetime.utcnow()
    
    # Calculate XP gain
    xp_gain = quest.reward_xp
    
    # Create XP event
    xp_event = XPEvent(
        id=str(uuid.uuid4()),
        user_id=user_id,
        quest_id=quest.id,
        delta_xp=xp_gain,
        reason='Quest completion',
        timestamp=datetime.utcnow()
    )
    
    # Update user stats based on quest category
    stats = Stat.query.filter_by(user_id=user_id).first()
    
    # Determine which stat to boost based on primary_stat
    stat_type = quest.primary_stat if quest.primary_stat else 'discipline'
    
    # Apply stat change (100 XP = 1 stat point)
    stat_change = xp_gain / 100
    
    if stat_type == 'strength':
        stats.strength += stat_change
    elif stat_type == 'intelligence':
        stats.intelligence += stat_change
    elif stat_type == 'discipline':
        stats.discipline += stat_change
    elif stat_type == 'focus':
        stats.focus += stat_change
    elif stat_type == 'communication':
        stats.communication += stat_change
    elif stat_type == 'adaptability':
        stats.adaptability += stat_change
    
    stats.last_updated = datetime.utcnow()
    
    # Update user's last active timestamp
    user = User.query.get(user_id)
    user.last_active = datetime.utcnow()
    
    # Update user level and XP
    user_level = UserLevel.query.filter_by(user_id=user_id).first()
    user_level.total_xp += xp_gain
    
    # Check if user leveled up
    old_level = user_level.level
    new_level = 1 + math.floor(user_level.total_xp / 1000)
    
    if new_level > old_level:
        # Level up! Grant attribute points
        level_diff = new_level - old_level
        points_gained = level_diff * 3
        user_level.level = new_level
        user_level.available_points += points_gained
        
        # Create level up notification
        level_notification = Notification(
            id=str(uuid.uuid4()),
            user_id=user_id,
            quest_id=None,
            title="LEVEL UP!",
            message=f"You have reached level {new_level}! You gained {points_gained} attribute points to allocate.",
            type="success",
            is_read=False,
            created_at=datetime.utcnow()
        )
        db.session.add(level_notification)
    
    user_level.last_updated = datetime.utcnow()
    
    # Check if title needs to be updated
    if user.title == "Alone, I Level Down":
        # Check if all stats are non-negative
        if all([
            stats.strength >= 0,
            stats.intelligence >= 0,
            stats.discipline >= 0,
            stats.focus >= 0,
            stats.communication >= 0,
            stats.adaptability >= 0
        ]):
            user.title = "Alone, I Level Up"
    
    db.session.add(xp_event)
    db.session.commit()
    
    # Create completion notification
    completion_notification = Notification(
        id=str(uuid.uuid4()),
        user_id=user_id,
        quest_id=quest.id,
        title="Quest Completed!",
        message=f"You gained {xp_gain} XP and increased your {stat_type} by {stat_change:.2f}!",
        type="success",
        is_read=False,
        created_at=datetime.utcnow()
    )
    db.session.add(completion_notification)
    db.session.commit()
    
    return jsonify({
        'message': 'Quest completed successfully',
        'xp_gained': xp_gain,
        'stat_increased': stat_type,
        'stat_change': stat_change,
        'level_up': new_level > old_level,
        'new_level': new_level if new_level > old_level else None,
        'points_gained': points_gained if new_level > old_level else 0,
        'quest': {
            'id': quest.id,
            'text': quest.text,
            'status': quest.status,
            'completed_at': quest.completed_at.isoformat()
        }
    }), 200

@user_bp.route('/quests/<quest_id>/fail', methods=['POST'])
def fail_quest(quest_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    quest = Quest.query.filter_by(id=quest_id, user_id=user_id).first()
    if not quest:
        return jsonify({'error': 'Quest not found'}), 404
    
    if quest.status != 'pending':
        return jsonify({'error': 'Quest already processed'}), 400
    
    # Mark quest as failed
    quest.status = 'failed'
    quest.completed_at = datetime.utcnow()
    
    # Calculate XP loss (negative value)
    xp_loss = -quest.reward_xp
    
    # Create XP event
    xp_event = XPEvent(
        id=str(uuid.uuid4()),
        user_id=user_id,
        quest_id=quest.id,
        delta_xp=xp_loss,
        reason='Quest failure',
        timestamp=datetime.utcnow()
    )
    
    # Update user stats based on quest category
    stats = Stat.query.filter_by(user_id=user_id).first()
    
    # Determine which stat to reduce based on primary_stat
    stat_type = quest.primary_stat if quest.primary_stat else 'discipline'
    
    # Apply stat change (100 XP = 1 stat point)
    stat_change = xp_loss / 100  # This will be negative
    
    if stat_type == 'strength':
        stats.strength += stat_change
    elif stat_type == 'intelligence':
        stats.intelligence += stat_change
    elif stat_type == 'discipline':
        stats.discipline += stat_change
    elif stat_type == 'focus':
        stats.focus += stat_change
    elif stat_type == 'communication':
        stats.communication += stat_change
    elif stat_type == 'adaptability':
        stats.adaptability += stat_change
    
    stats.last_updated = datetime.utcnow()
    
    # Update user's last active timestamp
    user = User.query.get(user_id)
    user.last_active = datetime.utcnow()
    
    # Update user level and XP
    user_level = UserLevel.query.filter_by(user_id=user_id).first()
    user_level.total_xp += xp_loss  # This will decrease total XP
    user_level.last_updated = datetime.utcnow()
    
    # Check if title needs to be updated due to negative stats
    if any([
        stats.strength < 0,
        stats.intelligence < 0,
        stats.discipline < 0,
        stats.focus < 0,
        stats.communication < 0,
        stats.adaptability < 0
    ]) and user.title != "Alone, I Level Down":
        user.title = "Alone, I Level Down"
    
    db.session.add(xp_event)
    db.session.commit()
    
    # Create failure notification
    failure_notification = Notification(
        id=str(uuid.uuid4()),
        user_id=user_id,
        quest_id=quest.id,
        title="Quest Failed",
        message=f"You lost {abs(xp_loss)} XP and decreased your {stat_type} by {abs(stat_change):.2f}.",
        type="error",
        is_read=False,
        created_at=datetime.utcnow()
    )
    db.session.add(failure_notification)
    db.session.commit()
    
    return jsonify({
        'message': 'Quest failed',
        'xp_lost': abs(xp_loss),
        'stat_decreased': stat_type,
        'stat_change': abs(stat_change),
        'quest': {
            'id': quest.id,
            'text': quest.text,
            'status': quest.status,
            'completed_at': quest.completed_at.isoformat()
        }
    }), 200

@user_bp.route('/dashboard', methods=['GET'])
def get_dashboard():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user = User.query.get(user_id)
    stats = Stat.query.filter_by(user_id=user_id).first()
    user_level = UserLevel.query.filter_by(user_id=user_id).first()
    
    # Get pending quests
    daily_quests = Quest.query.filter_by(user_id=user_id, status='pending', is_optional=False).all()
    optional_quests = Quest.query.filter_by(user_id=user_id, status='pending', is_optional=True).all()
    
    # Get total XP (sum of all XP events)
    xp_events = XPEvent.query.filter_by(user_id=user_id).all()
    total_xp = sum(event.delta_xp for event in xp_events)
    
    # Get unread notifications
    notifications = Notification.query.filter_by(user_id=user_id, is_read=False).order_by(Notification.created_at.desc()).all()
    
    return jsonify({
        'title': user.title,
        'stats': {
            'strength': stats.strength,
            'intelligence': stats.intelligence,
            'discipline': stats.discipline,
            'focus': stats.focus,
            'communication': stats.communication,
            'adaptability': stats.adaptability
        },
        'level': {
            'level': user_level.level,
            'total_xp': user_level.total_xp,
            'available_points': user_level.available_points,
            'next_level_xp': (user_level.level * 1000),
            'progress_percent': min(100, (user_level.total_xp % 1000) / 10)
        },
        'daily_quests': [{
            'id': quest.id,
            'text': quest.text,
            'difficulty': quest.difficulty,
            'reward_xp': quest.reward_xp,
            'due_date': quest.due_date.isoformat(),
            'primary_stat': quest.primary_stat
        } for quest in daily_quests],
        'optional_quests': [{
            'id': quest.id,
            'text': quest.text,
            'difficulty': quest.difficulty,
            'reward_xp': quest.reward_xp,
            'expiration_time': quest.expiration_time.isoformat() if quest.expiration_time else None,
            'primary_stat': quest.primary_stat
        } for quest in optional_quests],
        'notifications': [{
            'id': notification.id,
            'title': notification.title,
            'message': notification.message,
            'type': notification.type,
            'created_at': notification.created_at.isoformat()
        } for notification in notifications[:5]],  # Limit to 5 most recent
        'total_xp': total_xp
    }), 200

@user_bp.route('/notifications', methods=['GET'])
def get_notifications():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    notifications = Notification.query.filter_by(user_id=user_id).order_by(Notification.created_at.desc()).all()
    
    return jsonify({
        'notifications': [{
            'id': notification.id,
            'title': notification.title,
            'message': notification.message,
            'type': notification.type,
            'is_read': notification.is_read,
            'created_at': notification.created_at.isoformat()
        } for notification in notifications]
    }), 200

@user_bp.route('/notifications/mark-read', methods=['POST'])
def mark_notifications_read():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.get_json()
    notification_ids = data.get('notification_ids', [])
    
    if notification_ids:
        # Mark specific notifications as read
        notifications = Notification.query.filter(
            Notification.id.in_(notification_ids),
            Notification.user_id == user_id
        ).all()
        
        for notification in notifications:
            notification.is_read = True
    else:
        # Mark all notifications as read
        notifications = Notification.query.filter_by(user_id=user_id, is_read=False).all()
        for notification in notifications:
            notification.is_read = True
    
    db.session.commit()
    
    return jsonify({'message': 'Notifications marked as read'}), 200

# Gemini AI quest generation
@user_bp.route('/generate-quest', methods=['POST'])
def generate_quest_endpoint():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.get_json()
    
    if 'goal' not in data:
        return jsonify({'error': 'Missing goal field'}), 400
    
    goal_text = data['goal']
    
    try:
        quest_data = generate_quest_with_gemini(goal_text)
        if not quest_data:
            return jsonify({'error': 'Failed to generate quest'}), 500
        
        # Set due date to end of today
        today = datetime.utcnow().date()
        due_date = datetime.combine(today, datetime.max.time())
        
        # Find goal ID if it exists
        goal = Goal.query.filter_by(user_id=user_id, description=goal_text).first()
        goal_id = goal.id if goal else None
        
        new_quest = Quest(
            id=str(uuid.uuid4()),
            user_id=user_id,
            goal_id=goal_id,
            text=quest_data['text'],
            difficulty=quest_data['difficulty'],
            reward_xp=quest_data['reward_xp'],
            status='pending',
            due_date=due_date,
            created_at=datetime.utcnow(),
            is_optional=False,
            primary_stat=quest_data['primary_stat']
        )
        db.session.add(new_quest)
        
        # Create notification for new quest
        new_notification = Notification(
            id=str(uuid.uuid4()),
            user_id=user_id,
            quest_id=new_quest.id,
            title="New Quest Available!",
            message=f"A new quest has been generated for your goal: {goal_text}",
            type="info",
            is_read=False,
            created_at=datetime.utcnow()
        )
        db.session.add(new_notification)
        db.session.commit()
        
        return jsonify({
            'message': 'Quest generated successfully',
            'quest': {
                'id': new_quest.id,
                'text': new_quest.text,
                'difficulty': new_quest.difficulty,
                'reward_xp': new_quest.reward_xp,
                'due_date': new_quest.due_date.isoformat(),
                'primary_stat': new_quest.primary_stat
            }
        }), 201
    except Exception as e:
        return jsonify({'error': f'Error generating quest: {str(e)}'}), 500

# Generate a sample quest for demo purposes
@user_bp.route('/generate-sample-quest', methods=['POST'])
def generate_sample_quest():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.get_json()
    goal_description = data.get('goal', 'Improve yourself')
    
    try:
        quest_data = generate_quest_with_gemini(goal_description)
        if not quest_data:
            # Fallback to a default quest if Gemini fails
            quest_data = {
                'text': f"[QUEST] Complete one task related to: {goal_description}",
                'difficulty': 3,
                'reward_xp': 30,
                'primary_stat': 'discipline'
            }
        
        # Set due date to end of today
        today = datetime.utcnow().date()
        due_date = datetime.combine(today, datetime.max.time())
        
        new_quest = Quest(
            id=str(uuid.uuid4()),
            user_id=user_id,
            goal_id=None,
            text=quest_data['text'],
            difficulty=quest_data['difficulty'],
            reward_xp=quest_data['reward_xp'],
            status='pending',
            due_date=due_date,
            created_at=datetime.utcnow(),
            is_optional=False,
            primary_stat=quest_data['primary_stat']
        )
        
        db.session.add(new_quest)
        db.session.commit()
        
        return jsonify({
            'message': 'Sample quest generated',
            'quest': {
                'id': new_quest.id,
                'text': new_quest.text,
                'difficulty': new_quest.difficulty,
                'reward_xp': new_quest.reward_xp,
                'due_date': new_quest.due_date.isoformat(),
                'primary_stat': new_quest.primary_stat
            }
        }), 201
    except Exception as e:
        print(f"Error generating sample quest: {str(e)}")
        # Fallback to a default quest
        new_quest = Quest(
            id=str(uuid.uuid4()),
            user_id=user_id,
            goal_id=None,
            text=f"[QUEST] Complete one task related to: {goal_description}",
            difficulty=3,
            reward_xp=30,
            status='pending',
            due_date=datetime.combine(datetime.utcnow().date(), datetime.max.time()),
            created_at=datetime.utcnow(),
            is_optional=False,
            primary_stat='discipline'
        )
        
        db.session.add(new_quest)
        db.session.commit()
        
        return jsonify({
            'message': 'Sample quest generated (fallback)',
            'quest': {
                'id': new_quest.id,
                'text': new_quest.text,
                'difficulty': new_quest.difficulty,
                'reward_xp': new_quest.reward_xp,
                'due_date': new_quest.due_date.isoformat(),
                'primary_stat': 'discipline'
            }
        }), 201

# Helper functions
def check_title_status(user_id):
    """Check and update user title based on stats and activity."""
    user = User.query.get(user_id)
    stats = Stat.query.filter_by(user_id=user_id).first()
    
    # Check for negative stats
    has_negative_stat = any([
        stats.strength < 0,
        stats.intelligence < 0,
        stats.discipline < 0,
        stats.focus < 0,
        stats.communication < 0,
        stats.adaptability < 0
    ])
    
    # Check for inactivity (72 hours)
    inactive = (datetime.utcnow() - user.last_active).total_seconds() > 72 * 3600
    
    if (has_negative_stat or inactive) and user.title != "Alone, I Level Down":
        user.title = "Alone, I Level Down"
        
        # Create notification for title change
        title_notification = Notification(
            id=str(uuid.uuid4()),
            user_id=user_id,
            quest_id=None,
            title="Title Changed",
            message="Your title has changed to 'Alone, I Level Down' due to negative stats or inactivity.",
            type="warning",
            is_read=False,
            created_at=datetime.utcnow()
        )
        db.session.add(title_notification)
        db.session.commit()
    elif not has_negative_stat and not inactive and user.title == "Alone, I Level Down":
        user.title = "Alone, I Level Up"
        
        # Create notification for title change
        title_notification = Notification(
            id=str(uuid.uuid4()),
            user_id=user_id,
            quest_id=None,
            title="Title Changed",
            message="Your title has changed back to 'Alone, I Level Up'!",
            type="success",
            is_read=False,
            created_at=datetime.utcnow()
        )
        db.session.add(title_notification)
        db.session.commit()

def generate_quests_if_needed(user_id):
    """Generate quests for user if none exist for today."""
    # Get today's date
    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    # Check if user already has quests for today
    existing_quests = Quest.query.filter_by(user_id=user_id, status='pending', is_optional=False)\
        .filter(Quest.due_date.between(today_start, today_end))\
        .all()
    
    if not existing_quests:
        # Get user's active goals
        goals = Goal.query.filter_by(user_id=user_id, is_active=True).all()
        
        for goal in goals:
            try:
                # Generate a quest for each goal using Gemini
                quest_data = generate_quest_with_gemini(goal.description)
                if quest_data:
                    new_quest = Quest(
                        id=str(uuid.uuid4()),
                        user_id=user_id,
                        goal_id=goal.id,
                        text=quest_data['text'],
                        difficulty=quest_data['difficulty'],
                        reward_xp=quest_data['reward_xp'],
                        status='pending',
                        due_date=today_end,
                        created_at=datetime.utcnow(),
                        is_optional=False,
                        primary_stat=quest_data['primary_stat']
                    )
                    db.session.add(new_quest)
                    
                    # Create notification for new quest
                    new_notification = Notification(
                        id=str(uuid.uuid4()),
                        user_id=user_id,
                        quest_id=new_quest.id,
                        title="New Daily Quest",
                        message=f"A new daily quest has been generated for your goal: {goal.description}",
                        type="info",
                        is_read=False,
                        created_at=datetime.utcnow()
                    )
                    db.session.add(new_notification)
            except Exception as e:
                print(f"Error generating quest for goal {goal.id}: {str(e)}")
                # Fallback to a simple quest if Gemini fails
                difficulty = min(5, max(1, len(goal.description) % 5 + 1))
                reward_xp = difficulty * 10
                
                new_quest = Quest(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    goal_id=goal.id,
                    text=f"[QUEST] Complete one task related to: {goal.description}",
                    difficulty=difficulty,
                    reward_xp=reward_xp,
                    status='pending',
                    due_date=today_end,
                    created_at=datetime.utcnow(),
                    is_optional=False,
                    primary_stat=goal.category if goal.category else 'discipline'
                )
                db.session.add(new_quest)
        
        db.session.commit()

def generate_optional_quest(user_id):
    """Generate a random time-limited optional quest."""
    # Get user's active goals
    goals = Goal.query.filter_by(user_id=user_id, is_active=True).all()
    
    if not goals:
        return
    
    # Randomly select a goal
    goal = random.choice(goals)
    
    try:
        # Generate a quest with Gemini
        quest_data = generate_optional_quest_with_gemini(goal.description)
        if not quest_data:
            return
        
        # Set expiration time (1-4 hours from now)
        hours = random.randint(1, 4)
        expiration_time = datetime.utcnow() + timedelta(hours=hours)
        
        new_quest = Quest(
            id=str(uuid.uuid4()),
            user_id=user_id,
            goal_id=goal.id,
            text=quest_data['text'],
            difficulty=quest_data['difficulty'],
            reward_xp=quest_data['reward_xp'],
            status='pending',
            due_date=expiration_time,  # Same as expiration for optional quests
            created_at=datetime.utcnow(),
            is_optional=True,
            expiration_time=expiration_time,
            primary_stat=quest_data['primary_stat']
        )
        db.session.add(new_quest)
        
        # Create notification for new optional quest
        new_notification = Notification(
            id=str(uuid.uuid4()),
            user_id=user_id,
            quest_id=new_quest.id,
            title="⚠️ Optional Quest Available!",
            message=f"A time-limited optional quest has appeared! Complete it within {hours} hours for bonus rewards.",
            type="warning",
            is_read=False,
            created_at=datetime.utcnow()
        )
        db.session.add(new_notification)
        db.session.commit()
    except Exception as e:
        print(f"Error generating optional quest: {str(e)}")

def generate_quest_with_gemini(goal_text):
    """Generate a quest using Gemini AI."""
    try:
        # Enhanced prompt with Solo Leveling style
        prompt = f"""
        Generate a quest in the style of Solo Leveling manhwa for a user working on: {goal_text}

        The quest should:
        1. Have a clear objective related to {goal_text}
        2. Include a difficulty rating (1-5 stars)
        3. Specify XP reward (10-50 based on difficulty)
        4. Have a time limit (daily quest)
        5. Use language similar to Solo Leveling system notifications
        6. Map to one of these stats: strength, intelligence, discipline, focus, communication, adaptability

        Format:
        [QUEST] <Quest title>
        Difficulty: <stars>
        Reward: <XP> XP
        Stat: <primary stat affected>
        """
        
        # Make API call to Gemini
        headers = {
            "Content-Type": "application/json"
        }
        
        data = {
            "model": GEMINI_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 150
        }
        
        response = requests.post(
            f"{GEMINI_BASE_URL}chat/completions?key={GEMINI_API_KEY}",
            headers=headers,
            json=data
        )
        
        if response.status_code != 200:
            print(f"Gemini API error: {response.status_code} - {response.text}")
            return None
        
        result = response.json()
        quest_text = result['choices'][0]['message']['content'].strip()
        
        # Parse the quest text
        lines = quest_text.split('\n')
        quest_title = lines[0] if lines else "[QUEST] Complete a task"
        
        # Extract difficulty (default to 3 if not found)
        difficulty = 3
        for line in lines:
            if "difficulty:" in line.lower():
                # Count stars or extract number
                if "*" in line:
                    difficulty = line.count("*")
                else:
                    try:
                        difficulty = int(line.split(":")[-1].strip()[0])
                    except:
                        pass
        
        # Ensure difficulty is between 1-5
        difficulty = max(1, min(5, difficulty))
        
        # Extract reward XP (default based on difficulty)
        reward_xp = difficulty * 10
        for line in lines:
            if "reward:" in line.lower() and "xp" in line.lower():
                try:
                    reward_xp = int(''.join(filter(str.isdigit, line)))
                except:
                    pass
        
        # Extract primary stat (default to discipline)
        primary_stat = "discipline"
        for line in lines:
            if "stat:" in line.lower():
                stat_text = line.split(":")[-1].strip().lower()
                if "strength" in stat_text:
                    primary_stat = "strength"
                elif "intelligence" in stat_text:
                    primary_stat = "intelligence"
                elif "discipline" in stat_text:
                    primary_stat = "discipline"
                elif "focus" in stat_text:
                    primary_stat = "focus"
                elif "communication" in stat_text:
                    primary_stat = "communication"
                elif "adaptability" in stat_text:
                    primary_stat = "adaptability"
        
        return {
            'text': quest_title,
            'difficulty': difficulty,
            'reward_xp': reward_xp,
            'primary_stat': primary_stat
        }
    except Exception as e:
        print(f"Error in generate_quest_with_gemini: {str(e)}")
        return None

def generate_optional_quest_with_gemini(goal_text):
    """Generate an optional time-limited quest using Gemini AI."""
    try:
        # Enhanced prompt with Solo Leveling style for optional quests
        prompt = f"""
        Generate a SPECIAL TIME-LIMITED quest in the style of Solo Leveling manhwa for a user working on: {goal_text}

        This is an OPTIONAL quest with higher difficulty and rewards.

        The quest should:
        1. Have a clear objective related to {goal_text} but more challenging
        2. Include a difficulty rating (3-5 stars only, as this is a special quest)
        3. Specify XP reward (30-80 based on difficulty, higher than normal)
        4. Be marked as time-limited and urgent
        5. Use dramatic language similar to Solo Leveling system notifications
        6. Map to one of these stats: strength, intelligence, discipline, focus, communication, adaptability

        Format:
        [SPECIAL QUEST] <Quest title>
        Difficulty: <stars>
        Reward: <XP> XP
        Stat: <primary stat affected>
        """
        
        # Make API call to Gemini
        headers = {
            "Content-Type": "application/json"
        }
        
        data = {
            "model": GEMINI_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 150
        }
        
        response = requests.post(
            f"{GEMINI_BASE_URL}chat/completions?key={GEMINI_API_KEY}",
            headers=headers,
            json=data
        )
        
        if response.status_code != 200:
            print(f"Gemini API error: {response.status_code} - {response.text}")
            return None
        
        result = response.json()
        quest_text = result['choices'][0]['message']['content'].strip()
        
        # Parse the quest text
        lines = quest_text.split('\n')
        quest_title = lines[0] if lines else "[SPECIAL QUEST] Complete an urgent task"
        
        # Extract difficulty (default to 4 for optional quests)
        difficulty = 4
        for line in lines:
            if "difficulty:" in line.lower():
                # Count stars or extract number
                if "*" in line:
                    difficulty = line.count("*")
                else:
                    try:
                        difficulty = int(line.split(":")[-1].strip()[0])
                    except:
                        pass
        
        # Ensure difficulty is between 3-5 for optional quests
        difficulty = max(3, min(5, difficulty))
        
        # Extract reward XP (higher default based on difficulty)
        reward_xp = difficulty * 15  # Higher multiplier for optional quests
        for line in lines:
            if "reward:" in line.lower() and "xp" in line.lower():
                try:
                    reward_xp = int(''.join(filter(str.isdigit, line)))
                except:
                    pass
        
        # Extract primary stat (default to discipline)
        primary_stat = "discipline"
        for line in lines:
            if "stat:" in line.lower():
                stat_text = line.split(":")[-1].strip().lower()
                if "strength" in stat_text:
                    primary_stat = "strength"
                elif "intelligence" in stat_text:
                    primary_stat = "intelligence"
                elif "discipline" in stat_text:
                    primary_stat = "discipline"
                elif "focus" in stat_text:
                    primary_stat = "focus"
                elif "communication" in stat_text:
                    primary_stat = "communication"
                elif "adaptability" in stat_text:
                    primary_stat = "adaptability"
        
        return {
            'text': quest_title,
            'difficulty': difficulty,
            'reward_xp': reward_xp,
            'primary_stat': primary_stat
        }
    except Exception as e:
        print(f"Error in generate_optional_quest_with_gemini: {str(e)}")
        return None

def map_goal_to_category(goal_text):
    """Map a goal description to a stat category."""
    goal_text = goal_text.lower()
    
    # Physical/fitness related
    if any(word in goal_text for word in ['exercise', 'workout', 'gym', 'fitness', 'strength', 'run', 'physical']):
        return 'physical'
    
    # Learning/education related
    if any(word in goal_text for word in ['learn', 'study', 'read', 'book', 'course', 'education', 'knowledge', 'intelligence']):
        return 'learning'
    
    # Routine/habit related
    if any(word in goal_text for word in ['habit', 'routine', 'daily', 'consistent', 'discipline', 'regular']):
        return 'routine'
    
    # Focus/concentration related
    if any(word in goal_text for word in ['focus', 'concentrate', 'attention', 'mindful', 'meditation']):
        return 'concentration'
    
    # Social/communication related
    if any(word in goal_text for word in ['social', 'communicate', 'talk', 'friend', 'network', 'relationship']):
        return 'social'
    
    # Challenge/adaptability related
    if any(word in goal_text for word in ['challenge', 'adapt', 'change', 'new', 'try', 'experiment']):
        return 'challenge'
    
    # Default to routine if no match
    return 'routine'
