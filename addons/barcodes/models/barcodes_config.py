from odoo import fields, models


class BarcodesConfig(models.Model):
    _name = "barcodes.config"
    _description = "A company's barcodes configuration"
    _inherit = ["mixin.company.config"]

    nomenclature_id = fields.Many2one(
        comodel_name="barcode.nomenclature",
        default=lambda self: self._default_nomenclature_id(),
    )

    def _default_nomenclature_id(self):
        return self.env.ref(
            "barcodes.default_barcode_nomenclature", raise_if_not_found=False
        )
