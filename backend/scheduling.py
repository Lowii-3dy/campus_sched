"""
Advanced Scheduling Module
Handles event scheduling, overlap detection, and conflict resolution
"""

from datetime import datetime, timedelta
from app import db, Event, Schedule
from sqlalchemy import and_, or_

class SchedulingManager:
    """Manages all scheduling operations with conflict detection"""
    
    @staticmethod
    def check_overlap(event, exclude_event_id=None):
        """
        Check if an event overlaps with existing events in the same schedule
        Returns the conflicting event or None if no conflict
        
        Comprehensive overlap detection algorithm
        """
        query = Event.query.filter(
            Event.schedule_id == event.schedule_id,
            Event.id != (exclude_event_id or event.id),
            # Check if time ranges overlap
            Event.start_time < event.end_time,
            Event.end_time > event.start_time
        )
        
        return query.first()
    
    @staticmethod
    def check_overlaps_for_user(user_id, start_time, end_time, exclude_schedule_id=None):
        """
        Check if user has overlapping events across all their schedules
        Useful for personal schedule conflicts
        
        User-wide overlap detection
        """
        schedules = Schedule.query.filter_by(user_id=user_id).all()
        schedule_ids = [s.id for s in schedules]
        
        if not schedule_ids:
            return None
        
        conflicting_event = Event.query.filter(
            Event.schedule_id.in_(schedule_ids),
            Event.start_time < end_time,
            Event.end_time > start_time
        ).first()
        
        return conflicting_event
    
    @staticmethod
    def get_facility_availability(building, room_number, start_time, end_time, exclude_event_id=None):
        """
        Check facility availability for a given time slot
        Returns list of conflicting events if any
        
        Facility booking conflict detection
        """
        conflicts = Event.query.filter(
            Event.building == building,
            Event.room_number == room_number,
            Event.id != (exclude_event_id or 0),
            Event.start_time < end_time,
            Event.end_time > start_time
        ).all()
        
        return conflicts
    
    @staticmethod
    def suggest_alternative_times(event, duration_minutes=None):
        """
        Suggest alternative time slots for an event
        Returns list of available time slots
        
        Smart scheduling suggestions
        """
        if not duration_minutes:
            duration_minutes = int((event.end_time - event.start_time).total_seconds() / 60)
        
        alternatives = []
        current_time = event.start_time
        
        # Check next 7 days
        for day_offset in range(7):
            check_date = event.start_time.replace(day=event.start_time.day + day_offset)
            
            # Try different times: 8 AM to 6 PM in 30-min slots
            for hour in range(8, 18):
                for minute in [0, 30]:
                    start = check_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    end = start + timedelta(minutes=duration_minutes)
                    
                    # Check if slot is available
                    conflict = Event.query.filter(
                        Event.schedule_id == event.schedule_id,
                        Event.id != event.id,
                        Event.start_time < end,
                        Event.end_time > start
                    ).first()
                    
                    if not conflict:
                        alternatives.append({
                            'start_time': start.isoformat(),
                            'end_time': end.isoformat(),
                            'day_of_week': check_date.strftime('%A')
                        })
                        
                        if len(alternatives) >= 5:
                            return alternatives
        
        return alternatives
    
    @staticmethod
    def get_daily_schedule(user_id, date):
        """
        Get user's complete daily schedule for a specific date
        Returns sorted list of events for that day
        
        Daily schedule aggregation
        """
        schedules = Schedule.query.filter_by(user_id=user_id).all()
        
        events = Event.query.filter(
            Event.schedule_id.in_([s.id for s in schedules]),
            db.func.date(Event.start_time) == date.date()
        ).order_by(Event.start_time).all()
        
        return events
    
    @staticmethod
    def get_weekly_schedule(user_id, start_date):
        """
        Get user's complete weekly schedule
        Returns organized dict of events by day
        
        Weekly schedule aggregation
        """
        schedules = Schedule.query.filter_by(user_id=user_id).all()
        schedule_ids = [s.id for s in schedules]
        
        end_date = start_date + timedelta(days=7)
        
        events = Event.query.filter(
            Event.schedule_id.in_(schedule_ids),
            Event.start_time >= start_date,
            Event.start_time < end_date
        ).order_by(Event.start_time).all()
        
        # Organize by day
        weekly_schedule = {}
        for i in range(7):
            day = start_date + timedelta(days=i)
            weekly_schedule[day.strftime('%A')] = []
        
        for event in events:
            day_key = event.start_time.strftime('%A')
            if day_key in weekly_schedule:
                weekly_schedule[day_key].append(event.to_dict())
        
        return weekly_schedule
    
    @staticmethod
    def find_common_time_slot(user_ids, duration_minutes, min_date=None, max_date=None):
        """
        Find common available time slots for multiple users
        Useful for scheduling group meetings or classes
        
        Group scheduling algorithm
        """
        if not min_date:
            min_date = datetime.utcnow()
        if not max_date:
            max_date = min_date + timedelta(days=14)
        
        common_slots = []
        
        # Check each hour for 14 days
        current = min_date.replace(hour=8, minute=0, second=0, microsecond=0)
        
        while current < max_date:
            slot_end = current + timedelta(minutes=duration_minutes)
            
            # Check if slot is free for all users
            all_free = True
            for user_id in user_ids:
                conflict = SchedulingManager.check_overlaps_for_user(
                    user_id, current, slot_end
                )
                if conflict:
                    all_free = False
                    break
            
            if all_free:
                common_slots.append({
                    'start_time': current.isoformat(),
                    'end_time': slot_end.isoformat(),
                    'day': current.strftime('%A, %B %d')
                })
                
                if len(common_slots) >= 5:
                    return common_slots
            
            current += timedelta(hours=1)
        
        return common_slots
    
    @staticmethod
    def validate_event_chain(events):
        """
        Validate a chain of recurring events to ensure no overlaps
        
        Recurring event validation
        """
        events = sorted(events, key=lambda e: e.start_time)
        
        for i in range(len(events) - 1):
            if events[i].end_time > events[i + 1].start_time:
                return False, events[i + 1]
        
        return True, None


