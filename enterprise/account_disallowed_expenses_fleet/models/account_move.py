# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.depends('account_id.disallowed_expenses_category_id')
    def _compute_need_vehicle(self):
        for record in self:
            record.need_vehicle = record.account_id.disallowed_expenses_category_id.sudo().car_category and record.move_id.move_type == 'in_invoice'

    @api.model
    def _get_deferred_lines_values(self, account_id, balance, ref, analytic_distribution, line):
        deferred_lines_values = super()._get_deferred_lines_values(account_id, balance, ref, analytic_distribution, line)
        return {
            **deferred_lines_values,
            'vehicle_id': int(line['vehicle_id'] or 0) or None,
        }

    @api.model
    def _get_deferred_amounts_by_line_values(self, line):
        values = super()._get_deferred_amounts_by_line_values(line)
        values['vehicle_id'] = int(line['vehicle_id'] or 0) or None
        return values
