"""
Admin Panel Routes - Comprehensive administrative endpoints
Handles user management, permission control, and event approvals
"""

from flask import Blueprint, request, jsonify
from functools import wraps
from datetime import datetime
from app import db, User, Event, EventApproval, Schedule, Notification, mail
from flask_mail import Message

# Create admin blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

# ==================== ADMIN MIDDLEWARE ====================

def admin_required(f):
    """Decorator to verify admin role - use after token_required"""
    @wraps(f)
    def decorated(current_user, *args, **kwargs):
        if current_user.role != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        return f(current_user, *args, **kwargs)
    return decorated


# ==================== USER MANAGEMENT ENDPOINTS ====================

@admin_bp.route('/users', methods=['GET'])
def list_all_users(current_user):
    """
    List all users with filters
    Query params: role, department, is_active, page, per_page
    """
    role_filter = request.args.get('role')
    department_filter = request.args.get('department')
    is_active = request.args.get('is_active', type=lambda x: x.lower() == 'true')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = User.query
    
    if role_filter:
        query = query.filter_by(role=role_filter)
    if department_filter:
        query = query.filter_by(department=department_filter)
    if is_active is not None:
        query = query.filter_by(is_active=is_active)
    
    users = query.paginate(page=page, per_page=per_page)
    
    return jsonify({
        'total': users.total,
        'pages': users.pages,
        'current_page': page,
        'users': [u.to_dict() for u in users.items]
    }), 200


@admin_bp.route('/users/<int:user_id>', methods=['GET'])
def get_user_details(current_user, user_id):
    """Get detailed user information including schedules and events"""
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    user_data = user.to_dict()
    user_data['schedules'] = [s.to_dict() for s in user.schedules]
    user_data['created_events'] = len(user.events)
    
    return jsonify(user_data), 200


@admin_bp.route('/users/<int:user_id>/role', methods=['PUT'])
def update_user_role(current_user, user_id):
    """Change user role (admin, teacher, student)"""
    data = request.get_json()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    valid_roles = ['admin', 'teacher', 'student']
    if data.get('role') not in valid_roles:
        return jsonify({'error': 'Invalid role'}), 400
    
    user.role = data['role']
    
    # Auto-enable schedule creation for teachers and admins
    if data['role'] in ['teacher', 'admin']:
        user.can_create_schedule = True
    
    db.session.commit()
    
    return jsonify({
        'message': 'User role updated successfully',
        'user': user.to_dict()
    }), 200


@admin_bp.route('/users/<int:user_id>/permissions', methods=['PUT'])
def update_user_permissions(current_user, user_id):
    """
    Update user permissions for schedule creation
    Allows fine-grained control over who can create schedules
    """
    data = request.get_json()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    user.can_create_schedule = data.get('can_create_schedule', user.can_create_schedule)
    user.is_active = data.get('is_active', user.is_active)
    
    db.session.commit()
    
    return jsonify({
        'message': 'User permissions updated',
        'user': user.to_dict()
    }), 200


@admin_bp.route('/users/<int:user_id>/activate', methods=['POST'])
def activate_user(current_user, user_id):
    """Activate a deactivated user account"""
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    user.is_active = True
    db.session.commit()
    
    return jsonify({
        'message': 'User activated successfully',
        'user': user.to_dict()
    }), 200


@admin_bp.route('/users/<int:user_id>/deactivate', methods=['POST'])
def deactivate_user(current_user, user_id):
    """Deactivate a user account (soft delete)"""
    if user_id == current_user.id:
        return jsonify({'error': 'Cannot deactivate your own account'}), 400
    
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    user.is_active = False
    db.session.commit()
    
    return jsonify({
        'message': 'User deactivated successfully',
        'user': user.to_dict()
    }), 200


