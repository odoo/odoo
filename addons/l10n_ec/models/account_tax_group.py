# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

_TYPE_EC = [
    ("vat12", "VAT 12%"),
    ("vat14", "VAT 14%"),
    ("zero_vat", "VAT 0%"),
    ("not_charged_vat", "VAT Not Charged"),
    ("exempt_vat", "VAT Exempt"),
    ("withhold_vat", "VAT Withhold"),
    ("withhold_income_tax", "Profit Withhold"),
    ("ice", "Special Consumptions Tax (ICE)"),
    ("irbpnr", "Plastic Bottles (IRBPNR)"),
    ("outflows_tax", "Exchange Outflows"),
    ("other", "Others"),
]


class AccountTaxGroup(models.Model):
    _inherit = "account.tax.group"

    l10n_ec_type = fields.Selection(
        _TYPE_EC, string="Type Ecuadorian Tax", help="Ecuadorian taxes subtype"
    )
