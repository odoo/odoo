# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    holiday_id = fields.Many2one("hr.leave", string='Leave Request')

    @api.model
    def _get_leave_timesheet_protected_fields(self):
        return [
            'name',
            'project_id',
            'task_id',
            'account_id',
            'unit_amount',
            'user_id',
            'date',
            'employee_id',
        ]

    def write(self, values):
        if self.filtered('holiday_id') and any(f in values for f in self._get_leave_timesheet_protected_fields()):
            raise UserError(_('You cannot modify timesheet lines attached to a leave.'))
        return super(AccountAnalyticLine, self).write(values)

    def unlink(self):
        if self.filtered('holiday_id'):
            raise UserError(_('You cannot delete timesheet lines attached to a leave. Please cancel the leave instead.'))
        return super(AccountAnalyticLine, self).unlink()