@admin_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
def reset_user_password(current_user, user_id):
    """
    Generate a temporary password for user
    In production, send password reset email
    """
    import secrets
    
    data = request.get_json()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Generate temporary password
    temp_password = secrets.token_urlsafe(16)
    user.set_password(temp_password)
    db.session.commit()
    
    # In production: send email with temporary password
    # send_password_reset_email(user.email, temp_password)
    
    return jsonify({
        'message': 'Password reset (check email for temporary password)',
        'temporary_password': temp_password if data.get('return_password') else None
    }), 200


# ==================== STATISTICS & ANALYTICS ====================

@admin_bp.route('/statistics', methods=['GET'])
def get_statistics(current_user):
    """
    Get platform statistics
    Returns user counts, schedule counts, event counts by role
    """
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    
    admin_count = User.query.filter_by(role='admin').count()
    teacher_count = User.query.filter_by(role='teacher').count()
    student_count = User.query.filter_by(role='student').count()
    
    total_schedules = Schedule.query.count()
    class_schedules = Schedule.query.filter_by(is_class_schedule=True).count()
    event_schedules = Schedule.query.filter_by(is_class_schedule=False).count()
    
    total_events = Event.query.count()
    pending_approvals = Event.query.filter_by(approval_status='pending').count()
    approved_events = Event.query.filter_by(approval_status='approved').count()
    declined_events = Event.query.filter_by(approval_status='declined').count()
    
    return jsonify({
        'users': {
            'total': total_users,
            'active': active_users,
            'inactive': total_users - active_users,
            'by_role': {
                'admins': admin_count,
                'teachers': teacher_count,
                'students': student_count
            }
        },
        'schedules': {
            'total': total_schedules,
            'class_schedules': class_schedules,
            'event_schedules': event_schedules
        },
        'events': {
            'total': total_events,
            'pending_approval': pending_approvals,
            'approved': approved_events,
            'declined': declined_events
        }
    }), 200


@admin_bp.route('/departments', methods=['GET'])
def get_departments(current_user):
    """Get list of all departments with user counts"""
    departments = db.session.query(
        User.department,
        db.func.count(User.id).label('user_count')
    ).filter(User.department != None).group_by(User.department).all()
    
    return jsonify({
        'departments': [
            {
                'name': dept,
                'user_count': count
            }
            for dept, count in departments
        ]
    }), 200


# ==================== EVENT APPROVAL MANAGEMENT ====================

@admin_bp.route('/approvals', methods=['GET'])
def get_pending_approvals(current_user):
    """
    Get all pending event approvals
    Query params: status, page, per_page
    """
    status_filter = request.args.get('status', 'pending')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = EventApproval.query
    
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    approvals = query.paginate(page=page, per_page=per_page)
    
    approval_data = []
    for approval in approvals.items:
        data = approval.to_dict()
        data['event'] = approval.event.to_dict()
        data['organizer'] = User.query.get(approval.event.organizer_id).to_dict()
        approval_data.append(data)
    
    return jsonify({
        'total': approvals.total,
        'pages': approvals.pages,
        'current_page': page,
        'approvals': approval_data
    }), 200


@admin_bp.route('/approvals/<int:approval_id>/approve', methods=['POST'])
def approve_event(current_user, approval_id):
    """Approve an event request"""
    data = request.get_json()
    approval = EventApproval.query.get(approval_id)
    
    if not approval:
        return jsonify({'error': 'Approval request not found'}), 404
    
    approval.status = 'approved'
    approval.reason = data.get('reason', 'Approved')
    
    # Update event status
    event = approval.event
    event.approval_status = 'approved'
    
    # Create notification
    notification = Notification(
        user_id=event.organizer_id,
        event_id=event.id,
        type='approval',
        message=f'Your event "{event.title}" has been approved'
    )
    
    db.session.add(notification)
    db.session.commit()
    
    # Send email notification (would need mail setup)
    # send_approval_email(event.organizer.email, event)
    
    return jsonify({
        'message': 'Event approved successfully',
        'approval': approval.to_dict()
    }), 200


