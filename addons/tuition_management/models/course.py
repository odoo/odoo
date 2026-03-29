# -*- coding: utf-8 -*-
from odoo import api, fields, models


class TuitionTimeSlot(models.Model):
    _name = 'tuition.time.slot'
    _description = 'Tuition Time Slot'
    
    name = fields.Char(string='Time', required=True)
    hour = fields.Integer(string='Hour', required=True, help='Hour (0-23)')
    minute = fields.Integer(string='Minute', required=True, default=0, help='Minute (0-59)')
    
    @api.model
    def create(self, vals):
        if 'hour' in vals and 'minute' in vals:
            vals['name'] = f"{vals['hour']:02d}:{vals['minute']:02d}"
        return super().create(vals)
    
    def write(self, vals):
        if 'hour' in vals or 'minute' in vals:
            hour = vals.get('hour', self.hour)
            minute = vals.get('minute', self.minute)
            vals['name'] = f"{hour:02d}:{minute:02d}"
        return super().write(vals)


class TuitionCourse(models.Model):
    _name = 'tuition.course'
    _description = 'Tuition Course'

    name = fields.Char(required=True)
    code = fields.Char()
    description = fields.Text()
    capacity = fields.Integer()
    active = fields.Boolean(default=True)


class TuitionRegistration(models.Model):
    _name = 'tuition.registration'
    _description = 'Tuition Registration'

    course_id = fields.Many2one('tuition.course', string='Course', required=True)
    partner_id = fields.Many2one('res.partner', string='Student', required=True)
    date = fields.Date(default=fields.Date.context_today)
    state = fields.Selection([('draft', 'Draft'), ('confirmed', 'Confirmed')], default='draft')


