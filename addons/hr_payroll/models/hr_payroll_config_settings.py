# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrPayrollConfigSettings(models.TransientModel):
    _name = 'hr.payroll.config.settings'
    _inherit = 'res.config.settings'

    module_hr_timesheet = fields.Boolean(string='Timesheets')
    module_website_sign = fields.Boolean(string='Online Signatures')
    module_account_accountant = fields.Boolean(string='Account Accountant')
    module_l10n_fr_hr_payroll = fields.Boolean(string='French Payroll')
    module_l10n_be_hr_payroll = fields.Boolean(string='Belgium Payroll')
    module_l10n_in_hr_payroll = fields.Boolean(string='Indian Payroll')
