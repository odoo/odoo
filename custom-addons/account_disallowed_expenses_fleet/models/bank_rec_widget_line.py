# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class BankRecWidgetLine(models.Model):
    _inherit = 'bank.rec.widget.line'

    @api.depends('account_id')
    def _compute_vehicle_required(self):
        for line in self:
            line.vehicle_required = line.account_id and line.account_id.disallowed_expenses_category_id.car_category
