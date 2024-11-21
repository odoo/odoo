# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_es_is_simplified = fields.Boolean("Is Simplified",
                                           compute="_compute_l10n_es_is_simplified", readonly=False, store=True)

    @api.depends('partner_id')
    def _compute_l10n_es_is_simplified(self):
        simplified_partner = self.env.ref('l10n_es.partner_simplified', raise_if_not_found=False)
        for move in self:
            move.l10n_es_is_simplified = (
                (not move.partner_id and move.move_type in ('in_receipt', 'out_receipt')) or
                (simplified_partner and move.partner_id == simplified_partner)
            )

    def _l10n_es_is_dua(self):
        self.ensure_one()
        return any(t.l10n_es_type == 'dua' for t in self.invoice_line_ids.tax_ids.flatten_taxes_hierarchy())
