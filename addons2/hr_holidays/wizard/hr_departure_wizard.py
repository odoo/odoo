# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import api, fields, models


class HrDepartureWizard(models.TransientModel):
    _inherit = 'hr.departure.wizard'

    cancel_leaves = fields.Boolean("Cancel Future Time Off", default=True,
        help="Cancel all time off after this date.")
    archive_allocation = fields.Boolean("Archive Employee Allocations", default=True,
        help="Remove employee from existing accrual plans.")

    def action_register_departure(self):
        super(HrDepartureWizard, self).action_register_departure()
        if self.cancel_leaves:
            future_leaves = self.env['hr.leave'].search([('employee_id', '=', self.employee_id.id), 
                                                         ('date_to', '>', self.departure_date),
                                                         ('state', '!=', 'refuse')])
            future_leaves.write({'state': 'refuse'})

        if self.archive_allocation:
            employee_allocations = self.env['hr.leave.allocation'].search([('employee_id', '=', self.employee_id.id)])
            employee_allocations.action_archive()
