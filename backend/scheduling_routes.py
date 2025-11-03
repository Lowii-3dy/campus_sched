"""
Scheduling Routes - Advanced scheduling endpoints
Includes overlap detection, conflict resolution, and availability checking
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from scheduling import SchedulingManager, ConflictResolution, check_event_overlap
from app import Event, Schedule, User, db

scheduling_bp = Blueprint('scheduling', __name__, url_prefix='/api/scheduling')

# ==================== OVERLAP DETECTION ENDPOINTS ====================

@scheduling_bp.route('/check-overlap', methods=['POST'])
def check_overlap(current_user):
    """
    Check if proposed event overlaps with existing events
    Request body: schedule_id, start_time, end_time, exclude_event_id (optional)
    
    Real-time overlap checking endpoint
    """
    data = request.get_json()
    
    start_time = datetime.fromisoformat(data['start_time'])
    end_time = datetime.fromisoformat(data['end_time'])
    exclude_id = data.get('exclude_event_id')
    
    # Create temporary event for checking
    temp_event = Event(
        schedule_id=data['schedule_id'],
        start_time=start_time,
        end_time=end_time,
        organizer_id=current_user.id
    )
    
    conflict = SchedulingManager.check_overlap(temp_event, exclude_event_id=exclude_id)
    
    if conflict:
        return jsonify({
            'has_overlap': True,
            'conflicting_event': conflict.to_dict(),
            'conflict_duration': str((min(end_time, conflict.end_time) - max(start_time, conflict.start_time)))
        }), 200
    
    return jsonify({'has_overlap': False}), 200


@scheduling_bp.route('/facility-availability', methods=['POST'])
def check_facility_availability(current_user):
    """
    Check facility availability for a given time slot
    Request: building, room_number, start_time, end_time
    
    Facility booking availability check
    """
    data = request.get_json()
    
    start_time = datetime.fromisoformat(data['start_time'])
    end_time = datetime.fromisoformat(data['end_time'])
    
    conflicts = SchedulingManager.get_facility_availability(
        data['building'],
        data['room_number'],
        start_time,
        end_time
    )
    
    if conflicts:
        return jsonify({
            'available': False,
            'conflicts': [c.to_dict() for c in conflicts],
            'conflict_count': len(conflicts)
        }), 200
    
    return jsonify({'available': True}), 200


@scheduling_bp.route('/suggest-times', methods=['POST'])
def suggest_alternative_times(current_user):
    """
    Get suggested alternative time slots for an event
    Request: schedule_id, start_time, end_time, duration_minutes (optional)
    
    Intelligent scheduling suggestions
    """
    data = request.get_json()
    
    schedule = Schedule.query.get(data['schedule_id'])
    if not schedule:
        return jsonify({'error': 'Schedule not found'}), 404
    
    # Create temporary event for suggestion
    temp_event = Event(
        schedule_id=data['schedule_id'],
        start_time=datetime.fromisoformat(data['start_time']),
        end_time=datetime.fromisoformat(data['end_time']),
        organizer_id=current_user.id
    )
    
    alternatives = SchedulingManager.suggest_alternative_times(
        temp_event,
        duration_minutes=data.get('duration_minutes')
    )
    
    return jsonify({
        'alternatives': alternatives,
        'count': len(alternatives)
    }), 200


# ==================== SCHEDULE VIEW ENDPOINTS ====================

@scheduling_bp.route('/daily/<int:schedule_id>/<date_str>', methods=['GET'])
def get_daily_schedule(current_user, schedule_id, date_str):
    """
    Get all events for a specific day
    URL format: /daily/schedule_id/YYYY-MM-DD
    
    Daily schedule view
    """
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400
    
    schedule = Schedule.query.get(schedule_id)
    if not schedule:
        return jsonify({'error': 'Schedule not found'}), 404
    
    # Check permission
    if schedule.user_id != current_user.id and current_user.role != 'admin':
        if not schedule.is_public:
            return jsonify({'error': 'Access denied'}), 403
    
    events = Event.query.filter(
        Event.schedule_id == schedule_id,
        db.func.date(Event.start_time) == date.date()
    ).order_by(Event.start_time).all()
    
    return jsonify({
        'date': date.isoformat(),
        'schedule_id': schedule_id,
        'events': [e.to_dict() for e in events],
        'count': len(events)
    }), 200


@scheduling_bp.route('/weekly/<int:schedule_id>/<date_str>', methods=['GET'])
def get_weekly_schedule(current_user, schedule_id, date_str):
    """
    Get all events for a week
    URL format: /weekly/schedule_id/YYYY-MM-DD (Monday of that week)
    
    Weekly schedule view
    """
    try:
        start_date = datetime.strptime(date_str, '%Y-%m-%d')
        # Adjust to Monday
        start_date = start_date - timedelta(days=start_date.weekday())
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400
    
    schedule = Schedule.query.get(schedule_id)
    if not schedule:
        return jsonify({'error': 'Schedule not found'}), 404
    
    end_date = start_date + timedelta(days=7)
    
    events = Event.query.filter(
        Event.schedule_id == schedule_id,
        Event.start_time >= start_date,
        Event.start_time < end_date
    ).order_by(Event.start_time).all()
    
    # Organize by day
    weekly = {}
    for i in range(7):
        day = (start_date + timedelta(days=i)).strftime('%A')
        weekly[day] = []
    
    for event in events:
        day = event.start_time.strftime('%A')
        if day in weekly:
            weekly[day].append(event.to_dict())
    
    return jsonify({
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'schedule': weekly,
        'total_events': len(events)
    }), 200


@scheduling_bp.route('/conflicts/<int:schedule_id>', methods=['GET'])
def get_schedule_conflicts(current_user, schedule_id):
    """
    Get all conflicts in a schedule
    
    Conflict identification and reporting
    """
    schedule = Schedule.query.get(schedule_id)
    if not schedule:
        return jsonify({'error': 'Schedule not found'}), 404
    
    # Permission check
    if schedule.user_id != current_user.id and current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    events = Event.query.filter_by(schedule_id=schedule_id)\
        .order_by(Event.start_time).all()
    
    conflicts = []
    for i, e1 in enumerate(events):
        for e2 in events[i+1:]:
            if e1.start_time < e2.end_time and e1.end_time > e2.start_time:
                overlap_start = max(e1.start_time, e2.start_time)
                overlap_end = min(e1.end_time, e2.end_time)
                overlap_duration = (overlap_end - overlap_start).total_seconds() / 60
                
                conflicts.append({
                    'event1': e1.to_dict(),
                    'event2': e2.to_dict(),
                    'overlap_start': overlap_start.isoformat(),
                    'overlap_end': overlap_end.isoformat(),
                    'overlap_minutes': overlap_duration
                })
    
    return jsonify({
        'schedule_id': schedule_id,
        'conflicts': conflicts,
        'conflict_count': len(conflicts)
    }), 200


@scheduling_bp.route('/common-time', methods=['POST'])
def find_common_time(current_user):
    """
    Find common available time slots for multiple users
    Request: user_ids (list), duration_minutes, min_date (optional), max_date (optional)
    
    Group scheduling endpoint
    """
    data = request.get_json()
    user_ids = data.get('user_ids', [])
    duration = data.get('duration_minutes', 60)
    
    if not user_ids or len(user_ids) < 2:
        return jsonify({'error': 'At least 2 user IDs required'}), 400
    
    min_date = datetime.fromisoformat(data['min_date']) if data.get('min_date') else None
    max_date = datetime.fromisoformat(data['max_date']) if data.get('max_date') else None
    
    common_slots = SchedulingManager.find_common_time_slot(
        user_ids, duration, min_date, max_date
    )
    
    return jsonify({
        'user_ids': user_ids,
        'duration_minutes': duration,
        'common_slots': common_slots,
        'count': len(common_slots)
    }), 200


@scheduling_bp.route('/resolve-conflict', methods=['POST'])
def resolve_conflict(current_user):
    """
    Get resolution strategies for a conflicting event
    Request: event_id, conflicting_event_id
    
    Conflict resolution suggestions
    """
    data = request.get_json()
    
    event = Event.query.get(data['event_id'])
    conflicting = Event.query.get(data['conflicting_event_id'])
    
    if not event or not conflicting:
        return jsonify({'error': 'Event not found'}), 404
    
    strategies = ConflictResolution.resolve_overlap_conflict(event, conflicting)
    
    return jsonify({
        'event_id': event.id,
        'conflicting_event_id': conflicting.id,
        'strategies': strategies
    }), 200


@scheduling_bp.route('/user-conflicts/<int:user_id>', methods=['GET'])
def get_user_conflicts(current_user, user_id):
    """
    Get all conflicts across user's schedules
    
    User-wide conflict reporting
    """
    if user_id != current_user.id and current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    report = ConflictResolution.generate_conflict_report(user_id)
    
    return jsonify({
        'user_id': user_id,
        'user_email': user.email,
        'conflicts': report,
        'total_conflicts': len(report)
    }), 200
