# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api

L10N_HU_TAX_TYPE = [
    ("VAT", "Normal VAT (percent based)"),
    ("VAT-AAM", "AAM - Personal tax exemption"),
    ("VAT-TAM", 'TAM - "tax-exempt activity" or tax-exempt due to being in public interest or special in nature'),
    ("VAT-KBAET", "KBAET - intra-Community exempt supply, without new means of transport"),
    ("VAT-KBAUK", "KBAUK - tax-exempt, intra-Community sales of new means of transport"),
    ("VAT-EAM", "EAM - tax-exempt, extra-Community sales of goods (export of goods to a non-EU country)"),
    ("VAT-NAM", "NAM - tax-exempt on other grounds related to international transactions"),
    ("VAT-ATK", "ATK - Outside the scope of VAT"),
    (
        "VAT-EUFAD37",
        "EUFAD37 - Based on section 37 of the VAT Act, a reverse charge transaction carried out in another Member State",
    ),
    (
        "VAT-EUFADE",
        "EUFADE - Reverse charge transaction carried out in another Member State, not subject to Section 37 of the VAT Act",
    ),
    ("VAT-EUE", "EUE - Non-reverse charge transaction performed in another Member State"),
    ("VAT-HO", "HO - Transaction in a third country"),
]


class AccountTax(models.Model):
    _inherit = "account.tax"

    l10n_hu_tax_type = fields.Selection(
        L10N_HU_TAX_TYPE,
        string="Hungarian Tax Type",
        help="Precise identification of the tax for the hungarian authority",
    )
    l10n_hu_tax_reason = fields.Char("Hungarian Tax Description")

    @api.onchange("l10n_hu_tax_type")
    def l10n_hu_change_vat_type(self):
        for tax in self:
            if tax.l10n_hu_tax_type == "VAT":
                tax.l10n_hu_tax_reason = None
            if tax.l10n_hu_tax_type == "VAT-AAM":
                tax.l10n_hu_tax_reason = "AAM Alanyi adómentes"
            if tax.l10n_hu_tax_type == "VAT-TAM":
                tax.l10n_hu_tax_reason = "TAM Tárgyi adómentes"
            if tax.l10n_hu_tax_type == "VAT-KBAET":
                tax.l10n_hu_tax_reason = "KBAET EU-ba eladás - ÁFA tv.89.§"
            if tax.l10n_hu_tax_type == "VAT-KBAUK":
                tax.l10n_hu_tax_reason = "KBAUK Új közlekedési eszköz EU-n belülre - ÁFA tv.89.§(2)"
            if tax.l10n_hu_tax_type == "VAT-EAM":
                tax.l10n_hu_tax_reason = "EAM Termékexport 3.országba - ÁFA tv.98-109.§"
            if tax.l10n_hu_tax_type == "VAT-NAM":
                tax.l10n_hu_tax_reason = "NAM egyéb export ügylet ÁFA tv 110-118.§"
            if tax.l10n_hu_tax_type == "VAT-ATK":
                tax.l10n_hu_tax_reason = "ATK ÁFA tárgyán kívüli - ÁFA tv.2-3.§"
            if tax.l10n_hu_tax_type == "VAT-EUFAD37":
                tax.l10n_hu_tax_reason = "EUFAD37 ÁFA tv. 37.§ (1) Fordított ÁFA másik EU-s országban"
            if tax.l10n_hu_tax_type == "VAT-EUFADE":
                tax.l10n_hu_tax_reason = "EUFADE Fordított ÁFA másik EU-s országban nem ÁFA tv. 37.§ (1)"
            if tax.l10n_hu_tax_type == "VAT-EUE":
                tax.l10n_hu_tax_reason = "EUE 2.EU-s országban teljesített eladás"
            if tax.l10n_hu_tax_type == "VAT-HO":
                tax.l10n_hu_tax_reason = "HO Szolgáltatás 3.országba"


class AccountTaxTemplate(models.Model):
    _inherit = "account.tax.template"

    l10n_hu_tax_type = fields.Selection(
        L10N_HU_TAX_TYPE,
        string="Hungarian Tax Type",
        help="Precise identification of the tax for the hungarian authority",
    )
    l10n_hu_tax_reason = fields.Char("Hungarian Tax Description")

    def _get_tax_vals(self, company, tax_template_to_tax):
        vals = super(AccountTaxTemplate, self)._get_tax_vals(company, tax_template_to_tax)
        vals.update(
            {
                "l10n_hu_tax_type": self.l10n_hu_tax_type,
                "l10n_hu_tax_reason": self.l10n_hu_tax_reason,
            }
        )
        return vals
