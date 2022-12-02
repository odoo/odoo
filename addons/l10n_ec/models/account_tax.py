# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

L10N_EC_TAXSUPPORTS = [
    ('01', '01 Tax credit for VAT declaration (services and goods other than inventories and fixed assets)'),
    ('02', '02 Cost or Expense for IR declaration (services and goods other than inventories and fixed assets)'),
    ('03', '03 Fixed Asset - Tax Credit for VAT return'),
    ('04', '04 Fixed Asset - Cost or Expense for IR declaration'),
    ('05', '05 Settlement of travel, lodging and food expenses IR expenses (on behalf of employees and not of the company)'),
    ('06', '06 Inventory - Tax Credit for VAT return'),
    ('07', '07 Inventory - Cost or Expense for IR declaration'),
    ('08', '08 Amount paid to request Expense Reimbursement (intermediary)'),
    ('09', '09 Claims Reimbursement'),
    ('10', '10 Distribution of Dividends, Benefits or Profits'),
    ('15', '15 Payments made for own and third-party consumption of digital services'),
    ('00', '00 Special cases whose support does not apply to the above options')
]


class AccountTax(models.Model):

    _inherit = "account.tax"

    l10n_ec_code_base = fields.Char(
        string="Code base",
        help="Tax declaration code of the base amount prior to the calculation of the tax",
    )
    l10n_ec_code_applied = fields.Char(
        string="Code applied",
        help="Tax declaration code of the resulting amount after the calculation of the tax",
    )
    l10n_ec_code_ats = fields.Char(
        string="Code ATS",
        help="Tax Identification Code for the Simplified Transactional Annex",
    )
    l10n_ec_code_taxsupport = fields.Selection(
        L10N_EC_TAXSUPPORTS,
        string='Tax Support',
        help='Indicates if the purchase invoice supports tax credit or cost or expenses, conforming table 5 of ATS'
    )


class AccountTaxTemplate(models.Model):

    _inherit = "account.tax.template"

    def _get_tax_vals(self, company, tax_template_to_tax):
        vals = super(AccountTaxTemplate, self)._get_tax_vals(
            company, tax_template_to_tax
        )
        vals.update(
            {
                "l10n_ec_code_base": self.l10n_ec_code_base,
                "l10n_ec_code_applied": self.l10n_ec_code_applied,
                "l10n_ec_code_ats": self.l10n_ec_code_ats,
                "l10n_ec_code_taxsupport": self.l10n_ec_code_taxsupport,
            }
        )
        return vals

    l10n_ec_code_base = fields.Char(
        string="Code base",
        help="Tax declaration code of the base amount prior to the calculation of the tax",
    )
    l10n_ec_code_applied = fields.Char(
        string="Code applied",
        help="Tax declaration code of the resulting amount after the calculation of the tax",
    )
    l10n_ec_code_ats = fields.Char(
        string="Code ATS",
        help="Tax Identification Code for the Simplified Transactional Annex",
    )
    l10n_ec_code_taxsupport = fields.Selection(
        L10N_EC_TAXSUPPORTS,
        string='Tax Support',
        help='Indicates if the purchase invoice supports tax credit or cost or expenses, conforming table 5 of ATS'
    )
