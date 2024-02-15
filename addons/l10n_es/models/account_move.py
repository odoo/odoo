# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_es_is_simplified = fields.Boolean("Is Simplified",
                                           compute="_compute_l10n_es_is_simplified", readonly=False, store=True)

    @api.depends(
        'partner_id',
        'partner_id.country_id',
        'partner_id.vat',
    )
    def _compute_l10n_es_is_simplified(self):
        simplified_partner = self.env.ref('l10n_es.partner_simplified', raise_if_not_found=False)
        for move in self.filtered_domain([('state', '!=', 'posted'), ('partner_id', '!=', False)]):
            partner = move.partner_id
            if partner == simplified_partner \
                or not partner.country_id \
                or partner.country_id.code == 'ES' and not partner.vat:

                move.l10n_es_is_simplified = True
            else:
                move.l10n_es_is_simplified = False
