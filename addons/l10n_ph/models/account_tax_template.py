# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountTaxTemplate(models.Model):
    _inherit = "account.tax.template"

    l10n_ph_atc = fields.Char("Philippines ATC")

    def _get_tax_vals(self, company, tax_template_to_tax):
        val = super()._get_tax_vals(company, tax_template_to_tax)
        val.update({"l10n_ph_atc": self.l10n_ph_atc})
        return val
