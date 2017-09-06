# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    holiday_id = fields.Many2one("hr.holidays", string='Leave Request')

    @api.multi
    def unlink(self):
        if any(line.holiday_id for line in self):
            raise UserError(_('You cannot delete timesheet lines attached to a leaves. Please cancel the leaves instead.'))
        return super(AccountAnalyticLine, self).unlink()
