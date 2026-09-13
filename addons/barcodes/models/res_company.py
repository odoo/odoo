from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    def _default_nomenclature_id(self):
        return self.env.ref(
            "barcodes.default_barcode_nomenclature", raise_if_not_found=False
        )

    nomenclature_id = fields.Many2one(
        comodel_name="barcode.nomenclature",
        default=_default_nomenclature_id,
    )
