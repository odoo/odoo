# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AccountTax(models.Model):
    _name = 'account.tax'
    _inherit = 'account.tax'

    l10n_cl_sii_code = fields.Integer('SII Code')


class AccountTaxTemplate(models.Model):
    _name = 'account.tax.template'
    _inherit = 'account.tax.template'

    l10n_cl_sii_code = fields.Integer('SII Code')

    def _get_tax_vals(self, company, tax_template_to_tax):
        self.ensure_one()
        vals = super(AccountTaxTemplate, self)._get_tax_vals(company, tax_template_to_tax)
        vals.update({
            'l10n_cl_sii_code': self.l10n_cl_sii_code,
        })
        if self.tax_group_id:
            vals['tax_group_id'] = self.tax_group_id.id
        return vals
