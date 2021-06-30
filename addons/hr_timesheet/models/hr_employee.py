# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    timesheet_cost = fields.Monetary('Timesheet Cost', groups="hr.group_hr_user")
    overtime_cost = fields.Monetary('Overtime Cost', groups="hr.group_hr_user")
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
