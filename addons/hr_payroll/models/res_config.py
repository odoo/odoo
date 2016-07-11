# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrPayrollConfigSettings(models.TransientModel):
    _name = 'hr.payroll.config.settings'
    _inherit = 'res.config.settings'

    module_hr_payroll_account = fields.Boolean(string='Link your payroll to accounting system',
        help="Create journal entries from payslips")
