# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

L10N_HU_UOM_CODE = [
    ("PIECE", "Piece"),
    ("KILOGRAM", "Kilogram"),
    ("TON", "Ton"),
    ("KWH", "Kilowatt hour"),
    ("DAY", "Day"),
    ("HOUR", "Hour"),
    ("MINUTE", "Minute"),
    ("MONTH", "Month"),
    ("LITRE", "Litre"),
    ("KILOMETER", "Kilometer"),
    ("CUBIC_METER", "Cubic meter"),
    ("METER", "Meter"),
    ("LINEAR_METER", "Linear meter"),
    ("CARTON", "Carton"),
    ("PACK", "Package"),
]


class ProductUoM(models.Model):
    _inherit = "uom.uom"

    l10n_hu_measure_unit_code = fields.Selection(L10N_HU_UOM_CODE, "Measure unit code")
