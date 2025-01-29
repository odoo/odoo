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

    def _get_fpos_ranking_functions(self, partner):
        if self.env.company.account_fiscal_country_id.code != "BR" or partner.country_id.code != 'BR':
            return super()._get_fpos_ranking_functions(partner)
        company_state = self.env.company.state_id
        delivery_state = partner.state_id
        if company_state == delivery_state:
            fp_type = 'internal'
        elif company_state in SOUTH_SOUTHEAST and delivery_state in NORTH_NORTHEAST_MIDWEST:
            fp_type = 'ss_nnm'
        else:
            fp_type = 'interstate'
        return super()._get_fpos_ranking_functions(partner) + [
            ('l10n_br_fp_type', lambda fpos: (not fpos.l10n_br_fp_type or (fpos.l10n_br_fp_type == fp_type and 2)))]

