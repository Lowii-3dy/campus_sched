"""
Email Management Routes
Endpoints for configuring email preferences and templates
"""

from flask import Blueprint, request, jsonify
from app import db, User

email_bp = Blueprint('email', __name__, url_prefix='/api/email')

class UserEmailPreferences(db.Model):
    """Model for user email preferences"""
    __tablename__ = 'user_email_preferences'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    receive_approval_emails = db.Column(db.Boolean, default=True)
    receive_reminders = db.Column(db.Boolean, default=True)
    receive_schedule_updates = db.Column(db.Boolean, default=True)
    reminder_hours_before = db.Column(db.Integer, default=24)
    
    def to_dict(self):
        return {
            'receive_approval_emails': self.receive_approval_emails,
            'receive_reminders': self.receive_reminders,
            'receive_schedule_updates': self.receive_schedule_updates,
            'reminder_hours_before': self.reminder_hours_before
        }


# ==================== EMAIL PREFERENCES ====================

@email_bp.route('/preferences', methods=['GET'])
def get_email_preferences(current_user):
    """Get user's email notification preferences"""
    prefs = UserEmailPreferences.query.filter_by(user_id=current_user.id).first()
    
    if not prefs:
        # Create default preferences
        prefs = UserEmailPreferences(user_id=current_user.id)
        db.session.add(prefs)
        db.session.commit()
    
    return jsonify(prefs.to_dict()), 200


@email_bp.route('/preferences', methods=['PUT'])
def update_email_preferences(current_user):
    """Update user's email notification preferences"""
    data = request.get_json()
    
    prefs = UserEmailPreferences.query.filter_by(user_id=current_user.id).first()
    
    if not prefs:
        prefs = UserEmailPreferences(user_id=current_user.id)
    
    prefs.receive_approval_emails = data.get('receive_approval_emails', prefs.receive_approval_emails)
    prefs.receive_reminders = data.get('receive_reminders', prefs.receive_reminders)
    prefs.receive_schedule_updates = data.get('receive_schedule_updates', prefs.receive_schedule_updates)
    prefs.reminder_hours_before = data.get('reminder_hours_before', prefs.reminder_hours_before)
    
    db.session.commit()
    
    return jsonify({
        'message': 'Preferences updated',
        'preferences': prefs.to_dict()
    }), 200


@email_bp.route('/verify', methods=['POST'])
def verify_email(current_user):
    """Send verification email to user"""
    from email_service import EmailService
    import secrets
    
    # Generate verification token
    token = secrets.token_urlsafe(32)
    
    # Store in cache or database (simplified)
    current_user.email_verification_token = token
    current_user.email_verified = False
    db.session.commit()
    
    # Send verification email
    verification_link = f"https://campusscheduler.edu/verify-email?token={token}"
    
    html_body = f"""
    <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>Verify Your Email</h2>
            <p>Please verify your email address by clicking the link below:</p>
            <p><a href="{verification_link}">Verify Email</a></p>
        </body>
    </html>
    """
    
    try:
        from flask_mail import Message, Mail
        mail = Mail()
        msg = Message(
            subject='Verify Your Email',
            recipients=[current_user.email],
            html=html_body
        )
        mail.send(msg)
        
        return jsonify({'message': 'Verification email sent'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@email_bp.route('/test', methods=['POST'])
def send_test_email(current_user):
    """Send test email to user"""
    from email_service import EmailService
    
    try:
        EmailService.send_event_reminder(
            current_user.email,
            {
                'title': 'Test Event',
                'start_time': '2024-11-15T14:00:00',
                'location': 'Test Building Room 101',
                'room_number': '101'
            },
            hours_before=1
        )
        
        return jsonify({'message': 'Test email sent successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