class ConflictResolution:
    """Handles conflict resolution and notifications"""
    
    @staticmethod
    def resolve_overlap_conflict(primary_event, conflicting_event):
        """
        Suggest resolution strategies for conflicting events
        Returns list of possible actions
        
        Conflict resolution strategies
        """
        strategies = []
        
        # Strategy 1: Move primary event to suggested time
        alternatives = SchedulingManager.suggest_alternative_times(primary_event)
        if alternatives:
            strategies.append({
                'action': 'reschedule',
                'event': 'primary',
                'suggestions': alternatives[:3]
            })
        
        # Strategy 2: Move conflicting event
        alternatives = SchedulingManager.suggest_alternative_times(conflicting_event)
        if alternatives:
            strategies.append({
                'action': 'reschedule',
                'event': 'conflicting',
                'suggestions': alternatives[:3]
            })
        
        # Strategy 3: Accept overlap (if both are optional)
        if not primary_event.requires_approval:
            strategies.append({
                'action': 'accept_overlap',
                'warning': 'This will create a time conflict'
            })
        
        return strategies
    
    @staticmethod
    def generate_conflict_report(user_id):
        """
        Generate a report of all conflicts in user's schedules
        
        Comprehensive conflict reporting
        """
        schedules = Schedule.query.filter_by(user_id=user_id).all()
        conflicts = []
        
        for schedule in schedules:
            events = Event.query.filter_by(schedule_id=schedule.id)\
                .order_by(Event.start_time).all()
            
            for i, event1 in enumerate(events):
                for event2 in events[i+1:]:
                    if event1.start_time < event2.end_time and event1.end_time > event2.start_time:
                        conflicts.append({
                            'event1': event1.to_dict(),
                            'event2': event2.to_dict(),
                            'schedule': schedule.title,
                            'overlap_duration': min(
                                event1.end_time, event2.end_time
                            ) - max(event1.start_time, event2.start_time)
                        })
        
        return conflicts


# Export scheduling functions
def check_event_overlap(event_id, schedule_id, start_time, end_time):
    """API wrapper for overlap detection"""
    conflict = Event.query.filter(
        Event.schedule_id == schedule_id,
        Event.id != event_id,
        Event.start_time < end_time,
        Event.end_time > start_time
    ).first()
    return conflict


def get_schedule_conflicts(schedule_id):
    """Get all conflicts within a schedule"""
    events = Event.query.filter_by(schedule_id=schedule_id)\
        .order_by(Event.start_time).all()
    
    conflicts = []
    for i, e1 in enumerate(events):
        for e2 in events[i+1:]:
            if e1.start_time < e2.end_time and e1.end_time > e2.start_time:
                conflicts.append((e1, e2))
    
    return conflicts
