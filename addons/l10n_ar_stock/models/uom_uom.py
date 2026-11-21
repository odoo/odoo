from odoo import fields, models


class UomUom(models.Model):
    _inherit = 'uom.uom'

    l10n_ar_arba_unit_code = fields.Char(
        string="ARBA Unit of Measure Code",
        help="Argentina: ARBA unit of measure code used to generate the COT based on the official nomenclature.",
    )
