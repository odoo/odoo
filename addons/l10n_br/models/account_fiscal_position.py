# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models

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

    def _get_fpos_validation_functions(self, partner):
        functions = super()._get_fpos_validation_functions(partner)
        company = self.env.company
        if company.country_id.code == 'BR' and partner.country_id.code == 'BR':
            # Taxation in Brazil depends on both the state of the partner and the state of the company
            if company.state_id == partner.state_id:
                fp_type = 'internal'
            elif company.state_id.code in SOUTH_SOUTHEAST and partner.state_id.code in NORTH_NORTHEAST_MIDWEST:
                fp_type = 'ss_nnm'
            else:
                fp_type = 'interstate'
            functions.append(lambda fpos: fpos.l10n_br_fp_type == fp_type)
        return functions
