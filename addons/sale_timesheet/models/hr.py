# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import models, fields


class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    # FIXME: this field should be in module hr_timesheet, not sale_timesheet
    timesheet_cost = fields.Float(string='Timesheet Cost', default=0.0)