@admin_bp.route('/approvals/<int:approval_id>/decline', methods=['POST'])
def decline_event(current_user, approval_id):
    """Decline an event request"""
    data = request.get_json()
    approval = EventApproval.query.get(approval_id)
    
    if not approval:
        return jsonify({'error': 'Approval request not found'}), 404
    
    if not data.get('reason'):
        return jsonify({'error': 'Reason is required to decline'}), 400
    
    approval.status = 'declined'
    approval.reason = data['reason']
    
    # Update event status
    event = approval.event
    event.approval_status = 'declined'
    
    # Create notification
    notification = Notification(
        user_id=event.organizer_id,
        event_id=event.id,
        type='decline',
        message=f'Your event "{event.title}" has been declined: {data["reason"]}'
    )
    
    db.session.add(notification)
    db.session.commit()
    
    # Send email notification
    # send_decline_email(event.organizer.email, event, data['reason'])
    
    return jsonify({
        'message': 'Event declined successfully',
        'approval': approval.to_dict()
    }), 200


# ==================== FACILITY MANAGEMENT ====================

@admin_bp.route('/facilities', methods=['GET'])
def get_facilities(current_user):
    """
    Get list of all facilities/rooms with their schedules
    Returns building and room information with event count
    """
    facilities = db.session.query(
        Event.building,
        Event.room_number,
        db.func.count(Event.id).label('event_count')
    ).filter(
        Event.building != None,
        Event.room_number != None
    ).group_by(Event.building, Event.room_number).all()
    
    facility_list = []
    for building, room, count in facilities:
        facility_list.append({
            'building': building,
            'room_number': room,
            'event_count': count,
            'location': f'{building} Room {room}'
        })
    
    return jsonify({
        'facilities': facility_list,
        'total_facilities': len(facility_list)
    }), 200


@admin_bp.route('/facilities/<building>/<room>/schedule', methods=['GET'])
def get_facility_schedule(current_user, building, room):
    """
    Get schedule for a specific facility
    Returns all events in that room
    """
    events = Event.query.filter_by(
        building=building,
        room_number=room
    ).order_by(Event.start_time).all()
    
    return jsonify({
        'facility': f'{building} Room {room}',
        'events': [e.to_dict() for e in events],
        'total_events': len(events)
    }), 200


# ==================== AUDIT LOGGING ====================

@admin_bp.route('/audit-log', methods=['GET'])
def get_audit_log(current_user):
    """
    Get admin action audit log
    In a real system, this would log all admin actions
    """
    # For now, return recent updates as a simple audit
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    # Get recently updated events
    recent_events = Event.query.order_by(
        Event.updated_at.desc()
    ).paginate(page=page, per_page=per_page)
    
    return jsonify({
        'total': recent_events.total,
        'pages': recent_events.pages,
        'log_entries': [e.to_dict() for e in recent_events.items]
    }), 200


# ==================== BULK OPERATIONS ====================

@admin_bp.route('/users/bulk-grant-permission', methods=['POST'])
def bulk_grant_permission(current_user):
    """Grant schedule creation permission to multiple users"""
    data = request.get_json()
    user_ids = data.get('user_ids', [])
    
    if not user_ids:
        return jsonify({'error': 'No user IDs provided'}), 400
    
    users = User.query.filter(User.id.in_(user_ids)).all()
    
    for user in users:
        user.can_create_schedule = True
    
    db.session.commit()
    
    return jsonify({
        'message': f'Granted permission to {len(users)} users',
        'updated_count': len(users)
    }), 200


@admin_bp.route('/users/bulk-revoke-permission', methods=['POST'])
def bulk_revoke_permission(current_user):
    """Revoke schedule creation permission from multiple users"""
    data = request.get_json()
    user_ids = data.get('user_ids', [])
    
    if not user_ids:
        return jsonify({'error': 'No user IDs provided'}), 400
    
    users = User.query.filter(User.id.in_(user_ids)).all()
    
    for user in users:
        user.can_create_schedule = False
    
    db.session.commit()
    
    return jsonify({
        'message': f'Revoked permission from {len(users)} users',
        'updated_count': len(users)
    }), 200
