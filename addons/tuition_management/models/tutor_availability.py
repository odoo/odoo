# -*- coding: utf-8 -*-
from odoo import api, fields, models


class TutorAvailability(models.Model):
    _name = 'tutor.availability'
    _description = 'Tutor Availability'
    
    tutor_id = fields.Many2one('tutor.profile', string='Tutor', required=True, ondelete='cascade')
    
    # Availability Type
    availability_type = fields.Selection([
        ('normal', 'Normal'),
        ('special', 'Special')
    ], string='Type of Availability', required=True, default='normal')
    
    # Timezone
    timezone = fields.Selection('_tz_get', string='Timezone', required=True, 
                               default=lambda self: self.env.user.tz or 'UTC')
    
    # Days of Week - Multiple selection
    monday = fields.Boolean(string='Monday')
    tuesday = fields.Boolean(string='Tuesday')
    wednesday = fields.Boolean(string='Wednesday')
    thursday = fields.Boolean(string='Thursday')
    friday = fields.Boolean(string='Friday')
    saturday = fields.Boolean(string='Saturday')
    sunday = fields.Boolean(string='Sunday')
    
    # Time fields - using Selection dropdowns for hours and minutes
    start_hour = fields.Selection([(str(i).zfill(2), str(i).zfill(2)) for i in range(24)], 
                                  string='Start Hour', required=True, default='09')
    start_minute = fields.Selection([(str(i).zfill(2), str(i).zfill(2)) for i in range(0, 60, 5)], 
                                    string='Start Minute', required=True, default='00')
    
    end_hour = fields.Selection([(str(i).zfill(2), str(i).zfill(2)) for i in range(24)], 
                                string='End Hour', required=True, default='10')
    end_minute = fields.Selection([(str(i).zfill(2), str(i).zfill(2)) for i in range(0, 60, 5)], 
                                  string='End Minute', required=True, default='00')
    
    # Helper fields for display
    start_time_display = fields.Char(string='Start Time', compute='_compute_time_display', store=False)
    end_time_display = fields.Char(string='End Time', compute='_compute_time_display', store=False)
    
    # Additional info
    notes = fields.Text(string='Notes')
    active = fields.Boolean(string='Active', default=True)
    
    @staticmethod
    def _tz_get():
        return [(tz, tz) for tz in __import__('pytz').all_timezones]
    
    @api.depends('start_hour', 'start_minute', 'end_hour', 'end_minute')
    def _compute_time_display(self):
        """Format time display from hour and minute selections"""
        for rec in self:
            rec.start_time_display = f"{rec.start_hour}:{rec.start_minute}" if rec.start_hour and rec.start_minute else ""
            rec.end_time_display = f"{rec.end_hour}:{rec.end_minute}" if rec.end_hour and rec.end_minute else ""
    
    @api.constrains('start_hour', 'start_minute', 'end_hour', 'end_minute')
    def _check_times(self):
        """Validate that end time is after start time"""
        for rec in self:
            if rec.start_hour and rec.end_hour:
                start_total_minutes = int(rec.start_hour) * 60 + int(rec.start_minute or 0)
                end_total_minutes = int(rec.end_hour) * 60 + int(rec.end_minute or 0)
                
                if end_total_minutes <= start_total_minutes:
                    raise models.ValidationError(
                        "End time must be after start time."
                    )
    
    def _get_selected_days(self):
        """Get list of selected days"""
        days = []
        day_mapping = {
            'monday': 'Monday',
            'tuesday': 'Tuesday',
            'wednesday': 'Wednesday',
            'thursday': 'Thursday',
            'friday': 'Friday',
            'saturday': 'Saturday',
            'sunday': 'Sunday',
        }
        for field, label in day_mapping.items():
            if getattr(self, field):
                days.append(label)
        return ', '.join(days) if days else 'No days selected'