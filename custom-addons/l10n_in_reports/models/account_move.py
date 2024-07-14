# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_in_transaction_type = fields.Selection(
        selection=[
            ("inter_state", "Inter State"),
            ("intra_state", "Intra State"),
        ],
        string="Indian Transaction Type",
        compute="_compute_l10n_in_transaction_type",
        store=True,
    )

    @api.depends("country_code", "l10n_in_state_id", "company_id")
    def _compute_l10n_in_transaction_type(self):
        for move in self:
            if move.country_code == "IN":
                if move.l10n_in_state_id and move.l10n_in_state_id == move.company_id.state_id:
                    move.l10n_in_transaction_type = 'intra_state'
                else:
                    move.l10n_in_transaction_type = 'inter_state'
            else:
                move.l10n_in_transaction_type = False
