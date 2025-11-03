"""
Campus Scheduler Backend - Main Flask Application
Handles authentication, scheduling, and event management
"""

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import jwt
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///campus_scheduler.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Email configuration
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', True)
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@campusscheduler.com')

db = SQLAlchemy(app)
mail = Mail(app)

# ==================== DATABASE MODELS ====================

class User(db.Model):
    """User model for authentication and role management"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), default='student')  # student, teacher, admin
    department = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    can_create_schedule = db.Column(db.Boolean, default=False)  # Admin controlled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    schedules = db.relationship('Schedule', backref='creator', lazy=True, foreign_keys='Schedule.creator_id')
    events = db.relationship('Event', backref='organizer', lazy=True, foreign_keys='Event.organizer_id')
    approvals = db.relationship('EventApproval', backref='approver', lazy=True, foreign_keys='EventApproval.approver_id')
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def get_auth_token(self, expires_in=86400):
        """Generate JWT token for authentication (default 24 hours)"""
        payload = {
            'user_id': self.id,
            'email': self.email,
            'role': self.role,
            'exp': datetime.utcnow() + timedelta(seconds=expires_in)
        }
        return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')

    def to_dict(self):
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'role': self.role,
            'department': self.department,
            'can_create_schedule': self.can_create_schedule,
            'created_at': self.created_at.isoformat()
        }


class Schedule(db.Model):
    """Schedule model for student and teacher personal schedules"""
    __tablename__ = 'schedules'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    is_class_schedule = db.Column(db.Boolean, default=False)  # False = event schedule
    color = db.Column(db.String(7), default='#3b82f6')  # Hex color code
    is_public = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    events = db.relationship('Event', backref='schedule', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        """Convert schedule to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'description': self.description,
            'is_class_schedule': self.is_class_schedule,
            'color': self.color,
            'is_public': self.is_public,
            'events_count': len(self.events),
            'created_at': self.created_at.isoformat()
        }


class Event(db.Model):
    """Event model for scheduled classes or events"""
    __tablename__ = 'events'
    
    id = db.Column(db.Integer, primary_key=True)
    schedule_id = db.Column(db.Integer, db.ForeignKey('schedules.id'), nullable=False)
    organizer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    start_time = db.Column(db.DateTime, nullable=False, index=True)
    end_time = db.Column(db.DateTime, nullable=False, index=True)
    room_number = db.Column(db.String(50))
    building = db.Column(db.String(100))
    location = db.Column(db.String(255))  # Full address
    color = db.Column(db.String(7), default='#3b82f6')
    is_recurring = db.Column(db.Boolean, default=False)
    recurrence_pattern = db.Column(db.String(50))  # daily, weekly, monthly
    recurrence_end_date = db.Column(db.DateTime)
    requires_approval = db.Column(db.Boolean, default=False)
    approval_status = db.Column(db.String(20), default='pending')  # pending, approved, declined
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    approvals = db.relationship('EventApproval', backref='event', lazy=True, cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='event', lazy=True, cascade='all, delete-orphan')
    
    def check_overlap(self):
        """Check if this event overlaps with other events in the same schedule"""
        overlapping = Event.query.filter(
            Event.schedule_id == self.schedule_id,
            Event.id != self.id,
            Event.start_time < self.end_time,
            Event.end_time > self.start_time
        ).first()
        return overlapping
    
    def to_dict(self):
        """Convert event to dictionary"""
        return {
            'id': self.id,
            'schedule_id': self.schedule_id,
            'organizer_id': self.organizer_id,
            'title': self.title,
            'description': self.description,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'room_number': self.room_number,
            'building': self.building,
            'location': self.location,
            'color': self.color,
            'is_recurring': self.is_recurring,
            'recurrence_pattern': self.recurrence_pattern,
            'requires_approval': self.requires_approval,
            'approval_status': self.approval_status,
            'created_at': self.created_at.isoformat()
        }


class EventApproval(db.Model):
    """Event approval model for admin approval workflow"""
    __tablename__ = 'event_approvals'
    
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    approver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved, declined
    reason = db.Column(db.Text)  # Reason for approval or decline
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert approval to dictionary"""
        return {
            'id': self.id,
            'event_id': self.event_id,
            'approver_id': self.approver_id,
            'status': self.status,
            'reason': self.reason,
            'updated_at': self.updated_at.isoformat()
        }


class Notification(db.Model):
    """Notification model for email and in-app notifications"""
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'))
    type = db.Column(db.String(50))  # approval, decline, reminder, update
    message = db.Column(db.Text)
    is_read = db.Column(db.Boolean, default=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert notification to dictionary"""
        return {
            'id': self.id,
            'type': self.type,
            'message': self.message,
            'is_read': self.is_read,
            'sent_at': self.sent_at.isoformat()
        }


# ==================== AUTHENTICATION MIDDLEWARE ====================

