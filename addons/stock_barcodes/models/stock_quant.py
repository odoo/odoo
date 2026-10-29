# Copyright 2023 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import models


class StockQuant(models.Model):
    _inherit = "stock.quant"

    def action_barcode_inventory_quant_unlink(self):
        self.with_context(inventory_mode=True).action_set_inventory_quantity_to_zero()

    def _get_fields_to_edit(self):
        return [
            "location_id",
            "product_id",
            "product_uom_id",
            "lot_id",
            "package_id",
        ]

    def action_barcode_inventory_quant_edit(self):
        wiz_barcode_id = self.env.context.get("wiz_barcode_id", False)
        wiz_barcode = self.env["wiz.stock.barcodes.read.inventory"].browse(
            wiz_barcode_id
        )
        for quant in self:
            # Try to assign fields with the same name between quant and the scan wizard
            for fname in self._get_fields_to_edit():
                wiz_barcode[fname] = quant[fname]
            wiz_barcode.product_qty = quant.inventory_quantity
