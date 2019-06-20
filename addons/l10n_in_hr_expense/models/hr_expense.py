# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class HrExpense(models.Model):
    _inherit = "hr.expense"

    l10n_in_unit_id = fields.Many2one('res.partner', string="Operating Unit", ondelete="restrict", states={'draft': [('readonly', False)], 'refused': [('readonly', False)]})

    @api.onchange('company_id')
    def _l10n_in_onchange_company_id(self):
        default_unit = self.l10n_in_unit_id or self.env.user._get_default_unit()
        if default_unit not in self.company_id.l10n_in_unit_ids:
            self.l10n_in_unit_id = self.company_id.partner_id

    def _prepare_move_values(self):
        self.ensure_one()
        move_values = super()._prepare_move_values()
        move_values['l10n_in_unit_id'] = self.l10n_in_unit_id.id
        return move_values

    def prepare_payment_vals(self, move_line_dst):
        self.ensure_one()
        payment_vals = super().prepare_payment_vals(move_line_dst)
        payment_vals['l10n_in_unit_id'] = self.l10n_in_unit_id.id
        return payment_vals
