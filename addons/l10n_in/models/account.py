# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_in_reverse_charge = fields.Boolean("Reverse charge",
                                            help="Tick this if this tax is reverse charge. Only for Indian accounting")


class AccountTaxTemplate(models.Model):
    _inherit = 'account.tax.template'

    l10n_in_reverse_charge = fields.Boolean("Reverse charge",
                                            help="Tick this if this tax is reverse charge. Only for Indian accounting")

    def _get_tax_vals(self, company, tax_template_to_tax):
        val = super(AccountTaxTemplate, self)._get_tax_vals(company, tax_template_to_tax)
        if self.tax_group_id:
            val['l10n_in_reverse_charge'] = self.l10n_in_reverse_charge
        return val