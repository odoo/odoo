# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.onchange('journal_id')
    def _onchange_journal(self):
        res = super(AccountMove, self)._onchange_journal()
        default_l10n_in_unit_id = self.journal_id.l10n_in_unit_id or self.env.user._get_default_unit()
        purchase = self.line_ids.mapped('purchase_line_id.order_id')
        self.l10n_in_unit_id = purchase and purchase.l10n_in_unit_id or default_l10n_in_unit_id
        return res
