# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    holiday_id = fields.Many2one("hr.leave", string='Leave Request')
    global_leave_id = fields.Many2one("resource.calendar.leaves", string="Global Time Off", ondelete='cascade')

    @api.ondelete(at_uninstall=False)
    def _unlink_except_linked_leave(self):
        if any(line.holiday_id for line in self):
            raise UserError(_('You cannot delete timesheets linked to time off. Please, cancel the time off instead.'))
