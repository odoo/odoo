# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models

SOUTH_SOUTHEAST = {"PR", "RS", "SC", "SP", "ES", "MG", "RJ"}
NORTH_NORTHEAST_MIDWEST = {
    "AC", "AP", "AM", "PA", "RO", "RR", "TO", "AL", "BA", "CE",
    "MA", "PB", "PE", "PI", "RN", "SE", "DF", "GO", "MT", "MS"
}


class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    l10n_br_fp_type = fields.Selection(
        selection=[
            ('internal', 'Internal'),
            ('ss_nnm', 'South/Southeast selling to North/Northeast/Midwest'),
            ('interstate', 'Other interstate'),
        ],
        string='Interstate Fiscal Position Type',
    )

    @api.model
    def _get_fiscal_position(self, partner, delivery=None):
        if not delivery:
            delivery = partner

        if self.env.company.country_id.code != "BR" or delivery.country_id.code != 'BR':
            return super()._get_fiscal_position(partner, delivery=delivery)

        # manually set fiscal position on partner has a higher priority
        manual_fiscal_position = delivery.property_account_position_id or partner.property_account_position_id
        if manual_fiscal_position:
            return manual_fiscal_position

        # Taxation in Brazil depends on both the state of the partner and the state of the company
        if self.env.company.state_id == delivery.state_id:
            return self.search([('l10n_br_fp_type', '=', 'internal'), ('company_id', '=', self.env.company.id)], limit=1)
        if self.env.company.state_id.code in SOUTH_SOUTHEAST and delivery.state_id.code in NORTH_NORTHEAST_MIDWEST:
            return self.search([('l10n_br_fp_type', '=', 'ss_nnm'), ('company_id', '=', self.env.company.id)], limit=1)
        return self.search([('l10n_br_fp_type', '=', 'interstate'), ('company_id', '=', self.env.company.id)], limit=1)
