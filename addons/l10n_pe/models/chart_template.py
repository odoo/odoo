# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class AccountTaxTemplate(models.Model):
    _inherit = 'account.tax.template'

    def _get_tax_vals(self, company, tax_template_to_tax):
        val = super()._get_tax_vals(company, tax_template_to_tax)
        val.update({
            'l10n_pe_edi_tax_code': self.l10n_pe_edi_tax_code,
            'l10n_pe_edi_unece_category': self.l10n_pe_edi_unece_category,
        })
        return val
