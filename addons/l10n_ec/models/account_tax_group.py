# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

_TYPE_EC = [
    ("vat08", "IVA 8%"),
    ("vat12", "IVA 12%"),
    ("vat14", "IVA 14%"),
    ("zero_vat", "IVA 0%"),
    ("not_charged_vat", "No Grava IVA"),
    ("exempt_vat", "Exento de IVA"),
    ("ice", "Impuesto a los Consumos Especiales (ICE)"),
    ("irbpnr", "Botellas de Plástico (IRBPNR)"),
    ("withhold_vat_sale", "Retención de IVA en Ventas"),
    ("withhold_vat_purchase", "Retención de IVA en Compras"),
    ("withhold_income_sale", "Retención de Renta en Ventas"),
    ("withhold_income_purchase", "Retención de Renta en Compras"),
    ("outflows_tax", "Impuesto a la Salida de Divisas"),
    ("other", "Otros"),
]


class AccountTaxGroup(models.Model):
    _inherit = "account.tax.group"

    l10n_ec_type = fields.Selection(
        _TYPE_EC, string="Type Ecuadorian Tax", help="Ecuadorian taxes subtype"
    )
