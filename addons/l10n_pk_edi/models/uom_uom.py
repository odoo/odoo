# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models


class UoM(models.Model):
    _inherit = 'uom.uom'

    l10n_pk_uom_code = fields.Selection(
        selection = [
            ('U1000003', "MT"),
            ('U1000005', "SET"),
            ('U1000006', "KWH"),
            ('U1000008', "40KG"),
            ('U1000009', "Liter"),
            ('U1000011', "Sq Yard"),
            ('U1000012', "Bag"),
            ('U1000013', "KG"),
            ('U1000046', "MMBTU"),
            ('U1000048', "Meter"),
            ('U1000053', "Carat"),
            ('U1000055', "Cubic Metre"),
            ('U1000057', "Dozen"),
            ('U1000059', "Gram"),
            ('U1000061', "Gallon"),
            ('U1000063', "Kilogram"),
            ('U1000065', "Pound"),
            ('U1000067', "Timber Logs"),
            ('U1000069', "Pieces"),
            ('U1000071', "Packs"),
            ('U1000073', "Pair"),
            ('U1000075', "Square Foot"),
            ('U1000077', "Square Metre"),
            ('U1000079', "Thousand Unit"),
            ('U1000081', "Mega Watt"),
            ('U1000083', "Foot"),
            ('U1000085', "Barrels"),
            ('U1000087', "Number"),
            ('U1000004', "Bill of lading"),
            ('U1000088', "Others"),
        ],
        string="UoM Type (FBR)",
        default="U1000069",
        help="Unit of Measure (UoM) is a standard unit to express quantities of stock or products.",
        required=True,
    )
