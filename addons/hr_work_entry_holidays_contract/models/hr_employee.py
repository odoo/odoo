# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import models, api

class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    @api.depends('first_contract_date')
    def _compute_date_start_work(self):
        # override, this is used in hr holidays to calculate the accrual allocations
        for employee in self:
            employee.start_work_date = employee.first_contract_date
