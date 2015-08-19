# -*- coding: utf-8 -*-

from openerp import api, fields, models


class HrConfigSettings(models.TransientModel):
    _name = 'hr.config.settings'
    _inherit = 'res.config.settings'

    module_hr_timesheet_sheet = fields.Boolean(string='Allow timesheets validation by managers',
        help='This installs the module hr_timesheet_sheet.')
    module_hr_attendance = fields.Boolean(string='Install attendances feature',
        help='This installs the module hr_attendance.')
    module_hr_timesheet = fields.Boolean(string='Manage timesheets',
        help='This installs the module hr_timesheet.')
    module_hr_holidays = fields.Boolean(string='Manage holidays, leaves and allocation requests',
        help='This installs the module hr_holidays.')
    module_hr_expense = fields.Boolean(string='Manage employees expenses',
        help='This installs the module hr_expense.')
    module_hr_recruitment = fields.Boolean(string='Manage the recruitment process',
        help='This installs the module hr_recruitment.')
    module_hr_contract = fields.Boolean(string='Record contracts per employee',
        help ='This installs the module hr_contract.')
    module_hr_evaluation = fields.Boolean(string='Organize employees periodic evaluation',
        help='This installs the module hr_evaluation.')
    module_hr_gamification = fields.Boolean(string='Drive engagement with challenges and badges',
        help='This installs the module hr_gamification.')
    module_sale_contract = fields.Boolean(
        string='Allow invoicing based on timesheets (the sale application will be installed)',
        help='This installs the module sale_contract, which will install sales management too.')
    module_hr_payroll = fields.Boolean(string='Manage payroll',
        help='This installs the module hr_payroll.')
    module_website_hr_recruitment = fields.Boolean(string='Publish jobs on your website',
        help='This installs the module website_hr_recruitment')
    group_hr_attendance = fields.Boolean(string='Track attendances for all employees',
        implied_group='base.group_hr_attendance', help='Allocates attendance group to all users.')

    @api.onchange('module_hr_timesheet')
    def _onchange_module_hr_timesheet(self):
        ' module_hr_timesheet implies module_hr_attendance '
        if self.module_hr_timesheet:
            self.module_hr_attendance = True

    @api.onchange('module_hr_attendance')
    def _onchange_module_hr_attendance(self):
        ' module_hr_timesheet implies module_hr_attendance '
        if not self.module_hr_attendance:
            self.module_hr_timesheet = False
            self.group_hr_attendance = False

    @api.onchange('group_hr_attendance')
    def _onchange_group_hr_attendance(self):
        ' group_hr_attendance implies module_hr_attendance '
        if self.group_hr_attendance:
            self.module_hr_attendance = True
