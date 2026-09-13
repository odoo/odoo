from odoo import fields, models


class L10n_Eg_EdiUomCode(models.Model):
    _name = "l10n_eg_edi.uom.code"
    _description = "ETA code for the unit of measures"

    name = fields.Char(
        translate=True,
        required=True,
    )
    code = fields.Char(required=True)


class UomUom(models.Model):
    _inherit = "uom.uom"

    l10n_eg_unit_code_id = fields.Many2one(
        comodel_name="l10n_eg_edi.uom.code",
        string="ETA Unit Code",
        help="This is the type of unit according to egyptian tax authority",
    )