class CourseMaster(models.Model):
    _name = 'course.master'
    _description = 'Course Master'

    name = fields.Char(required=True)
    subject_id = fields.Many2one('subject.master', string='Subject', required=True)
    grade_id = fields.Many2one('grade.master', string='Grade', required=True)
    status = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('disabled', 'Disabled')
    ], default='draft', tracking=True)
    start_date = fields.Date()
    end_date = fields.Date()
    tutor_id = fields.Many2one('tutor.profile', string='Tutor')
    coordinator_id = fields.Many2one('res.partner', string='Student Coordinator')
    schedule_ids = fields.One2many('class.schedule', 'course_id', string='Class Schedules')
    enrollment_ids = fields.One2many('course.enrollment', 'course_id', string='Enrollments')

    def action_enroll_student(self):
        """Open enrollment form for this course"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'course.enrollment',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_course_id': self.id,
            }
        }


class CourseEnrollment(models.Model):
    _name = 'course.enrollment'
    _description = 'Course Enrollment'

    name = fields.Char(string='Enrollment Name', required=True)
    course_id = fields.Many2one('course.master', string='Course', required=True, ondelete='cascade')
    student_id = fields.Many2one('student.profile', string='Student', required=True, ondelete='cascade')
    enrollment_date = fields.Date(default=fields.Date.context_today)
    status = fields.Selection([
        ('enrolled', 'Enrolled'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('dropped', 'Dropped')
    ], default='enrolled', tracking=True)
    
    # Fee Details
    fee = fields.Float(string='Fee Amount')
    currency_id = fields.Many2one('res.currency', string='Currency')
    discount_amount = fields.Float(string='Discount Amount')
    net_fee = fields.Float(string='Net Fee', compute='_compute_net_fee', store=True)
    
    # Invoice Options
    invoice_type = fields.Selection([
        ('per_lesson', 'Per Lesson'),
        ('monthly', 'Monthly')
    ], default='monthly', string='Invoice Type')
    billing_cycle = fields.Selection([
        ('weekly', 'Per Week'),
        ('monthly', 'Per Month')
    ], default='monthly', string='Billing Cycle')
    invoice_start_date = fields.Date(string='Invoice Start Date')
    invoice_generation_date = fields.Integer(string='Invoice Generation Date (Day of Month)')

    @api.depends('fee', 'discount_amount')
    def _compute_net_fee(self):
        for rec in self:
            rec.net_fee = rec.fee - rec.discount_amount if rec.fee else 0.0


class Enquiry(models.Model):
    _name = 'enquiry'
    _description = 'Student Enquiry'

    name = fields.Char(required=True)
    partner_id = fields.Many2one('res.partner', string='Contact', required=True, ondelete='cascade')
    email = fields.Char()
    phone = fields.Char()
    subject_id = fields.Many2one('subject.master', string='Interested Subject')
    grade_id = fields.Many2one('grade.master', string='Target Grade')
    enquiry_date = fields.Date(default=fields.Date.context_today)
    status = fields.Selection([
        ('new', 'New'),
        ('demo_scheduled', 'Demo Scheduled'),
        ('completed', 'Completed'),
        ('enrolled', 'Enrolled')
    ], default='new', tracking=True)
    notes = fields.Text()

    def action_schedule_demo(self):
        """Schedule a demo session for this enquiry."""
        self.ensure_one()
        demo_vals = {
            'enquiry_id': self.id,
            'student_name': self.name,
            'subject_id': self.subject_id.id,
            'scheduled_date': fields.Date.context_today(self),
        }
        demo = self.env['demo.session'].create(demo_vals)
        self.status = 'demo_scheduled'
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'demo.session',
            'res_id': demo.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_convert_to_student(self):
        """Convert enquiry to student profile and create enrollment."""
        self.ensure_one()
        # Create or get student profile
        student_profile = self.env['student.profile'].search([('partner_id', '=', self.partner_id.id)])
        if not student_profile:
            student_profile = self.env['student.profile'].create({
                'partner_id': self.partner_id.id,
                'grade_id': self.grade_id.id,
                'subjects_ids': [(6, 0, [self.subject_id.id])] if self.subject_id else [],
            })
        
        # Find course matching subject and grade
        course = self.env['course.master'].search([
            ('subject_id', '=', self.subject_id.id),
            ('grade_id', '=', self.grade_id.id),
            ('status', '=', 'active')
        ], limit=1)
        
        if course:
            # Create enrollment
            enrollment = self.env['course.enrollment'].create({
                'course_id': course.id,
                'student_id': student_profile.id,
                'status': 'enrolled',
            })
            self.status = 'enrolled'
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'course.enrollment',
                'res_id': enrollment.id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            raise models.UserError('No active course found matching the subject and grade.')


class DemoSession(models.Model):
    _name = 'demo.session'
    _description = 'Demo Session'

    enquiry_id = fields.Many2one('enquiry', string='Enquiry', ondelete='cascade')
    student_name = fields.Char(required=True)
    subject_id = fields.Many2one('subject.master', string='Subject', required=True)
    tutor_id = fields.Many2one('tutor.profile', string='Tutor')
    scheduled_date = fields.Date(required=True)
    completed_date = fields.Date()
    status = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], default='scheduled', tracking=True)
    feedback = fields.Text(string='Feedback')
    rating = fields.Integer(string='Rating (1-5)', default=5)

    def action_mark_completed(self):
        """Mark demo session as completed."""
        self.ensure_one()
        self.completed_date = fields.Date.context_today(self)
        self.status = 'completed'
        if self.enquiry_id:
            self.enquiry_id.status = 'completed'


class AttendanceRecord(models.Model):
    _name = 'attendance.record'
    _description = 'Attendance Record'

    class_schedule_id = fields.Many2one('class.schedule', string='Class Schedule', required=True, ondelete='cascade')
    student_id = fields.Many2one('student.profile', string='Student', required=True, ondelete='cascade')
    attendance_date = fields.Date(string='Attendance Date', required=True)
    status = fields.Selection([
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('excused', 'Excused')
    ], default='absent', tracking=True)
    remarks = fields.Text(string='Remarks')

    _sql_constraints = [
        ('unique_attendance', 'UNIQUE(class_schedule_id, student_id, attendance_date)', 'Attendance record already exists for this student on this date.')
    ]

    def action_mark_present(self):
        """Mark attendance as present."""
        self.write({'status': 'present'})

    def action_mark_absent(self):
        """Mark attendance as absent."""
        self.write({'status': 'absent'})

    def action_mark_late(self):
        """Mark attendance as late."""
        self.write({'status': 'late'})

    def action_mark_excused(self):
        """Mark attendance as excused."""
        self.write({'status': 'excused'})


class ClassSchedule(models.Model):
    _name = 'class.schedule'
    _description = 'Class Schedule'

    name = fields.Char(required=True)
    course_id = fields.Many2one('course.master', string='Course', required=True, ondelete='cascade')
    tutor_id = fields.Many2one('tutor.profile', string='Tutor', required=True)
    
    # Schedule Configuration
    schedule_type = fields.Selection([
        ('once_weekly', 'Once a Week'),
        ('twice_weekly', 'Twice a Week'),
        ('weekdays', 'Weekdays (Mon-Fri)'),
        ('daily', 'Every Day')
    ], default='once_weekly', string='Schedule Type', required=True)
    
    # Multiple days selection
    monday = fields.Boolean(string='Monday')
    tuesday = fields.Boolean(string='Tuesday')
    wednesday = fields.Boolean(string='Wednesday')
    thursday = fields.Boolean(string='Thursday')
    friday = fields.Boolean(string='Friday')
    saturday = fields.Boolean(string='Saturday')
    sunday = fields.Boolean(string='Sunday')
    
    # Time fields with hours and minutes
    schedule_hour = fields.Selection([(str(i).zfill(2), str(i).zfill(2)) for i in range(24)], 
                                     string='Hour', required=True, default='09')
    schedule_minute = fields.Selection([(str(i).zfill(2), str(i).zfill(2)) for i in range(0, 60, 5)], 
                                       string='Minute', required=True, default='00')
    schedule_duration = fields.Integer(string='Class Duration (Minutes)', default=60)
    timezone = fields.Selection('_tz_get', string='Timezone', default=lambda self: self.env.user.tz or 'UTC')
    
    # Recurrence settings
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date')
    
    status = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], default='scheduled', tracking=True)

    @staticmethod
    def _tz_get():
        return [(tz, tz) for tz in __import__('pytz').all_timezones]
    
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            record._generate_calendar_events()
        return records
    
    def write(self, vals):
        result = super().write(vals)
        # Regenerate calendar events if schedule details changed
        if any(field in vals for field in ['schedule_type', 'schedule_hour', 'schedule_minute', 'schedule_duration', 
                                              'start_date', 'end_date', 'timezone',
                                              'monday', 'tuesday', 'wednesday', 'thursday', 
                                              'friday', 'saturday', 'sunday']):
            # Delete old events for this schedule
            old_events = self.env['calendar.event'].search([
                ('description', 'ilike', self.name)
            ])
            old_events.unlink()
            # Generate new events
            for record in self:
                record._generate_calendar_events()
        return result
    
    def _generate_calendar_events(self):
        """Generate calendar events based on schedule configuration"""
        from datetime import datetime, timedelta
        import pytz
        
        self.ensure_one()
        
        if not self.start_date:
            return
        
        # Get the days to schedule
        days_to_schedule = self._get_days_to_schedule()
        if not days_to_schedule:
            return
        
        tz = pytz.timezone(self.timezone)
        current_date = datetime.strptime(str(self.start_date), '%Y-%m-%d').date()
        end_date = datetime.strptime(str(self.end_date), '%Y-%m-%d').date() if self.end_date else current_date + timedelta(days=365)
        
        # Get hours and minutes from the selection fields
        hours = int(self.schedule_hour)
        minutes = int(self.schedule_minute)
        
        events_to_create = []
        
        while current_date <= end_date:
            # Check if current day is in the schedule
            day_of_week = current_date.weekday()  # 0=Monday, 6=Sunday
            
            if day_of_week in days_to_schedule:
                # Create start and end datetime
                event_start = tz.localize(datetime.combine(current_date, __import__('datetime').time(hours, minutes)))
                event_end = event_start + timedelta(minutes=self.schedule_duration)
                
                events_to_create.append({
                    'name': f"{self.name} - {current_date.strftime('%A, %b %d, %Y')}",
                    'start': event_start,
                    'stop': event_end,
                    'location': '',
                    'description': f"Course: {self.course_id.name}\nTutor: {self.tutor_id.name if self.tutor_id else 'N/A'}",
                    'user_id': self.tutor_id.partner_id.user_ids[0].id if self.tutor_id and self.tutor_id.partner_id.user_ids else self.env.user.id,
                })
            
            current_date += timedelta(days=1)
        
        # Create all events
        if events_to_create:
            self.env['calendar.event'].create(events_to_create)
    
    def _get_days_to_schedule(self):
        """Get list of day numbers (0=Monday, 6=Sunday) based on schedule configuration"""
        days = []
        
        if self.schedule_type == 'weekdays':
            days = [0, 1, 2, 3, 4]  # Monday to Friday
        elif self.schedule_type == 'daily':
            days = [0, 1, 2, 3, 4, 5, 6]  # All days
        else:
            # For once_weekly and twice_weekly, use manual day selection
            if self.monday:
                days.append(0)
            if self.tuesday:
                days.append(1)
            if self.wednesday:
                days.append(2)
            if self.thursday:
                days.append(3)
            if self.friday:
                days.append(4)
            if self.saturday:
                days.append(5)
            if self.sunday:
                days.append(6)
        
        return days
