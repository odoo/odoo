# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

_TYPE_EC = [
    ("vat05", "VAT 5%"),
    ("vat08", "VAT 8%"),
    ("vat12", "VAT 12%"),
    ("vat13", "VAT 13%"),
    ("vat14", "VAT 14%"),
    ("vat15", "VAT 15%"),
    ("zero_vat", "VAT 0%"),
    ("not_charged_vat", "VAT Not Charged"),
    ("exempt_vat", "VAT Exempt"),
    ("ice", "Special Consumptions Tax (ICE)"),
    ("irbpnr", "Plastic Bottles (IRBPNR)"),
    ("withhold_vat_sale", "VAT Withhold on Sales"),
    ("withhold_vat_purchase", "VAT Withhold on Purchases"),
    ("withhold_income_sale", "Profit Withhold on Sales"),
    ("withhold_income_purchase", "Profit Withhold on Purchases"),
    ("outflows_tax", "Exchange Outflows"),
    ("other", "Others"),
]


class AccountTaxGroup(models.Model):
    _inherit = "account.tax.group"

    l10n_ec_type = fields.Selection(
        _TYPE_EC, string="Type Ecuadorian Tax", help="Ecuadorian taxes subtype"
    )
