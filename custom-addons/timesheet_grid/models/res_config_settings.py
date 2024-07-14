# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    reminder_user_allow = fields.Boolean("Employee Reminder", related='company_id.timesheet_mail_employee_allow', readonly=False)
    reminder_user_delay = fields.Integer("Days to Remind User", related='company_id.timesheet_mail_employee_delay', readonly=False,
        help="Numbers of days after the end of the week/month after which an automatic email reminder will be sent to timesheet users that still have timesheets to encode (according to their working hours).")
    reminder_user_interval = fields.Selection(string='User Reminder Frequency', required=True,
        related='company_id.timesheet_mail_employee_interval', readonly=False)

    reminder_allow = fields.Boolean("Approver Reminder", related='company_id.timesheet_mail_allow', readonly=False)
    reminder_delay = fields.Integer("Days to Remind Approver", related='company_id.timesheet_mail_delay', readonly=False,
        help="Number of days after the end of the week/month after which an automatic email reminder will be sent to timesheet managers that still have timesheets to validate.")
    reminder_interval = fields.Selection(string='Approver Reminder Frequency', required=True,
        related='company_id.timesheet_mail_interval', readonly=False)
    timesheet_min_duration = fields.Integer('Minimal Duration', default=15, config_parameter='timesheet_grid.timesheet_min_duration')
    timesheet_rounding = fields.Integer('Round up', default=15, config_parameter='timesheet_grid.timesheet_rounding')
