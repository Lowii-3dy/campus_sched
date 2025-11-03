"""
Event Approval Routes
Handles event approval workflows and notifications
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
from app import db, Event, EventApproval, User, Notification, mail
from flask_mail import Message
from functools import wraps

approval_bp = Blueprint('approvals', __name__, url_prefix='/api/approvals')

# ==================== APPROVAL WORKFLOW ====================

@approval_bp.route('/', methods=['POST'])
def request_approval(current_user):
    """
    Request approval for an event
    Creates approval request for admin review
    
    Event approval request creation
    """
    data = request.get_json()
    event_id = data.get('event_id')
    
    event = Event.query.get(event_id)
    if not event:
        return jsonify({'error': 'Event not found'}), 404
    
    # Check if user is event organizer
    if event.organizer_id != current_user.id and current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    # Check if already has pending approval
    existing = EventApproval.query.filter_by(
        event_id=event_id,
        status='pending'
    ).first()
    
    if existing:
        return jsonify({'error': 'Approval already requested'}), 409
    
    # Create approval record
    approval = EventApproval(
        event_id=event_id,
        approver_id=None,  # Will be assigned by admin
        status='pending',
        reason=data.get('reason', 'Event requires approval')
    )
    
    # Update event status
    event.approval_status = 'pending'
    event.requires_approval = True
    
    db.session.add(approval)
    db.session.commit()
    
    # Notify admins
    notify_admins_pending_approval(event)
    
    return jsonify({
        'message': 'Approval requested successfully',
        'approval': approval.to_dict()
    }), 201


@approval_bp.route('/<int:approval_id>/approve', methods=['POST'])
def approve_approval(current_user, approval_id):
    """
    Approve an event (admin only)
    
    Event approval workflow
    """
    # Check admin role
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    data = request.get_json()
    approval = EventApproval.query.get(approval_id)
    
    if not approval:
        return jsonify({'error': 'Approval not found'}), 404
    
    if approval.status != 'pending':
        return jsonify({'error': 'Approval is not pending'}), 400
    
    # Update approval
    approval.status = 'approved'
    approval.approver_id = current_user.id
    approval.reason = data.get('reason', 'Approved')
    approval.updated_at = datetime.utcnow()
    
    # Update event
    event = approval.event
    event.approval_status = 'approved'
    
    db.session.commit()
    
    # Create notification
    create_notification(
        event.organizer_id,
        event_id=event.id,
        type='approval',
        message=f'Your event "{event.title}" has been approved for {event.start_time.strftime("%B %d at %I:%M %p")}'
    )
    
    # Send email
    send_approval_email(event.organizer.email, event, 'approved', data.get('reason'))
    
    return jsonify({
        'message': 'Event approved successfully',
        'approval': approval.to_dict()
    }), 200


@approval_bp.route('/<int:approval_id>/decline', methods=['POST'])
def decline_approval(current_user, approval_id):
    """
    Decline an event approval request (admin only)
    Requires reason for decline
    
    Event decline workflow
    """
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    data = request.get_json()
    
    if not data.get('reason'):
        return jsonify({'error': 'Reason is required for decline'}), 400
    
    approval = EventApproval.query.get(approval_id)
    
    if not approval:
        return jsonify({'error': 'Approval not found'}), 404
    
    if approval.status != 'pending':
        return jsonify({'error': 'Approval is not pending'}), 400
    
    # Update approval
    approval.status = 'declined'
    approval.approver_id = current_user.id
    approval.reason = data['reason']
    approval.updated_at = datetime.utcnow()
    
    # Update event
    event = approval.event
    event.approval_status = 'declined'
    
    db.session.commit()
    
    # Create notification
    create_notification(
        event.organizer_id,
        event_id=event.id,
        type='decline',
        message=f'Your event "{event.title}" was declined. Reason: {data["reason"]}'
    )
    
    # Send email
    send_approval_email(event.organizer.email, event, 'declined', data['reason'])
    
    return jsonify({
        'message': 'Event declined successfully',
        'approval': approval.to_dict()
    }), 200


@approval_bp.route('/<int:approval_id>/request-changes', methods=['POST'])
def request_changes(current_user, approval_id):
    """
    Request changes to an event (admin only)
    Sends event back for modification
    
    Change request workflow
    """
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    data = request.get_json()
    approval = EventApproval.query.get(approval_id)
    
    if not approval:
        return jsonify({'error': 'Approval not found'}), 404
    
    # Create notification about changes needed
    event = approval.event
    create_notification(
        event.organizer_id,
        event_id=event.id,
        type='changes_requested',
        message=f'Changes requested for event "{event.title}". Reason: {data.get("reason")}'
    )
    
    # Send email
    send_changes_request_email(event.organizer.email, event, data.get('reason'))
    
    return jsonify({
        'message': 'Change request sent successfully'
    }), 200


@approval_bp.route('/<int:approval_id>/resubmit', methods=['POST'])
def resubmit_for_approval(current_user, approval_id):
    """
    Resubmit event for approval after changes
    
    Event resubmission workflow
    """
    approval = EventApproval.query.get(approval_id)
    
    if not approval:
        return jsonify({'error': 'Approval not found'}), 404
    
    event = approval.event
    
    # Check if user is organizer
    if event.organizer_id != current_user.id and current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    # Reset status to pending
    approval.status = 'pending'
    approval.approver_id = None
    approval.reason = request.get_json().get('reason', 'Resubmitted for approval')
    approval.updated_at = datetime.utcnow()
    
    event.approval_status = 'pending'
    
    db.session.commit()
    
    # Notify admins
    notify_admins_pending_approval(event)
    
    return jsonify({
        'message': 'Event resubmitted for approval',
        'approval': approval.to_dict()
    }), 200


# ==================== APPROVAL QUERIES ====================

@approval_bp.route('/', methods=['GET'])
def list_approvals(current_user):
    """
    List approvals with filtering
    Query params: status (pending/approved/declined), page, per_page
    
    Approval list with filtering
    """
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    status = request.args.get('status', 'pending')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = EventApproval.query
    
    if status:
        query = query.filter_by(status=status)
    
    approvals = query.order_by(
        EventApproval.created_at.desc()
    ).paginate(page=page, per_page=per_page)
    
    result = []
    for approval in approvals.items:
        data = approval.to_dict()
        data['event'] = approval.event.to_dict()
        data['organizer'] = approval.event.organizer.to_dict()
        result.append(data)
    
    return jsonify({
        'total': approvals.total,
        'pages': approvals.pages,
        'current_page': page,
        'approvals': result
    }), 200


@approval_bp.route('/<int:approval_id>', methods=['GET'])
def get_approval(current_user, approval_id):
    """Get approval details"""
    approval = EventApproval.query.get(approval_id)
    
    if not approval:
        return jsonify({'error': 'Approval not found'}), 404
    
    # Check permission
    event = approval.event
    if event.organizer_id != current_user.id and current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    data = approval.to_dict()
    data['event'] = event.to_dict()
    data['organizer'] = event.organizer.to_dict()
    
    return jsonify(data), 200


@approval_bp.route('/event/<int:event_id>', methods=['GET'])
def get_event_approval_status(current_user, event_id):
    """Get approval status for specific event"""
    event = Event.query.get(event_id)
    
    if not event:
        return jsonify({'error': 'Event not found'}), 404
    
    # Check permission
    if event.organizer_id != current_user.id and current_user.role != 'admin':
        if not event.schedule.is_public:
            return jsonify({'error': 'Access denied'}), 403
    
    approval = EventApproval.query.filter_by(event_id=event_id).first()
    
    return jsonify({
        'event_id': event_id,
        'requires_approval': event.requires_approval,
        'approval_status': event.approval_status,
        'approval': approval.to_dict() if approval else None
    }), 200


@approval_bp.route('/pending-count', methods=['GET'])
def get_pending_count(current_user):
    """
    Get count of pending approvals (admin only)
    Used for dashboard badge
    
    Pending approval count
    """
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    count = EventApproval.query.filter_by(status='pending').count()
    
    return jsonify({'pending_count': count}), 200


# ==================== NOTIFICATIONS ====================

@approval_bp.route('/notifications', methods=['GET'])
def get_user_notifications(current_user):
    """
    Get notifications for current user
    Query params: is_read (optional), page, per_page
    
    User notifications retrieval
    """
    is_read = request.args.get('is_read', type=lambda x: x.lower() == 'true')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = Notification.query.filter_by(user_id=current_user.id)
    
    if is_read is not None:
        query = query.filter_by(is_read=is_read)
    
    notifications = query.order_by(
        Notification.sent_at.desc()
    ).paginate(page=page, per_page=per_page)
    
    return jsonify({
        'total': notifications.total,
        'pages': notifications.pages,
        'current_page': page,
        'unread_count': Notification.query.filter_by(
            user_id=current_user.id,
            is_read=False
        ).count(),
        'notifications': [n.to_dict() for n in notifications.items]
    }), 200


@approval_bp.route('/notifications/<int:notif_id>/read', methods=['POST'])
def mark_notification_read(current_user, notif_id):
    """Mark notification as read"""
    notification = Notification.query.get(notif_id)
    
    if not notification:
        return jsonify({'error': 'Notification not found'}), 404
    
    if notification.user_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    notification.is_read = True
    db.session.commit()
    
    return jsonify({'message': 'Marked as read'}), 200


@approval_bp.route('/notifications/mark-all-read', methods=['POST'])
def mark_all_read(current_user):
    """Mark all user notifications as read"""
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({
        Notification.is_read: True
    })
    db.session.commit()
    
    return jsonify({'message': 'All notifications marked as read'}), 200


# ==================== HELPER FUNCTIONS ====================

def create_notification(user_id, event_id=None, type='info', message=''):
    """
    Create in-app notification
    
    Notification creation helper
    """
    notification = Notification(
        user_id=user_id,
        event_id=event_id,
        type=type,
        message=message,
        is_read=False
    )
    db.session.add(notification)
    db.session.commit()
    return notification


def notify_admins_pending_approval(event):
    """
    Notify all admins about pending event approval
    
    Admin notification for pending approvals
    """
    admins = User.query.filter_by(role='admin').all()
    
    for admin in admins:
        create_notification(
            admin.id,
            event_id=event.id,
            type='approval_pending',
            message=f'Event "{event.title}" requires approval for {event.start_time.strftime("%B %d")}'
        )
        
        # Send email to admin
        send_admin_notification_email(
            admin.email,
            event,
            'pending_approval'
        )


def send_approval_email(email, event, status, reason=''):
    """
    Send approval/decline email notification
    
    Email notification for approvals
    """
    if status == 'approved':
        subject = f'Event Approved: {event.title}'
        body = f"""
        Your event "{event.title}" has been approved!
        
        Date & Time: {event.start_time.strftime('%B %d, %Y at %I:%M %p')}
        Location: {event.location or event.building}
        
        Your event is now confirmed and visible in the schedule.
        """
    else:
        subject = f'Event Declined: {event.title}'
        body = f"""
        Your event "{event.title}" has been declined.
        
        Reason: {reason}
        
        Please contact administration if you have questions.
        """
    
    try:
        msg = Message(
            subject=subject,
            recipients=[email],
            body=body
        )
        mail.send(msg)
    except Exception as e:
        print(f'Error sending email: {e}')


def send_admin_notification_email(email, event, type):
    """Send notification email to admin"""
    if type == 'pending_approval':
        subject = f'Event Approval Needed: {event.title}'
        body = f"""
        New event requires approval:
        
        Title: {event.title}
        Organizer: {event.organizer.first_name} {event.organizer.last_name}
        Date & Time: {event.start_time.strftime('%B %d, %Y at %I:%M %p')}
        Location: {event.location}
        
        Log in to the admin panel to review and approve/decline.
        """
    
    try:
        msg = Message(
            subject=subject,
            recipients=[email],
            body=body
        )
        mail.send(msg)
    except Exception as e:
        print(f'Error sending email: {e}')


def send_changes_request_email(email, event, reason):
    """Send email requesting changes to event"""
    subject = f'Changes Requested: {event.title}'
    body = f"""
    Changes have been requested for your event "{event.title}".
    
    Reason: {reason}
    
    Please make the necessary changes and resubmit your event for approval.
    """
    
    try:
        msg = Message(
            subject=subject,
            recipients=[email],
            body=body
        )
        mail.send(msg)
    except Exception as e:
        print(f'Error sending email: {e}')
