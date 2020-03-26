# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval

from odoo import api, fields, models
from pytz import timezone, UTC
from odoo.tools import format_time


class HrEmployeeBase(models.AbstractModel):
    _name = "hr.employee.base"
    _description = "Basic Employee"
    _order = 'name'

    name = fields.Char()
    active = fields.Boolean("Active")
    color = fields.Integer('Color Index', default=0)
    department_id = fields.Many2one('hr.department', 'Department', domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    job_id = fields.Many2one('hr.job', 'Job Position', domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    job_title = fields.Char("Job Title")
    company_id = fields.Many2one('res.company', 'Company')
    address_id = fields.Many2one('res.partner', 'Work Address', domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    work_phone = fields.Char('Work Phone')
    mobile_phone = fields.Char('Work Mobile')
    work_email = fields.Char('Work Email')
    work_location = fields.Char('Work Location')
    user_id = fields.Many2one('res.users')
    resource_id = fields.Many2one('resource.resource')
    resource_calendar_id = fields.Many2one('resource.calendar', domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    parent_id = fields.Many2one('hr.employee', 'Manager', domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    coach_id = fields.Many2one(
        'hr.employee', 'Coach', compute='_compute_coach', store=True, readonly=False,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help='Select the "Employee" who is the coach of this employee.\n'
             'The "Coach" has no specific rights or responsibilities by default.')
    tz = fields.Selection(
        string='Timezone', related='resource_id.tz', readonly=False,
        help="This field is used in order to define in which timezone the resources will work.")
    hr_presence_state = fields.Selection([
        ('present', 'At Work'),
        ('absent', 'Off'),
        ('to_define', 'To Be Checked')], compute='_compute_presence_state', default='to_define')
    must_be_at_work = fields.Boolean(compute='_compute_must_be_at_work', help="Now, the user must be at work based on his calendar.")
    last_activity = fields.Date(compute="_compute_last_activity")
    last_activity_time = fields.Char(compute="_compute_last_activity")

    @api.depends('user_id.im_status')
    def _compute_presence_state(self):
        """
        This method is overritten in several other modules which add additional
        presence criterions. e.g. hr_attendance, hr_holidays
        """
        self.hr_presence_state = 'to_define'

    def _compute_must_be_at_work(self):
        for tz in set(self.mapped('tz')):
            employee_ids = self.filtered(lambda employee: employee.tz == tz)
            now_tz = fields.Datetime.now().astimezone(timezone(tz)).replace(tzinfo=None)
            valid_calendar = employee_ids.resource_calendar_id._get_calendar_including_time(now_tz)
            employee_at_work = employee_ids.filtered(lambda e: e.resource_calendar_id in valid_calendar)
            employee_at_work.must_be_at_work = True
            (employee_ids - employee_at_work).must_be_at_work = False

    @api.depends('user_id')
    def _compute_last_activity(self):
        presences = self.env['bus.presence'].search_read([('user_id', 'in', self.mapped('user_id').ids)], ['user_id', 'last_presence'])
        # transform the result to a dict with this format {user.id: last_presence}
        presences = {p['user_id'][0]: p['last_presence'] for p in presences}

        for employee in self:
            tz = employee.tz
            last_presence = presences.get(employee.user_id.id, False)
            if last_presence:
                last_activity_datetime = last_presence.replace(tzinfo=UTC).astimezone(timezone(tz)).replace(tzinfo=None)
                employee.last_activity = last_activity_datetime.date()
                if employee.last_activity == fields.Date.today():
                    employee.last_activity_time = format_time(self.env, last_activity_datetime, time_format='short')
                else:
                    employee.last_activity_time = False
            else:
                employee.last_activity = False
                employee.last_activity_time = False

    @api.depends('parent_id')
    def _compute_coach(self):
        for employee in self:
            manager = employee.parent_id
            previous_manager = employee._origin.parent_id
            if manager and (employee.coach_id == previous_manager or not employee.coach_id):
                employee.coach_id = manager
            elif not employee.coach_id:
                employee.coach_id = False

    def _get_placeholder_filename(self, field=None):
        image_fields = ['image_%s' % size for size in [1920, 1024, 512, 256, 128]]
        if field in image_fields and not self:
            return 'base/static/img/user-slash.png'
        return super()._get_placeholder_filename(field=field)
