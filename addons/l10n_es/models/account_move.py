# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_es_is_simplified = fields.Boolean("Is Simplified",
                                           compute="_compute_l10n_es_is_simplified", readonly=False, store=True)

    @api.depends('partner_id', 'amount_total_signed')
    def _compute_l10n_es_is_simplified(self):
        simplified_partner = self.env.ref('l10n_es.partner_simplified', raise_if_not_found=False)
        for move in self:
            move.l10n_es_is_simplified = (move.country_code == 'ES') and (
                (not move.partner_id and move.move_type in ('in_receipt', 'out_receipt'))
                or (simplified_partner and move.partner_id == simplified_partner)
                or (move.move_type in ('out_invoice', 'out_refund')
                    and not move.commercial_partner_id.vat
                    and move.currency_id.compare_amounts(abs(move.amount_total_signed), 400) <= 0  # standard simplified invoice limit
                    and move.commercial_partner_id.country_id in self.env.ref('base.europe').country_ids
                )
            )
