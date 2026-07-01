# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta
from collections import defaultdict
from odoo.tools.intervals import Intervals
from odoo import SUPERUSER_ID, models, fields, api, exceptions, _
from odoo.fields import Domain
from odoo.tools import BinaryBytes


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    attendance_based = fields.Boolean(readonly=False, related="version_id.attendance_based", inherited=True, groups="hr.group_hr_user")

    attendance_manager_id = fields.Many2one(
        'res.users', store=True, readonly=False,
        string="Attendance Approver",
        compute='_compute_attendance_manager',
        domain="[('share', '=', False), ('company_ids', 'in', company_id)]",
        groups="hr_attendance.group_hr_attendance_own,hr_attendance.group_hr_attendance_officer",
        help="The user set in Attendance will access the attendance of the employee through the dedicated app and will be able to edit them.")
    attendance_ids = fields.One2many(
        'hr.attendance', 'employee_id', groups="hr_attendance.group_hr_attendance_own,hr_attendance.group_hr_attendance_officer,hr.group_hr_user")
    last_attendance_id = fields.Many2one(
        'hr.attendance', compute='_compute_last_attendance_id', store=True, index='btree_not_null',
        groups="hr_attendance.group_hr_attendance_own,hr_attendance.group_hr_attendance_officer,hr.group_hr_user")
    last_check_in = fields.Datetime(
        related='last_attendance_id.check_in', store=True,
        groups="hr_attendance.group_hr_attendance_own,hr_attendance.group_hr_attendance_officer,hr.group_hr_user", tracking=False)
    last_check_out = fields.Datetime(
        related='last_attendance_id.check_out', store=True,
        groups="hr_attendance.group_hr_attendance_own,hr_attendance.group_hr_attendance_officer,hr.group_hr_user", tracking=False)
    attendance_state = fields.Selection(
        string="Attendance Status", compute='_compute_attendance_state',
        selection=[('checked_out', "Checked out"), ('checked_in', "Checked in")],
        groups="hr_attendance.group_hr_attendance_own,hr_attendance.group_hr_attendance_officer,hr.group_hr_user")
    hours_last_month = fields.Float(compute='_compute_hours_last_month')
    hours_last_month_overtime = fields.Float(compute='_compute_hours_last_month')
    hours_today = fields.Float(
        compute='_compute_hours_today',
        groups="hr_attendance.group_hr_attendance_own,hr_attendance.group_hr_attendance_officer,hr.group_hr_user")
    hours_previously_today = fields.Float(
        compute='_compute_hours_today',
        groups="hr_attendance.group_hr_attendance_own,hr_attendance.group_hr_attendance_officer,hr.group_hr_user")
    today_attendance_ids = fields.Many2many(
        'hr.attendance', compute='_compute_hours_today',
        groups="hr_attendance.group_hr_attendance_own,hr_attendance.group_hr_attendance_officer,hr.group_hr_user")
    last_attendance_worked_hours = fields.Float(
        compute='_compute_hours_today',
        groups="hr_attendance.group_hr_attendance_own,hr_attendance.group_hr_attendance_officer,hr.group_hr_user")
    hours_last_month_display = fields.Char(
        compute='_compute_hours_last_month', groups="hr.group_hr_user")
    total_overtime = fields.Float(compute='_compute_total_overtime')
    display_attendances = fields.Boolean(compute="_compute_display_attendances")

    def _has_attendance_check_in_ability(self):
        self.ensure_one()
        has_attendance_check_in_ability = self.company_id.attendance_from_systray and self.attendance_based
        return has_attendance_check_in_ability

    def get_attendace_data_by_employee(self, date_start, date_stop):
        attendance_data = {
            employee_id: {
                'worked_hours': 0,
                'overtime_hours': 0,
            }
            for employee_id in self.ids
        }
        all_attendances = self.env['hr.attendance']._read_group(
            domain=[
                ('employee_id', 'in', self.ids),
                ('check_in', '<', date_stop),
                ('check_out', '>', date_start),
            ],
            groupby=['employee_id'],
            aggregates=['worked_hours:sum'],
        )
        for employee, worked_hours in all_attendances:
            attendance_data[employee.id]['worked_hours'] += worked_hours

        return attendance_data

    @api.model_create_multi
    def create(self, vals_list):
        officer_group = self.env.ref('hr_attendance.group_hr_attendance_officer', raise_if_not_found=False)
        group_updates = []
        for vals in vals_list:
            if officer_group and vals.get('attendance_manager_id'):
                group_updates.append((4, vals['attendance_manager_id']))
        if group_updates:
            officer_group.sudo().write({'user_ids': group_updates})
        return super().create(vals_list)

    def write(self, vals):
        old_officers = self.env['res.users']
        if 'attendance_manager_id' in vals:
            old_officers = self.attendance_manager_id
            # Officer was added
            if vals['attendance_manager_id']:
                officer = self.env['res.users'].browse(vals['attendance_manager_id'])
                officers_group = self.env.ref('hr_attendance.group_hr_attendance_officer', raise_if_not_found=False)
                if officers_group and not officer.has_group('hr_attendance.group_hr_attendance_officer'):
                    officer.sudo().write({'group_ids': [(4, officers_group.id)]})

        res = super().write(vals)
        old_officers.sudo()._clean_attendance_officers()

        return res

    @api.depends('parent_id')
    def _compute_attendance_manager(self):
        for employee in self:
            previous_manager = employee._origin.parent_id.user_id
            new_manager = employee.parent_id.user_id
            if new_manager and employee.attendance_manager_id and employee.attendance_manager_id == previous_manager:
                employee.attendance_manager_id = new_manager
            elif not employee.attendance_manager_id:
                employee.attendance_manager_id = False

    def action_archive(self):
        res = super().action_archive()
        open_attendances = self.env['hr.attendance'].sudo().search([
            ('employee_id', 'in', self.ids),
            ('check_out', '=', False),
        ])
        if open_attendances:
            open_attendances.write({
                'check_out': fields.Datetime.now(),
            })
        return res

    def _compute_total_overtime(self):
        for employee in self:
            employee.total_overtime = 0.0

    def _compute_hours_last_month(self):
        """
        Compute hours and overtime hours in the current month, if we are the 15th of october, will compute from 1 oct to 15 oct
        """
        now = fields.Datetime.now()
        now_utc = now.replace(tzinfo=datetime.UTC)
        for timezone, employees in self.grouped('tz').items():
            tz = ZoneInfo(timezone or 'UTC')
            now_tz = now_utc.astimezone(tz)
            start_tz = now_tz.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            start_naive = start_tz.astimezone(datetime.UTC).replace(tzinfo=None)
            end_tz = now_tz
            end_naive = end_tz.astimezone(datetime.UTC).replace(tzinfo=None)

            for employee in employees:
                current_month_attendances = employee.attendance_ids.filtered(
                    lambda att: att.check_in >= start_naive and att.check_out and att.check_out <= end_naive
                )
                hours = sum(att.worked_hours or 0 for att in current_month_attendances)
                employee.hours_last_month = round(hours, 2)
                employee.hours_last_month_display = self.env._("%(hours)g h in %(month)s") % {'hours': employee.hours_last_month, 'month': now_tz.strftime('%b')}
                employee.hours_last_month_overtime = 0.0

    def _compute_hours_today(self):
        now = fields.Datetime.now()
        now_utc = now.replace(tzinfo=datetime.UTC)
        for timezone, employees in self.grouped('tz').items():
            # start of day in the employee's timezone might be the previous day in utc
            tz = ZoneInfo(timezone or 'UTC')
            start_tz = now_utc.astimezone(tz) + relativedelta(hour=0, minute=0)  # day start in the employee's timezone
            start_naive = start_tz.astimezone(datetime.UTC).replace(tzinfo=None)

            attendances_by_employee = dict(self.env['hr.attendance']._read_group(
                [
                    ('employee_id', 'in', employees.ids),
                    ('check_in', '<=', now),
                    '|', ('check_out', '>=', start_naive), ('check_out', '=', False),
                ],
                ['employee_id'],
                ['id:recordset'],
            ))

            for employee in employees:
                attendances = attendances_by_employee.get(employee, self.env['hr.attendance'])
                employee.today_attendance_ids = attendances
                hours_previously_today = 0
                worked_hours = 0
                attendance_worked_hours = 0
                for attendance in attendances:
                    delta = (attendance.check_out or now) - max(attendance.check_in, start_naive)
                    attendance_worked_hours = delta.total_seconds() / 3600.0
                    worked_hours += attendance_worked_hours
                    hours_previously_today += attendance_worked_hours
                employee.last_attendance_worked_hours = attendance_worked_hours
                hours_previously_today -= attendance_worked_hours
                employee.hours_previously_today = hours_previously_today
                employee.hours_today = worked_hours

    @api.depends('attendance_ids')
    def _compute_last_attendance_id(self):
        current_datetime = fields.Datetime.now()
        for employee in self:
            employee.last_attendance_id = self.env['hr.attendance'].search([
                ('employee_id', 'in', employee.ids),
                ('check_in', '<=', current_datetime),
            ], order="check_in desc", limit=1)

    @api.depends('last_attendance_id.check_in', 'last_attendance_id.check_out', 'last_attendance_id')
    def _compute_attendance_state(self):
        for employee in self:
            att = employee.last_attendance_id.sudo()
            employee.attendance_state = att and not att.check_out and 'checked_in' or 'checked_out'

    @api.depends_context('uid')
    @api.depends('user_id', 'user_id.group_ids')
    def _compute_display_attendances(self):
        current_user = self.env.user
        for employee in self:
            if current_user.has_group('hr_attendance.group_hr_attendance_officer'):
                employee.display_attendances = True
            else:
                employee.display_attendances = current_user.has_group('hr_attendance.group_hr_attendance_own_reader') \
                                                and employee in current_user.employee_ids

    def _notify_employee_presence_status(self):
        self.ensure_one()
        payload = {
            "hr_presence_state": self.hr_presence_state,
            "hr_icon_display": self.hr_icon_display,
            "employee_id": self.id,
        }
        self._bus_send("hr.employee/presence", payload)

    def _attendance_action_change(self, geo_information=None, check_in_image_data=None):
        """ Check In/Check Out action
            Check In: create a new attendance record and attach check-in image to it, if available
            Check Out: modify check_out field of appropriate attendance record
        """
        self.ensure_one()
        action_date = fields.Datetime.now()
        notification = False

        if self.attendance_state != 'checked_in':
            vals = {
                'employee_id': self.id,
                'check_in': action_date,
            }
            if geo_information:
                vals.update({'in_%s' % key: geo_information[key] for key in geo_information})

            attendance = self.env['hr.attendance'].create(vals)
            if check_in_image_data:
                attendance.in_image = BinaryBytes(check_in_image_data['image'])
                attachment = self.env['ir.attachment'].search([
                    ('res_model', '=', attendance._name),
                    ('res_id', '=', attendance.id),
                    ('res_field', '=', 'in_image'),
                ], limit=1)
                attachment.name = f"{self.display_name.replace(' ', '_')}_{str(attendance.check_in).replace(' ', '_')}_UTC"
                message_vals = {
                    'body': self.env._("Check-in image captured"),
                    'attachment_ids': [attachment.id],
                }
                if self.env.user._is_internal():
                    attendance.message_post(**message_vals)
                else:
                    attendance.with_user(SUPERUSER_ID).message_post(**message_vals)
            elif self.company_id.attendance_capture_check_in:
                notification = {
                    'type': 'warning',
                    'message': self.env._("Check-in is recorded, but picture could not be captured"),
                }
            self._notify_employee_presence_status()
            return notification

        attendance = self.env['hr.attendance'].search([('employee_id', '=', self.id), ('check_out', '=', False)], limit=1)
        if attendance:
            if not self.version_id.is_flexible and self.company_id.single_check_in:
                if self.env.context.get('is_from_systray_check_in_out', False):  # throw user error if user tries to checkout from systray.
                    raise exceptions.UserError(self.env._("You've already checked in."))
                return notification  # no need to checkout the user if single checkin enabled.
            if geo_information:
                attendance.write({
                    'check_out': action_date,
                    **{'out_%s' % key: geo_information[key] for key in geo_information}
                })
            else:
                attendance.write({
                    'check_out': action_date
                })
            self._notify_employee_presence_status()
        else:
            raise exceptions.UserError(_(
                'Cannot perform check out on %(empl_name)s, could not find corresponding check in. '
                'Your attendances have probably been modified manually by human resources.',
                empl_name=self.sudo().name))
        return notification

    def action_open_last_month_attendances(self):
        self.ensure_one()
        now = fields.Datetime.now()
        tz = ZoneInfo(self.tz or 'UTC')
        now_tz = now.replace(tzinfo=datetime.UTC).astimezone(tz)
        month_start = now_tz.replace(day=1, hour=0, minute=0, second=0, microsecond=0).astimezone(datetime.UTC).replace(tzinfo=None)
        month_end = (now_tz + relativedelta(months=1)).replace(day=1, hour=0, minute=0, second=0, microsecond=0).astimezone(datetime.UTC).replace(tzinfo=None)
        return {
            "type": "ir.actions.act_window",
            "name": _("Attendances This Month"),
            "res_model": "hr.attendance",
            "views": [[False, "list"]],
            "domain": [('employee_id', '=', self.id), ('check_in', '>=', month_start), ('check_in', '<', month_end)],
            "context": {"group_by": ["check_in:week"]},
        }

    @api.depends("user_id.im_status", "attendance_state")
    def _compute_presence_state(self):
        """
        Override to include checkin/checkout in the presence state
        Attendance has the second highest priority after login
        """
        super()._compute_presence_state()
        employees = self.filtered(lambda e: e.hr_presence_state != "present")
        employee_to_check_working = self.filtered(lambda e: e.sudo().attendance_state == "checked_out"
                                                            and e.hr_presence_state == "out_of_working_hour")
        working_now_list = employee_to_check_working._get_employee_working_now()
        for employee in employees:
            if employee.sudo().attendance_state == "checked_in" or not employee.user_id:
                if not employee.user_id and not employee.sudo().is_in_contract:
                    employee.hr_presence_state = "out_of_working_hour"
                else:
                    employee.hr_presence_state = "present"
            elif employee.sudo().attendance_state == "checked_out" and \
                 employee.hr_presence_state == "out_of_working_hour" and \
                 employee.id in working_now_list and \
                 employee.sudo().is_in_contract:
                employee.hr_presence_state = "absent"

    def _compute_presence_icon(self):
        res = super()._compute_presence_icon()
        # All employee must chek in or check out. Everybody must have an icon
        for employee in self:
            employee.show_hr_icon_display = employee.company_id.hr_presence_control_attendance or bool(employee.user_id)
        return res

    def open_barcode_scanner(self):
        return {
            "type": "ir.actions.client",
            "tag": "employee_barcode_scanner",
            "name": "Badge Scanner"
        }

    def _get_calendar_attendance_domain(self):
        """Return the domain to filter attendances when computing calendar attendance intervals.

        This method can be overridden to customize which attendances are considered
        for calendar scheduling calculations.

        Returns:
            Domain: The domain expression to filter hr.attendance records.
        """
        return Domain.TRUE

    def _get_work_intervals_by_type(self, start, stop, version_periods_by_employee):
        employees_by_calendar = defaultdict(lambda: self.env['hr.employee'])
        leave_intervals_by_cal_by_resource = defaultdict(lambda: defaultdict(Intervals))
        public_leave_intervals_by_cal_by_resource = defaultdict(lambda: defaultdict(Intervals))
        attendance_intervals_by_employee = defaultdict(Intervals)

        for employee, intervals in version_periods_by_employee.items():
            for (_start, _stop, version) in intervals:
                employees_by_calendar[version.resource_calendar_id] |= employee

        for cal, employees in employees_by_calendar.items():
            if not cal:  # employees are flex or fully flex
                employees = employees.filtered(lambda e: not e.is_fully_flexible)
                if not employees:
                    continue
            resources_per_tz = employees._get_resources_per_tz()
            cal_leave_intervals_by_resource = cal._leave_intervals_batch(
                start,
                stop,
                resources_per_tz=resources_per_tz,
            )
            cal_public_leave_intervals_by_resource = cal._leave_intervals_batch(
                start,
                stop,
                resources_per_tz=resources_per_tz,
                domain=[('resource_id', '=', False)]
            )
            for resource, leave_intervals in cal_leave_intervals_by_resource.items():
                naive_leave_intervals = Intervals([(
                    i_start.replace(tzinfo=None),
                    i_stop.replace(tzinfo=None),
                    i_model
                ) for (i_start, i_stop, i_model) in leave_intervals])
                leave_intervals_by_cal_by_resource[cal][resource] = naive_leave_intervals

            for resource, public_leave_intervals in cal_public_leave_intervals_by_resource.items():
                naive_public_leave_intervals = Intervals([(
                    i_start.replace(tzinfo=None),
                    i_stop.replace(tzinfo=None),
                    i_model
                ) for (i_start, i_stop, i_model) in public_leave_intervals])
                public_leave_intervals_by_cal_by_resource[cal][resource] = naive_public_leave_intervals

            cal_attendance_intervals_by_resource = cal._attendance_intervals_batch(
                start,
                stop,
                resources_per_tz=resources_per_tz,
                domain=self._get_calendar_attendance_domain() if cal else None,
            )
            for employee in employees:
                attendance_intervals_by_employee[employee] = Intervals([(
                    i_start.replace(tzinfo=None),
                    i_stop.replace(tzinfo=None),
                    i_model
                ) for (i_start, i_stop, i_model) in cal_attendance_intervals_by_resource[employee.resource_id.id]])

        work_intervals_by_type = {
            'leave': defaultdict(Intervals),
            'schedule': defaultdict(Intervals),
            'fully_flexible': defaultdict(Intervals),
            'public_leave': defaultdict(Intervals),
        }
        for employee, intervals in version_periods_by_employee.items():
            employee_attendances = attendance_intervals_by_employee[employee]
            for (p_start, p_stop, version) in intervals:
                interval = Intervals([(p_start.replace(tzinfo=None), p_stop.replace(tzinfo=None), self.env['resource.calendar'])])
                if version.is_fully_flexible:
                    work_intervals_by_type['fully_flexible'][employee] |= interval
                    continue
                calendar = version.resource_calendar_id
                employee_leaves = leave_intervals_by_cal_by_resource[calendar][employee.resource_id.id]
                employee_public_leaves = public_leave_intervals_by_cal_by_resource[calendar][employee.resource_id.id]
                work_intervals_by_type['public_leave'][employee] |= employee_public_leaves & interval
                work_intervals_by_type['leave'][employee] |= employee_leaves & interval
                work_intervals_by_type['schedule'][employee] |= employee_attendances & interval

        return work_intervals_by_type
