# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrEmployeeBase(models.AbstractModel):
    _name = "hr.employee.base"
    _description = "Basic Employee"
    _order = 'name'

    name = fields.Char()
    active = fields.Boolean("Active")
    color = fields.Integer('Color Index', default=0)
    department_id = fields.Many2one('hr.department', 'Department')
    job_id = fields.Many2one('hr.job', 'Job Position')
    job_title = fields.Char("Job Title")
    company_id = fields.Many2one('res.company', 'Company')
    address_id = fields.Many2one('res.partner', 'Work Address')
    work_phone = fields.Char('Work Phone')
    mobile_phone = fields.Char('Work Mobile')
    work_email = fields.Char('Work Email')
    work_location = fields.Char('Work Location')
    user_id = fields.Many2one('res.users')
    resource_id = fields.Many2one('resource.resource')
    resource_calendar_id = fields.Many2one('resource.calendar')
    hr_presence_state = fields.Selection([
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('to_define', 'To Define')], compute='_compute_presence_state', default='to_define')
    last_activity = fields.Date(compute="_compute_last_activity")

    @api.depends('user_id.im_status')
    def _compute_presence_state(self):
        """
        This method is overritten in several other modules which add additional
        presence criterions. e.g. hr_attendance, hr_holidays
        """
        # Check on login
        check_login = self.env['ir.config_parameter'].sudo().get_param('hr.hr_presence_control_login')
        for employee in self:
            state = 'to_define'
            if check_login:
                if employee.user_id.im_status == 'online':
                    state = 'present'
                elif employee.user_id.im_status == 'offline':
                    state = 'absent'
            employee.hr_presence_state = state

    @api.depends('user_id')
    def _compute_last_activity(self):
        presences = self.env['bus.presence'].search_read([('user_id', 'in', self.mapped('user_id').ids)], ['user_id', 'last_presence'])
        # transform the result to a dict with this format {user.id: last_presence}
        presences = {p['user_id']: p['last_presence'] for p in presences}

        for employee in self:
            employee.last_activity = presences.get(employee.user_id.id, False)
