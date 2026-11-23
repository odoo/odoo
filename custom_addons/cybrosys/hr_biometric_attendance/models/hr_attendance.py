import pytz
from odoo import fields, models,api
from datetime import timedelta,datetime as dt


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    x_late_minutes = fields.Float(
        string='Late Minutes',
        help='Minutes late compared to scheduled start (after grace period)')

    x_early_leave_minutes = fields.Float(
        string='Early Leave Minutes',
        help='Minutes left early compared to scheduled end (after grace period)')

    x_is_absent = fields.Boolean(
        string='Is Absent',
        default=False,
        readonly=True,
        help='Indicates if the employee is considered absent for this attendance record'
    )

    x_day_of_week = fields.Char(
        string="Day",
        compute='_compute_day_of_week',
        store=True,
    )

    x_is_weekend = fields.Boolean(
        string='Is Weekend',
        default=False,
    )

    x_weekend_granted = fields.Boolean(
        string='Weekend Granted',
        default=False,
    )


    @api.depends('check_in')
    def _compute_day_of_week(self):
        for record in self:
            if record.check_in:
                record.x_day_of_week = record.check_in.strftime('%A')
            else:
                record.x_day_of_week = False



    @api.depends('employee_id', 'check_in')
    def _compute_weekend_info(self):
        helper = self.env['biometric.schedule.helper']
        for rec in self:
            rec.is_weekend = False
            rec.weekend_granted = False
            rec.weekend_hours = 0.0

            if not rec.employee_id or not rec.check_in:
                continue

            emp = rec.employee_id
            emp_tz = helper.get_employee_tz(emp)
            local_ci = pytz.utc.localize(rec.check_in).astimezone(emp_tz)
            current_date = local_ci.date()

            # Check if this date is a non-scheduled day (weekend)
            if helper.is_scheduled_workday(emp, current_date):
                continue

            rec.is_weekend = True

            # Find the contiguous weekend block containing this date
            weekend_block = [current_date]
            # Expand backwards
            d = current_date - timedelta(days=1)
            while not helper.is_scheduled_workday(emp, d):
                weekend_block.insert(0, d)
                d -= timedelta(days=1)
            day_before_weekend = d  # last workday before the block

            # Expand forwards
            d = current_date + timedelta(days=1)
            while not helper.is_scheduled_workday(emp, d):
                weekend_block.append(d)
                d += timedelta(days=1)
            day_after_weekend = d  # first workday after the block

            # Check if employee attended the day before or after the weekend block
            attended_before = self.search_count([
                ('employee_id', '=', emp.id),
                ('check_in', '>=', dt.combine(day_before_weekend, dt.min.time())),
                ('check_in', '<', dt.combine(day_before_weekend + timedelta(days=1), dt.min.time())),
                ('is_absent', '!=', True),
            ], limit=1)

            attended_after = self.search_count([
                ('employee_id', '=', emp.id),
                ('check_in', '>=', dt.combine(day_after_weekend, dt.min.time())),
                ('check_in', '<', dt.combine(day_after_weekend + timedelta(days=1), dt.min.time())),
                ('is_absent', '!=', True),
            ], limit=1)

            if attended_before or attended_after:
                rec.weekend_granted = True
                # Use a reference workday schedule to determine hours
                # Use the day before or after (whichever is a workday) to get normal hours
                ref_date = day_before_weekend
                ref_schedule = helper.get_employee_day_schedule(emp, ref_date, emp_tz)
                if not ref_schedule:
                    ref_date = day_after_weekend
                    ref_schedule = helper.get_employee_day_schedule(emp, ref_date, emp_tz)

                if ref_schedule:
                    total_sched = (ref_schedule['end'] - ref_schedule['start']).total_seconds() / 3600.0
                    break_hrs = ref_schedule.get('break_hours', 0.0)
                    rec.weekend_hours = max(0.0, total_sched - break_hrs)


