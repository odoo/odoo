# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    l10n_co_edi_tax_regime = fields.Selection(
        selection=[
            ('common', 'Regimen Comun'),
            ('simple', 'Regimen Simple (SIMPLE)'),
            ('not_responsible', 'No Responsable de IVA'),
        ],
        string='CO Tax Regime Filter',
        help='If set, this fiscal position only auto-applies to partners with '
             'this Colombian tax regime.',
    )
    l10n_co_edi_gran_contribuyente = fields.Selection(
        selection=[
            ('yes', 'Gran Contribuyente only'),
            ('no', 'Non-Gran Contribuyente only'),
        ],
        string='CO Gran Contribuyente Filter',
        help='If set, filter auto-apply by whether the partner is a Gran Contribuyente.',
    )

    def _get_fpos_validation_functions(self, partner):
        functions = super()._get_fpos_validation_functions(partner)
        if self.env.company.country_id.code != 'CO':
            return functions

        def _co_tax_classification_match(fpos):
            # Tax regime filter
            if fpos.l10n_co_edi_tax_regime:
                if fpos.l10n_co_edi_tax_regime != partner.l10n_co_edi_tax_regime:
                    return False
            # Gran Contribuyente filter
            if fpos.l10n_co_edi_gran_contribuyente:
                is_gc = partner.l10n_co_edi_gran_contribuyente
                if fpos.l10n_co_edi_gran_contribuyente == 'yes' and not is_gc:
                    return False
                if fpos.l10n_co_edi_gran_contribuyente == 'no' and is_gc:
                    return False
            return True

        return [_co_tax_classification_match] + functions
