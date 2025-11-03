"""
Email Service Module
Handles all email notifications for the Campus Scheduler
Supports event approvals, schedule updates, and reminders
"""

from flask_mail import Mail, Message
from datetime import datetime, timedelta
from app import db, User, Event, Schedule
import os
from functools import wraps

mail = Mail()

class EmailService:
    """Centralized email service for all notifications"""
    
    # Email templates
    EMAIL_TEMPLATES = {
        'approval': {
            'subject': 'Event Approved: {event_title}',
            'template': 'email_templates/event_approved.html'
        },
        'decline': {
            'subject': 'Event Declined: {event_title}',
            'template': 'email_templates/event_declined.html'
        },
        'changes_requested': {
            'subject': 'Changes Requested: {event_title}',
            'template': 'email_templates/changes_requested.html'
        },
        'event_reminder': {
            'subject': 'Reminder: {event_title} is coming up',
            'template': 'email_templates/event_reminder.html'
        },
        'schedule_shared': {
            'subject': '{user_name} shared a schedule with you',
            'template': 'email_templates/schedule_shared.html'
        },
        'new_pending_approval': {
            'subject': 'New Event Requires Approval: {event_title}',
            'template': 'email_templates/admin_pending_approval.html'
        }
    }
    
    @staticmethod
    def send_approval_email(recipient_email, event, status, reason=''):
        """
        Send approval/decline email to event organizer
        
        Event approval notification emails
        """
        event_dict = event.to_dict() if hasattr(event, 'to_dict') else event
        
        if status == 'approved':
            subject = f'Event Approved: {event_dict["title"]}'
            html_body = EmailService._build_approval_email(event_dict, reason)
        else:
            subject = f'Event Declined: {event_dict["title"]}'
            html_body = EmailService._build_decline_email(event_dict, reason)
        
        try:
            msg = Message(
                subject=subject,
                recipients=[recipient_email],
                html=html_body
            )
            mail.send(msg)
            return True
        except Exception as e:
            print(f'Error sending approval email: {e}')
            return False
    
    @staticmethod
    def send_changes_request_email(recipient_email, event, reason):
        """
        Send email requesting changes to event
        
        Changes request notification
        """
        event_dict = event.to_dict() if hasattr(event, 'to_dict') else event
        subject = f'Changes Requested: {event_dict["title"]}'
        html_body = EmailService._build_changes_request_email(event_dict, reason)
        
        try:
            msg = Message(
                subject=subject,
                recipients=[recipient_email],
                html=html_body
            )
            mail.send(msg)
            return True
        except Exception as e:
            print(f'Error sending changes request email: {e}')
            return False
    
    @staticmethod
    def send_event_reminder(recipient_email, event, hours_before=24):
        """
        Send reminder email before event
        
        Event reminder notifications
        """
        event_dict = event.to_dict() if hasattr(event, 'to_dict') else event
        subject = f'Reminder: {event_dict["title"]} is coming up'
        html_body = EmailService._build_reminder_email(event_dict, hours_before)
        
        try:
            msg = Message(
                subject=subject,
                recipients=[recipient_email],
                html=html_body
            )
            mail.send(msg)
            return True
        except Exception as e:
            print(f'Error sending reminder email: {e}')
            return False
    
    @staticmethod
    def send_admin_pending_approval_email(admin_email, event):
        """
        Send notification to admin about pending approval
        
        Admin pending approval notifications
        """
        event_dict = event.to_dict() if hasattr(event, 'to_dict') else event
        subject = f'New Event Requires Approval: {event_dict["title"]}'
        html_body = EmailService._build_admin_approval_email(event_dict)
        
        try:
            msg = Message(
                subject=subject,
                recipients=[admin_email],
                html=html_body
            )
            mail.send(msg)
            return True
        except Exception as e:
            print(f'Error sending admin email: {e}')
            return False
    
    @staticmethod
    def send_schedule_shared_email(recipient_email, schedule, shared_by_user):
        """
        Send email when schedule is shared with user
        
        Schedule sharing notifications
        """
        schedule_dict = schedule.to_dict() if hasattr(schedule, 'to_dict') else schedule
        user_dict = shared_by_user.to_dict() if hasattr(shared_by_user, 'to_dict') else shared_by_user
        
        subject = f'{user_dict["first_name"]} {user_dict["last_name"]} shared a schedule with you'
        html_body = EmailService._build_schedule_shared_email(schedule_dict, user_dict)
        
        try:
            msg = Message(
                subject=subject,
                recipients=[recipient_email],
                html=html_body
            )
            mail.send(msg)
            return True
        except Exception as e:
            print(f'Error sending schedule shared email: {e}')
            return False
    
    @staticmethod
    def send_batch_reminders():
        """
        Send event reminders for events happening in next 24 hours
        Should be called by scheduler/cron job
        
        Batch reminder processing
        """
        now = datetime.utcnow()
        reminder_time = now + timedelta(hours=24)
        
        # Find all events in next 24 hours
        upcoming_events = Event.query.filter(
            Event.start_time >= now,
            Event.start_time <= reminder_time
        ).all()
        
        sent_count = 0
        for event in upcoming_events:
            organizer = event.organizer
            if EmailService.send_event_reminder(
                organizer.email,
                event,
                hours_before=24
            ):
                sent_count += 1
        
        return {'sent': sent_count, 'total_events': len(upcoming_events)}
    
    # ==================== EMAIL BUILDERS ====================
    
    @staticmethod
    def _build_approval_email(event, reason=''):
        """Build HTML for approval email"""
        start_time = datetime.fromisoformat(event['start_time'])
        start_formatted = start_time.strftime('%B %d, %Y at %I:%M %p')
        
        return f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333; background-color: #f5f5f5;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: white; border-radius: 8px;">
                    <h2 style="color: #10b981;">Event Approved!</h2>
                    
                    <p>Your event has been approved and is now confirmed.</p>
                    
                    <div style="background-color: #f0fdf4; border-left: 4px solid #10b981; padding: 15px; margin: 20px 0;">
                        <h3 style="margin-top: 0;">{event['title']}</h3>
                        <p><strong>Date & Time:</strong> {start_formatted}</p>
                        <p><strong>Location:</strong> {event.get('location', event.get('building', 'TBA'))}</p>
                        {f'<p><strong>Details:</strong> {reason}</p>' if reason else ''}
                    </div>
                    
                    <p>Your event is now visible in the schedule and available to all users.</p>
                    
                    <p style="color: #666; font-size: 0.9em;">
                        <a href="https://campusscheduler.edu/dashboard">View in Dashboard</a>
                    </p>
                </div>
            </body>
        </html>
        """
    
    @staticmethod
    def _build_decline_email(event, reason):
        """Build HTML for decline email"""
        start_time = datetime.fromisoformat(event['start_time'])
        start_formatted = start_time.strftime('%B %d, %Y at %I:%M %p')
        
        return f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333; background-color: #f5f5f5;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: white; border-radius: 8px;">
                    <h2 style="color: #ef4444;">Event Declined</h2>
                    
                    <p>Your event request has been reviewed and declined.</p>
                    
                    <div style="background-color: #fef2f2; border-left: 4px solid #ef4444; padding: 15px; margin: 20px 0;">
                        <h3 style="margin-top: 0;">{event['title']}</h3>
                        <p><strong>Date & Time:</strong> {start_formatted}</p>
                        <p><strong>Location:</strong> {event.get('location', event.get('building', 'TBA'))}</p>
                        <p><strong>Reason:</strong> {reason}</p>
                    </div>
                    
                    <p>Please contact administration if you have questions about this decision.</p>
                    
                    <p style="color: #666; font-size: 0.9em;">
                        <a href="https://campusscheduler.edu/support">Contact Support</a>
                    </p>
                </div>
            </body>
        </html>
        """
    
    @staticmethod
    def _build_changes_request_email(event, reason):
        """Build HTML for changes request email"""
        return f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333; background-color: #f5f5f5;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: white; border-radius: 8px;">
                    <h2 style="color: #f59e0b;">Changes Requested</h2>
                    
                    <p>Your event "{event['title']}" requires changes before approval.</p>
                    
                    <div style="background-color: #fffbeb; border-left: 4px solid #f59e0b; padding: 15px; margin: 20px 0;">
                        <p><strong>Required Changes:</strong></p>
                        <p>{reason}</p>
                    </div>
                    
                    <p>Please make the necessary modifications and resubmit your event for approval.</p>
                    
                    <p style="color: #666; font-size: 0.9em;">
                        <a href="https://campusscheduler.edu/events/{event.get('id', '')}/edit">Edit Event</a>
                    </p>
                </div>
            </body>
        </html>
        """
    
    @staticmethod
    def _build_reminder_email(event, hours_before):
        """Build HTML for event reminder email"""
        start_time = datetime.fromisoformat(event['start_time'])
        start_formatted = start_time.strftime('%B %d, %Y at %I:%M %p')
        
        return f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333; background-color: #f5f5f5;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: white; border-radius: 8px;">
                    <h2 style="color: #3b82f6;">Event Reminder</h2>
                    
                    <p>Your event is coming up in {hours_before} hours!</p>
                    
                    <div style="background-color: #eff6ff; border-left: 4px solid #3b82f6; padding: 15px; margin: 20px 0;">
                        <h3 style="margin-top: 0;">{event['title']}</h3>
                        <p><strong>Date & Time:</strong> {start_formatted}</p>
                        <p><strong>Location:</strong> {event.get('location', event.get('building', 'TBA'))}</p>
                        {f'<p><strong>Room:</strong> {event.get("room_number", "")}</p>' if event.get('room_number') else ''}
                    </div>
                    
                    <p style="color: #666; font-size: 0.9em;">
                        <a href="https://campusscheduler.edu/dashboard">View Event Details</a>
                    </p>
                </div>
            </body>
        </html>
        """
    
    @staticmethod
    def _build_admin_approval_email(event):
        """Build HTML for admin approval notification"""
        start_time = datetime.fromisoformat(event['start_time'])
        start_formatted = start_time.strftime('%B %d, %Y at %I:%M %p')
        
        return f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333; background-color: #f5f5f5;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: white; border-radius: 8px;">
                    <h2 style="color: #3b82f6;">New Event Requires Approval</h2>
                    
                    <p>A new event has been submitted and requires your review.</p>
                    
                    <div style="background-color: #eff6ff; border-left: 4px solid #3b82f6; padding: 15px; margin: 20px 0;">
                        <h3 style="margin-top: 0;">{event['title']}</h3>
                        <p><strong>Date & Time:</strong> {start_formatted}</p>
                        <p><strong>Location:</strong> {event.get('location', event.get('building', 'TBA'))}</p>
                        <p><strong>Description:</strong> {event.get('description', 'No description')}</p>
                    </div>
                    
                    <p style="color: #666; font-size: 0.9em;">
                        <a href="https://campusscheduler.edu/admin/approvals">Review in Admin Panel</a>
                    </p>
                </div>
            </body>
        </html>
        """
    
    @staticmethod
    def _build_schedule_shared_email(schedule, shared_by_user):
        """Build HTML for schedule shared notification"""
        return f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333; background-color: #f5f5f5;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: white; border-radius: 8px;">
                    <h2 style="color: #10b981;">Schedule Shared</h2>
                    
                    <p>{shared_by_user['first_name']} {shared_by_user['last_name']} shared a schedule with you.</p>
                    
                    <div style="background-color: #f0fdf4; border-left: 4px solid #10b981; padding: 15px; margin: 20px 0;">
                        <h3 style="margin-top: 0;">{schedule['title']}</h3>
                        <p>{schedule.get('description', '')}</p>
                        <p><strong>Type:</strong> {'Class Schedule' if schedule['is_class_schedule'] else 'Event Schedule'}</p>
                    </div>
                    
                    <p style="color: #666; font-size: 0.9em;">
                        <a href="https://campusscheduler.edu/schedules/{schedule.get('id', '')}">View Schedule</a>
                    </p>
                </div>
            </body>
        </html>
        """


# ==================== SCHEDULED EMAIL TASKS ====================

def setup_email_scheduler(app):
    """
    Setup scheduled email tasks
    Should be called on application startup
    
    Scheduled email task configuration
    """
    from apscheduler.schedulers.background import BackgroundScheduler
    
    scheduler = BackgroundScheduler()
    
    # Send reminders every hour
    scheduler.add_job(
        func=EmailService.send_batch_reminders,
        trigger="interval",
        hours=1,
        id='send_reminders',
        name='Send event reminders',
        replace_existing=True
    )
    
    scheduler.start()
    print('Email scheduler started')


# ==================== EMAIL CONFIGURATION ====================

def configure_email(app):
    """Configure email settings from environment variables"""
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', True)
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv(
        'MAIL_DEFAULT_SENDER',
        'noreply@campusscheduler.edu'
    )
    
    mail.init_app(app)
