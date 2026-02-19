# Copyright 2019 Sergio Teruel <sergio.teruel@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class WizStockBarcodesNewLot(models.TransientModel):
    _inherit = "barcodes.barcode_events_mixin"
    _name = "wiz.stock.barcodes.new.lot"
    _description = "Wizard to create new lot from barcode scanner"

    product_id = fields.Many2one(comodel_name="product.product", required=True)
    lot_name = fields.Char(string="Lot name")

    def on_barcode_scanned(self, barcode):
        product = self.env["product.product"].search([("barcode", "=", barcode)])[:1]
        if product and not self.product_id:
            self.product_id = product
            return
        self.lot_name = barcode

    def _prepare_lot_values(self):
        return {
            "product_id": self.product_id.id,
            "name": self.lot_name,
            "company_id": self.env.company.id,
        }

    def get_scan_wizard(self):
        return self.env[self.env.context["active_model"]].browse(
            self.env.context["active_id"]
        )

    def scan_wizard_action(self):
        if self.env.context.get("active_model") == "wiz.stock.barcodes.read.inventory":
            action = self.env["ir.actions.actions"]._for_xml_id(
                "stock_barcodes.action_stock_barcodes_read_inventory"
            )
        else:
            action = self.env["ir.actions.actions"]._for_xml_id(
                "stock_barcodes.action_stock_barcodes_read_picking"
            )
        wiz_id = self.get_scan_wizard()
        action["res_id"] = wiz_id.id
        return action

    def confirm(self):
        ProductionLot = self.env["stock.lot"]
        lot = ProductionLot.search(
            [("product_id", "=", self.product_id.id), ("name", "=", self.lot_name)]
        )
        if not lot:
            lot = self.env["stock.lot"].create(self._prepare_lot_values())
        # Assign lot created or found to wizard scanning barcode lot_id field
        wiz = self.get_scan_wizard()
        if wiz:
            wiz.lot_id = lot
        return self.scan_wizard_action()

    def cancel(self):
        return self.scan_wizard_action()
