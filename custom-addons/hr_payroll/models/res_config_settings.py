# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_l10n_fr_hr_payroll = fields.Boolean(string='French Payroll')
    module_l10n_be_hr_payroll = fields.Boolean(string='Belgium Payroll')
    module_l10n_in_hr_payroll = fields.Boolean(string='Indian Payroll')
    module_hr_payroll_account = fields.Boolean(string='Payroll with Accounting')
    module_hr_payroll_account_sepa = fields.Boolean(string='Payroll with SEPA payment')
    group_payslip_display = fields.Boolean(implied_group="hr_payroll.group_payslip_display")
