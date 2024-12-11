# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models


class UoM(models.Model):
    _inherit = 'uom.uom'

    def _get_l10n_pk_edi_uom_codes(self):
        return [
            ('U1000069', _("[U1000069] Unit")),
            ('U1000057', _("[U1000057] Dozen")),
            ('U1000063', _("[U1000063] KGM")),
            ('U1000059', _("[U1000059] Gram")),
            ('U1000003', _("[U1000003] Ton")),
            ('U1000048', _("[U1000048] Meter")),
            ('U1000077', _("[U1000077] Square Meter")),
            ('U1000009', _("[U1000009] Litre")),
            ('U1000055', _("[U1000055] Cubic Meter")),
            ('U1000065', _("[U1000065] Pound")),
            ('U1000083', _("[U1000083] Foot")),
            ('U1000075', _("[U1000075] Square Foot")),
            ('U1000061', _("[U1000061] Gallon")),
            ('U1000088', _("[U1000088] Other")),
        ]

    l10n_pk_uom_code = fields.Selection(selection=_get_l10n_pk_edi_uom_codes, string="UoM")
