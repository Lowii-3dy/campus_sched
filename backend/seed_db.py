"""
Database seeding script for Campus Scheduler
Populates database with sample users and schedules for testing
"""

from app import app, db, User, Schedule, Event
from datetime import datetime, timedelta

def seed_database():
    """Create sample data for testing"""
    with app.app_context():
        # Clear existing data
        db.drop_all()
        db.create_all()
        
        print("Creating sample users...")
        
        # Create admin user
        admin = User(
            email='admin@campus.edu',
            first_name='Admin',
            last_name='User',
            role='admin',
            department='Administration',
            is_active=True,
            can_create_schedule=True
        )
        admin.set_password('admin123')
        
        # Create teachers
        teacher1 = User(
            email='teacher1@campus.edu',
            first_name='John',
            last_name='Smith',
            role='teacher',
            department='Computer Science',
            is_active=True,
            can_create_schedule=True
        )
        teacher1.set_password('teacher123')
        
        teacher2 = User(
            email='teacher2@campus.edu',
            first_name='Jane',
            last_name='Doe',
            role='teacher',
            department='Mathematics',
            is_active=True,
            can_create_schedule=True
        )
        teacher2.set_password('teacher123')
        
        # Create students
        student1 = User(
            email='student1@campus.edu',
            first_name='Alice',
            last_name='Johnson',
            role='student',
            department='Computer Science',
            is_active=True,
            can_create_schedule=False
        )
        student1.set_password('student123')
        
        student2 = User(
            email='student2@campus.edu',
            first_name='Bob',
            last_name='Williams',
            role='student',
            department='Mathematics',
            is_active=True,
            can_create_schedule=False
        )
        student2.set_password('student123')
        
        db.session.add_all([admin, teacher1, teacher2, student1, student2])
        db.session.commit()
        
        print("Creating sample schedules...")
        
        # Create class schedule for teacher1
        cs_schedule = Schedule(
            user_id=teacher1.id,
            creator_id=teacher1.id,
            title='CS101 - Introduction to Programming',
            description='Fall 2024 Class Schedule',
            is_class_schedule=True,
            color='#3b82f6',
            is_public=True
        )
        
        # Create event schedule for student1
        student_schedule = Schedule(
            user_id=student1.id,
            creator_id=student1.id,
            title='My Class Schedule',
            description='Personal class schedule',
            is_class_schedule=False,
            color='#10b981',
            is_public=False
        )
        
        db.session.add_all([cs_schedule, student_schedule])
        db.session.commit()
        
        print("Creating sample events...")
        
        # Create events for class schedule
        now = datetime.utcnow()
        monday = now.replace(hour=9, minute=0, second=0, microsecond=0)
        
        event1 = Event(
            schedule_id=cs_schedule.id,
            organizer_id=teacher1.id,
            title='Lecture: Python Basics',
            description='Introduction to Python programming language',
            start_time=monday,
            end_time=monday + timedelta(hours=1, minutes=30),
            room_number='101',
            building='Science Hall',
            location='Science Hall Room 101',
            color='#3b82f6',
            is_recurring=True,
            recurrence_pattern='weekly',
            recurrence_end_date=now + timedelta(days=120)
        )
        
        event2 = Event(
            schedule_id=cs_schedule.id,
            organizer_id=teacher1.id,
            title='Lecture: Data Structures',
            description='Understanding arrays, lists, and trees',
            start_time=monday + timedelta(days=2, hours=10),
            end_time=monday + timedelta(days=2, hours=11, minutes=30),
            room_number='102',
            building='Science Hall',
            location='Science Hall Room 102',
            color='#0ea5e9',
            is_recurring=True,
            recurrence_pattern='weekly',
            recurrence_end_date=now + timedelta(days=120)
        )
        
        db.session.add_all([event1, event2])
        db.session.commit()
        
        print("Database seeding completed successfully!")
        print("\nSample credentials for testing:")
        print("Admin: admin@campus.edu / admin123")
        print("Teacher: teacher1@campus.edu / teacher123")
        print("Student: student1@campus.edu / student123")

if __name__ == '__main__':
    seed_database()