def token_required(f):
    """Decorator to require valid JWT token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Check for token in headers
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({'error': 'Invalid token format'}), 401
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = User.query.get(payload['user_id'])
            if not current_user:
                return jsonify({'error': 'User not found'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated


def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated(current_user, *args, **kwargs):
        if current_user.role != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        return f(current_user, *args, **kwargs)
    return decorated


# ==================== AUTHENTICATION ROUTES ====================

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register a new user"""
    data = request.get_json()
    
    # Validate required fields
    if not all(k in data for k in ['email', 'password', 'first_name', 'last_name']):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Check if user already exists
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 400
    
    try:
        # Create new user
        user = User(
            email=data['email'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            role=data.get('role', 'student'),  # Default to student
            department=data.get('department')
        )
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.commit()
        
        # Generate auth token
        token = user.get_auth_token()
        
        return jsonify({
            'message': 'User registered successfully',
            'user': user.to_dict(),
            'token': token
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login user with email and password"""
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Missing email or password'}), 400
    
    user = User.query.filter_by(email=data['email']).first()
    
    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid email or password'}), 401
    
    if not user.is_active:
        return jsonify({'error': 'User account is inactive'}), 403
    
    token = user.get_auth_token()
    
    return jsonify({
        'message': 'Login successful',
        'user': user.to_dict(),
        'token': token
    }), 200


@app.route('/api/auth/verify', methods=['GET'])
@token_required
def verify_token(current_user):
    """Verify JWT token and return current user"""
    return jsonify({
        'user': current_user.to_dict(),
        'valid': True
    }), 200


# ==================== USER MANAGEMENT ROUTES ====================

@app.route('/api/users/<int:user_id>', methods=['GET'])
@token_required
def get_user(current_user, user_id):
    """Get user profile"""
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify(user.to_dict()), 200


@app.route('/api/users/<int:user_id>/permission', methods=['PUT'])
@token_required
@admin_required
def update_user_permission(current_user, user_id):
    """Admin endpoint to allow/revoke schedule creation permissions"""
    data = request.get_json()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    user.can_create_schedule = data.get('can_create_schedule', user.can_create_schedule)
    db.session.commit()
    
    return jsonify({
        'message': 'User permissions updated',
        'user': user.to_dict()
    }), 200


@app.route('/api/users', methods=['GET'])
@token_required
@admin_required
def list_users(current_user):
    """Admin endpoint to list all users"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    users = User.query.paginate(page=page, per_page=per_page)
    
    return jsonify({
        'total': users.total,
        'pages': users.pages,
        'current_page': page,
        'users': [u.to_dict() for u in users.items]
    }), 200


# ==================== SCHEDULE ROUTES ====================

@app.route('/api/schedules', methods=['POST'])
@token_required
def create_schedule(current_user):
    """Create a new schedule"""
    if not current_user.can_create_schedule and current_user.role != 'admin':
        return jsonify({'error': 'You do not have permission to create schedules'}), 403
    
    data = request.get_json()
    
    if not data.get('title'):
        return jsonify({'error': 'Title is required'}), 400
    
    try:
        schedule = Schedule(
            user_id=current_user.id,
            creator_id=current_user.id,
            title=data['title'],
            description=data.get('description'),
            is_class_schedule=data.get('is_class_schedule', False),
            color=data.get('color', '#3b82f6'),
            is_public=data.get('is_public', False)
        )
        
        db.session.add(schedule)
        db.session.commit()
        
        return jsonify({
            'message': 'Schedule created successfully',
            'schedule': schedule.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/schedules', methods=['GET'])
@token_required
def get_user_schedules(current_user):
    """Get all schedules for current user"""
    schedules = Schedule.query.filter_by(user_id=current_user.id).all()
    
    return jsonify({
        'schedules': [s.to_dict() for s in schedules]
    }), 200


@app.route('/api/schedules/<int:schedule_id>', methods=['GET'])
@token_required
def get_schedule(current_user, schedule_id):
    """Get schedule details with events"""
    schedule = Schedule.query.get(schedule_id)
    
    if not schedule:
        return jsonify({'error': 'Schedule not found'}), 404
    
    # Check permission
    if schedule.user_id != current_user.id and current_user.role != 'admin':
        if not schedule.is_public:
            return jsonify({'error': 'Access denied'}), 403
    
    schedule_data = schedule.to_dict()
    schedule_data['events'] = [e.to_dict() for e in schedule.events]
    
    return jsonify(schedule_data), 200


@app.route('/api/schedules/<int:schedule_id>', methods=['PUT'])
@token_required
def update_schedule(current_user, schedule_id):
    """Update schedule details"""
    schedule = Schedule.query.get(schedule_id)
    
    if not schedule:
        return jsonify({'error': 'Schedule not found'}), 404
    
    if schedule.user_id != current_user.id and current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    
    schedule.title = data.get('title', schedule.title)
    schedule.description = data.get('description', schedule.description)
    schedule.color = data.get('color', schedule.color)
    schedule.is_public = data.get('is_public', schedule.is_public)
    
    db.session.commit()
    
    return jsonify({
        'message': 'Schedule updated successfully',
        'schedule': schedule.to_dict()
    }), 200


@app.route('/api/schedules/<int:schedule_id>', methods=['DELETE'])
@token_required
def delete_schedule(current_user, schedule_id):
    """Delete schedule and all associated events"""
    schedule = Schedule.query.get(schedule_id)
    
    if not schedule:
        return jsonify({'error': 'Schedule not found'}), 404
    
    if schedule.user_id != current_user.id and current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    db.session.delete(schedule)
    db.session.commit()
    
    return jsonify({'message': 'Schedule deleted successfully'}), 200


# ==================== EVENT ROUTES ====================

@app.route('/api/events', methods=['POST'])
@token_required
def create_event(current_user):
    """Create a new event in a schedule"""
    data = request.get_json()
    schedule_id = data.get('schedule_id')
    
    # Verify schedule ownership
    schedule = Schedule.query.get(schedule_id)
    if not schedule or (schedule.user_id != current_user.id and current_user.role != 'admin'):
        return jsonify({'error': 'Access denied'}), 403
    
    # Validate required fields
    if not all(k in data for k in ['title', 'start_time', 'end_time']):
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        start_time = datetime.fromisoformat(data['start_time'])
        end_time = datetime.fromisoformat(data['end_time'])
        
        # Validate time range
        if start_time >= end_time:
            return jsonify({'error': 'End time must be after start time'}), 400
        
        event = Event(
            schedule_id=schedule_id,
            organizer_id=current_user.id,
            title=data['title'],
            description=data.get('description'),
            start_time=start_time,
            end_time=end_time,
            room_number=data.get('room_number'),
            building=data.get('building'),
            location=data.get('location'),
            color=data.get('color', '#3b82f6'),
            is_recurring=data.get('is_recurring', False),
            recurrence_pattern=data.get('recurrence_pattern'),
            recurrence_end_date=datetime.fromisoformat(data['recurrence_end_date']) if data.get('recurrence_end_date') else None,
            requires_approval=data.get('requires_approval', False)
        )
        
        # Check for overlaps
        overlap = event.check_overlap()
        if overlap:
            return jsonify({
                'error': 'Event overlaps with existing event',
                'overlap_event': overlap.to_dict()
            }), 409
        
        db.session.add(event)
        db.session.commit()
        
        return jsonify({
            'message': 'Event created successfully',
            'event': event.to_dict()
        }), 201
    
    except ValueError as e:
        return jsonify({'error': f'Invalid datetime format: {str(e)}'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/events/<int:event_id>', methods=['GET'])
@token_required
def get_event(current_user, event_id):
    """Get event details"""
    event = Event.query.get(event_id)
    
    if not event:
        return jsonify({'error': 'Event not found'}), 404
    
    # Check permission
    if event.schedule.user_id != current_user.id and current_user.role != 'admin':
        if not event.schedule.is_public:
            return jsonify({'error': 'Access denied'}), 403
    
    return jsonify(event.to_dict()), 200


@app.route('/api/events/<int:event_id>', methods=['PUT'])
@token_required
def update_event(current_user, event_id):
    """Update event details"""
    event = Event.query.get(event_id)
    
    if not event:
        return jsonify({'error': 'Event not found'}), 404
    
    if event.organizer_id != current_user.id and current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    
    # Update fields
    if 'title' in data:
        event.title = data['title']
    if 'description' in data:
        event.description = data['description']
    if 'start_time' in data:
        event.start_time = datetime.fromisoformat(data['start_time'])
    if 'end_time' in data:
        event.end_time = datetime.fromisoformat(data['end_time'])
    if 'room_number' in data:
        event.room_number = data['room_number']
    if 'building' in data:
        event.building = data['building']
    if 'location' in data:
        event.location = data['location']
    if 'color' in data:
        event.color = data['color']
    
    # Check for overlaps after update
    overlap = event.check_overlap()
    if overlap:
        db.session.rollback()
        return jsonify({
            'error': 'Event overlaps with existing event',
            'overlap_event': overlap.to_dict()
        }), 409
    
    db.session.commit()
    
    return jsonify({
        'message': 'Event updated successfully',
        'event': event.to_dict()
    }), 200


@app.route('/api/events/<int:event_id>', methods=['DELETE'])
@token_required
def delete_event(current_user, event_id):
    """Delete event"""
    event = Event.query.get(event_id)
    
    if not event:
        return jsonify({'error': 'Event not found'}), 404
    
    if event.organizer_id != current_user.id and current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    db.session.delete(event)
    db.session.commit()
    
    return jsonify({'message': 'Event deleted successfully'}), 200


# ==================== ERROR HANDLING ====================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Resource not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
