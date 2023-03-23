# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import UserError

ACCOUNT_TAX_TEMPLATES = ['l10n_ec.tax_vat_510_sup_01',
'l10n_ec.tax_vat_510_sup_05',
'l10n_ec.tax_vat_510_sup_06',
'l10n_ec.tax_vat_510_sup_15',
'l10n_ec.tax_vat_511_sup_03',
'l10n_ec.tax_vat_512_sup_04',
'l10n_ec.tax_vat_512_sup_05',
'l10n_ec.tax_vat_512_sup_07',
'l10n_ec.tax_vat_513_sup_01',
'l10n_ec.tax_vat_514_sup_06',
'l10n_ec.tax_vat_515_sup_03',
'l10n_ec.tax_vat_516_sup_07',
'l10n_ec.tax_vat_517_sup_02',
'l10n_ec.tax_vat_517_sup_04',
'l10n_ec.tax_vat_517_sup_05',
'l10n_ec.tax_vat_517_sup_07',
'l10n_ec.tax_vat_517_sup_15',
'l10n_ec.tax_vat_518_sup_02',
'l10n_ec.tax_vat_541_sup_02',
'l10n_ec.tax_vat_542_sup_02',
'l10n_ec.tax_vat_510_08_sup_01',
'l10n_ec.tax_vat_545_sup_08',
'l10n_ec.tax_vat_545_sup_08_vat0',
'l10n_ec.tax_vat_545_sup_08_vat_exempt',
'l10n_ec.tax_vat_545_sup_08_vat_not_charged',
'l10n_ec.tax_vat_545_sup_09',
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

    @api.ondelete(at_uninstall=False)
    def _unlink_except_last_account_template(self):
        if self.get_external_id()[self.id] in ACCOUNT_TAX_TEMPLATES:
            raise UserError(_("You cannot delete account template %s as it is used in another module but you can archive it.") % self.name)
