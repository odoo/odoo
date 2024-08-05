# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models


class UoM(models.Model):
    _inherit = 'uom.uom'

    l10n_pk_uom_code = fields.Selection(
        selection=[
            ('U1000069', "Unit"),
            ('U1000057', "Dozen"),
            ('U1000063', "KGM"),
            ('U1000059', "Gram"),
            ('U1000003', "Ton"),
            ('U1000048', "Meter"),
            ('U1000077', "Square Meter"),
            ('U1000009', "Litre"),
            ('U1000055', "Cubic Meter"),
            ('U1000065', "Pound"),
            ('U1000083', "Foot"),
            ('U1000075', "Square Foot"),
            ('U1000061', "Gallon"),
            ('U1000088', "Other"),
        ],
        string="UoM Type (FBR)",
        help="Unit of Measure (UoM) is a standard unit to express quantities of stock or products."
    )
