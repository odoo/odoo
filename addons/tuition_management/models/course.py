# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError
import pytz

COUNTRY_CODES = [
    ('+1', '+1 (USA/Canada)'),
    ('+44', '+44 (UK)'),
    ('+91', '+91 (India)'),
    ('+61', '+61 (Australia)'),
    ('+86', '+86 (China)'),
    ('+81', '+81 (Japan)'),
    ('+33', '+33 (France)'),
    ('+49', '+49 (Germany)'),
    ('+39', '+39 (Italy)'),
    ('+34', '+34 (Spain)'),
    ('+65', '+65 (Singapore)'),
    ('+60', '+60 (Malaysia)'),
    ('+62', '+62 (Indonesia)'),
    ('+63', '+63 (Philippines)'),
    ('+66', '+66 (Thailand)'),
    ('+84', '+84 (Vietnam)'),
    ('+852', '+852 (Hong Kong)'),
    ('+886', '+886 (Taiwan)'),
    ('+64', '+64 (New Zealand)'),
    ('+27', '+27 (South Africa)'),
    ('+55', '+55 (Brazil)'),
    ('+52', '+52 (Mexico)'),
    ('+54', '+54 (Argentina)'),
    ('+56', '+56 (Chile)'),
    ('+57', '+57 (Colombia)'),
    ('+971', '+971 (UAE)'),
    ('+966', '+966 (Saudi Arabia)'),
    ('+972', '+972 (Israel)'),
    ('+90', '+90 (Turkey)'),
    ('+47', '+47 (Norway)'),
    ('+46', '+46 (Sweden)'),
    ('+45', '+45 (Denmark)'),
    ('+31', '+31 (Netherlands)'),
    ('+43', '+43 (Austria)'),
    ('+41', '+41 (Switzerland)'),
    ('+32', '+32 (Belgium)'),
    ('+358', '+358 (Finland)'),
    ('+48', '+48 (Poland)'),
    ('+36', '+36 (Hungary)'),
    ('+420', '+420 (Czech Republic)'),
    ('+421', '+421 (Slovakia)'),
    ('+40', '+40 (Romania)'),
    ('+353', '+353 (Ireland)'),
    ('+30', '+30 (Greece)'),
    ('+359', '+359 (Bulgaria)'),
    ('+385', '+385 (Croatia)'),
    ('+389', '+389 (Macedonia)'),
]


# Helper function to get all timezones
def _get_timezone_selection():
    """Return a list of tuples of all available timezones."""
    return [(tz, tz) for tz in sorted(pytz.all_timezones)]


class GradeMaster(models.Model):
    _name = 'grade.master'
    _description = 'Grade Master'

    name = fields.Char(string='Grade Name', required=True)


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


