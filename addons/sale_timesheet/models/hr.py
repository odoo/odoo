# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # FIXME: this field should be in module hr_timesheet, not sale_timesheet
    timesheet_cost = fields.Float('Timesheet Cost', default=0.0)
    account_id = fields.Many2one('account.account', string='Account')