class EnquiryStage(models.Model):
    _name = 'enquiry.stage'
    _description = 'Enquiry Stage'
    _order = 'sequence, id'

    name = fields.Char(string='Stage Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    fold = fields.Boolean(string='Folded in Kanban', default=False)


class Enquiry(models.Model):
    _name = 'enquiry'
    _description = 'Student Enquiry'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Enquiry identification
    enquiry_name = fields.Char(string='Enquiry Name', required=True, help='e.g., SAT Enquiry for Tom Thomas', tracking=True)
    
    # Personal Information
    name = fields.Char(string='Parent Name', required=True, tracking=True)
    
    # Student Information
    student_name = fields.Char(string='Student Name', required=True, tracking=True)
    
    partner_id = fields.Many2one('res.partner', string='Contact', required=True, ondelete='cascade')
    email = fields.Char()
    country_code = fields.Selection(COUNTRY_CODES, string='Country Code', default='+1')
    phone = fields.Char()
    subject_id = fields.Many2one('subject.master', string='Interested Subject', required=True)
    grade_id = fields.Many2one('grade.master', string='Target Grade', required=True)
    enquiry_date = fields.Date(default=fields.Date.context_today, tracking=True)
    stage_id = fields.Many2one('enquiry.stage', string='Stage', tracking=True, 
                                default=lambda self: self.env['enquiry.stage'].search([], limit=1, order='sequence'),
                                group_expand='_read_group_stage_ids')
    notes = fields.Text()
    demo_session_ids = fields.One2many('demo.session', 'enquiry_id', string='Demo Sessions')

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        """Always display all stages in kanban, even if empty."""
        return self.env['enquiry.stage'].search([], order='sequence')

    def action_schedule_demo(self):
        """Schedule a demo session for this enquiry."""
        self.ensure_one()
        demo_vals = {
            'enquiry_id': self.id,
            'subject_id': self.subject_id.id,
            'scheduled_date': fields.Date.context_today(self),
        }
        demo = self.env['demo.session'].create(demo_vals)
        # Move to "Demo Scheduled" stage if it exists
        demo_stage = self.env['enquiry.stage'].search([('name', 'ilike', 'Demo')], limit=1)
        if demo_stage:
            self.stage_id = demo_stage
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
            enrolled_stage = self.env['enquiry.stage'].search([('name', 'ilike', 'Enrolled')], limit=1)
            if enrolled_stage:
                self.stage_id = enrolled_stage
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'course.enrollment',
                'res_id': enrollment.id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            raise UserError('No active course found matching the subject and grade.')

    def action_convert_to_parent(self):
        """Convert enquiry to parent profile."""
        self.ensure_one()
        parent_profile = self.env['parent.profile'].search([('name', '=', self.name)], limit=1)
        if not parent_profile:
            parent_profile = self.env['parent.profile'].create({
                'name': self.name,
                'email': self.email or '',
                'phone': self.phone or '',
                'country_code': self.country_code or '+1',
            })
        
        enrolled_stage = self.env['enquiry.stage'].search([('name', 'ilike', 'Enrolled')], limit=1)
        if enrolled_stage:
            self.stage_id = enrolled_stage
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'parent.profile',
            'res_id': parent_profile.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_mark_completed(self):
        """Mark enquiry as completed."""
        self.ensure_one()
        completed_stage = self.env['enquiry.stage'].search([('name', 'ilike', 'Completed')], limit=1)
        if completed_stage:
            self.stage_id = completed_stage

    def action_mark_lost(self):
        """Mark enquiry as lost."""
        self.ensure_one()
        lost_stage = self.env['enquiry.stage'].search([('name', 'ilike', 'Lost')], limit=1)
        if lost_stage:
            self.stage_id = lost_stage

    def action_enroll_student(self):
        """Mark enquiry as enrolled (alternative to converting to student/parent)."""
        self.ensure_one()
        enrolled_stage = self.env['enquiry.stage'].search([('name', 'ilike', 'Enrolled')], limit=1)
        if enrolled_stage:
            self.stage_id = enrolled_stage

    def action_enroll_to_course(self):
        """Convert enquiry to a course enrollment, creating student, parent, and course."""
        self.ensure_one()
        
        # Create or find parent profile
        parent_profile = self.env['parent.profile'].search([
            ('email', '=', self.email)
        ], limit=1)
        
        if not parent_profile:
            parent_profile = self.env['parent.profile'].create({
                'name': self.name,
                'email': self.email or '',
                'phone': self.phone or '',
                'country_code': self.country_code or '+1',
            })
        
        # Create or find student profile
        student_profile = self.env['student.profile'].search([
            ('name', '=', self.student_name),
            ('parent_id', '=', parent_profile.id),
        ], limit=1)
        
        if not student_profile:
            student_profile = self.env['student.profile'].create({
                'name': self.student_name,
                'email': self.email or '',
                'phone': self.phone or '',
                'country_code': self.country_code,
                'grade_id': self.grade_id.id if self.grade_id else False,
                'subjects_ids': [(6, 0, [self.subject_id.id])] if self.subject_id else [],
                'parent_id': parent_profile.id,
            })
        else:
            # Link existing student to parent if not already linked
            if not student_profile.parent_id:
                student_profile.parent_id = parent_profile.id
        
        # Build course name: Student Name - Subject - Grade
        course_name = f"{self.student_name} - {self.subject_id.name} - {self.grade_id.name}"
        
        # Find existing course with the same name, or create a new one
        course = self.env['course.master'].search([
            ('name', '=', course_name),
        ], limit=1)
        
        if not course:
            course = self.env['course.master'].create({
                'name': course_name,
                'subject_id': self.subject_id.id,
                'grade_id': self.grade_id.id,
                'status': 'active',
            })
        
        # Create enrollment
        enrollment = self.env['course.enrollment'].create({
            'name': f"{student_profile.name} - {course.name}",
            'course_id': course.id,
            'student_id': student_profile.id,
            'status': 'enrolled',
        })
        
        # Move to Enrolled stage
        enrolled_stage = self.env['enquiry.stage'].search([('name', 'ilike', 'Enrolled')], limit=1)
        if enrolled_stage:
            self.stage_id = enrolled_stage
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'course.enrollment',
            'res_id': enrollment.id,
            'view_mode': 'form',
            'target': 'current',
        }


class DemoSession(models.Model):
    _name = 'demo.session'
    _description = 'Demo Session'

    enquiry_id = fields.Many2one('enquiry', string='Enquiry', required=True, ondelete='cascade')
    subject_id = fields.Many2one('subject.master', string='Subject', required=True, ondelete='restrict')
    tutor_id = fields.Many2one('tutor.profile', string='Tutor', required=True, ondelete='restrict')
    scheduled_datetime = fields.Datetime(string='Scheduled Date & Time', required=True)
    timezone = fields.Selection(lambda self: self._get_timezone_selection(), string='Timezone', default='UTC', required=True)
    duration_minutes = fields.Integer(string='Duration (Minutes)', default=30, required=True)
    status = fields.Selection([
        ('pending', 'Pending'),
        ('completed', 'Completed')
    ], string='Status', default='pending', required=True)
    rating = fields.Integer(string='Rating', default=0, help='Rate from 0 to 5')
    feedback = fields.Text(string='Feedback')

    @staticmethod
    def _get_timezone_selection():
        """Return a list of tuples of all available timezones."""
        return [(tz, tz) for tz in sorted(pytz.all_timezones)]

    def action_mark_completed(self):
        """Mark demo session as completed."""
        self.ensure_one()
        self.write({
            'status': 'completed'
        })
        if self.enquiry_id:
            completed_stage = self.env['enquiry.stage'].search([('name', 'ilike', 'Completed')], limit=1)
            if completed_stage:
                self.enquiry_id.stage_id = completed_stage


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
            day_of_week = current_date.weekday() # 0=Monday, 6=Sunday
            
            if day_of_week in days_to_schedule:
                # Create start and end datetime in local tz, then convert to naive UTC
                local_start = tz.localize(datetime.combine(current_date, __import__('datetime').time(hours, minutes)))
                utc_start = local_start.astimezone(pytz.utc).replace(tzinfo=None)
                utc_end = utc_start + timedelta(minutes=self.schedule_duration)
                
                events_to_create.append({
                    'name': f"{self.name} - {current_date.strftime('%A, %b %d, %Y')}",
                    'start': utc_start,
                    'stop': utc_end,
                    'location': '',
                    'description': f"Course: {self.course_id.name}\nTutor: {self.tutor_id.name if self.tutor_id else 'N/A'}",
                    'user_id': self.env.user.id,
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


class TutorProfile(models.Model):
    _name = 'tutor.profile'
    _description = 'Tutor Profile'

    name = fields.Char(string='Full Name', required=True)
    email = fields.Char(string='Email')
    country_code = fields.Selection(COUNTRY_CODES, string='Country Code', default='+1')
    phone = fields.Char(string='Phone')
    address_line_1 = fields.Char(string='Address Line 1')
    address_line_2 = fields.Char(string='Address Line 2')
    address_line_3 = fields.Char(string='Address Line 3')
    address_line_4 = fields.Char(string='Address Line 4')
    zip_code = fields.Char(string='Zip Code')
    subjects_ids = fields.Many2many('subject.master', string='Subjects')
    bio = fields.Text(string='Biography')
    experience = fields.Integer(string='Years of Experience')
    rating = fields.Float(string='Rating', digits=(2, 1), default=5.0)
    availability_ids = fields.One2many('tutor.availability', 'tutor_id', string='Availability')
    student_ids = fields.One2many('student.profile', 'tutor_id', string='Students')


class TutorAvailability(models.Model):
    _name = 'tutor.availability'
    _description = 'Tutor Availability'

    name = fields.Char(string='Name')
    tutor_id = fields.Many2one('tutor.profile', string='Tutor', required=True, ondelete='cascade')
    day_of_week = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday')
    ], string='Day of Week', required=True)
    start_time = fields.Float(string='Start Time', required=True)
    end_time = fields.Float(string='End Time', required=True)

    @api.constrains('start_time', 'end_time')
    def _check_availability_times(self):
        """Ensure that end_time is after start_time"""
        for record in self:
            if record.end_time <= record.start_time:
                raise models.ValidationError("End time must be after start time.")

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to set default name"""
        records = super().create(vals_list)
        for record in records:
            record.name = f"{record.tutor_id.name} - {record.get_day_name(record.day_of_week)}: {record.start_time} - {record.end_time}"
        return records

    def write(self, vals):
        """Override write to update name field"""
        result = super().write(vals)
        for record in self:
            record.name = f"{record.tutor_id.name} - {record.get_day_name(record.day_of_week)}: {record.start_time} - {record.end_time}"
        return result

    def get_day_name(self, day_number):
        """Helper method to get day name from day number"""
        day_names = dict(self._fields['day_of_week'].selection).get(day_number)
        return day_names if day_names else ''

class StudentProfile(models.Model):
    _name = 'student.profile'
    _description = 'Student Profile'

    name = fields.Char(string='Full Name', required=True)
    email = fields.Char(string='Email')
    country_code = fields.Selection(COUNTRY_CODES, string='Country Code', default='+1')
    phone = fields.Char(string='Phone')
    grade_id = fields.Many2one('grade.master', string='Grade')
    subjects_ids = fields.Many2many('subject.master', string='Subjects')
    address_line_1 = fields.Char(string='Address Line 1')
    address_line_2 = fields.Char(string='Address Line 2')
    address_line_3 = fields.Char(string='Address Line 3')
    address_line_4 = fields.Char(string='Address Line 4')
    zip_code = fields.Char(string='Zip Code')
    parent_id = fields.Many2one('parent.profile', string='Parent', ondelete='set null')
    tutor_id = fields.Many2one('tutor.profile', string='Tutor', ondelete='set null')

    def action_link_parent(self):
        """Open parent selection dialog to link parent to student."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'parent.profile',
            'view_mode': 'tree,form',
            'target': 'current',
            'context': {
                'default_student_ids': [(4, self.id)],
            }
        }

    def action_view_parent(self):
        """Navigate to the parent form from student."""
        self.ensure_one()
        if not self.parent_id:
            return
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'parent.profile',
            'res_id': self.parent_id.id,
            'view_mode': 'form',
            'target': 'current',
        }


class ParentProfile(models.Model):
    _name = 'parent.profile'
    _description = 'Parent Profile'

    name = fields.Char(string='Full Name', required=True)
    email = fields.Char(string='Email')
    country_code = fields.Selection(COUNTRY_CODES, string='Country Code', default='+1')
    phone = fields.Char(string='Phone')
    address_line_1 = fields.Char(string='Address Line 1')
    address_line_2 = fields.Char(string='Address Line 2')
    address_line_3 = fields.Char(string='Address Line 3')
    address_line_4 = fields.Char(string='Address Line 4')
    zip_code = fields.Char(string='Zip Code')
    student_ids = fields.One2many('student.profile', 'parent_id', string='Students')
