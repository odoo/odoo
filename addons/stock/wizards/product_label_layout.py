import base64
from collections import defaultdict

from odoo import api, fields, models
from odoo.tools.misc import file_open

from ..tools import debug_log as dbg


class ProductLabelLayout(models.TransientModel):
    _inherit = "product.label.layout"

    @api.model
    def _default_zpl_preview(self):
        with file_open("stock/static/img/zpl_label_placeholder.png", "rb") as f:
            return base64.b64encode(f.read())

    move_ids = fields.Many2many(comodel_name="stock.move")
    move_quantity = fields.Selection(
        selection=[("move", "Operation Quantities"), ("custom", "Custom")],
        string="Quantity to print",
        default="custom",
        required=True,
    )
    print_format = fields.Selection(
        selection_add=[("zpl", "ZPL Labels"), ("zplxprice", "ZPL Labels with price")],
        ondelete={"zpl": "set default", "zplxprice": "set default"},
    )
    zpl_template = fields.Selection(
        selection=[
            ("normal", 'Normal (2.25" x 1.25")'),
            ("small", 'Small (1.25" x 1.00")'),
            ("alternative", 'Alternative (2.00" x 1.00")'),
            ("jewelry", 'Jewelry (2.20" x 0.50")'),
        ],
        string="ZPL Template",
        default="normal",
        required=True,
    )
    zpl_preview = fields.Image(
        string="ZPL Preview",
        default=_default_zpl_preview,
        readonly=True,
    )

    def _prepare_report_data(self):
        xml_id, data = super()._prepare_report_data()

        if "zpl" in self.print_format:
            xml_id = "stock.label_product_product"
            data["zpl_template"] = self.zpl_template

        quantities = defaultdict(int)
        uom_unit = self.env.ref("uom.product_uom_unit", raise_if_not_found=False)
        if (
            self.move_quantity == "move"
            and self.move_ids
            and all(
                ml.product_uom_id.is_zero(ml.quantity)
                for ml in self.move_ids.move_line_ids
            )
        ):
            for move in self.move_ids:
                use_reserved = move.product_uom_id.compare(move.quantity, 0) > 0
                useable_qty = move.quantity if use_reserved else move.product_uom_qty
                if not move.product_uom_id.is_zero(useable_qty):
                    quantities[move.product_id.id] += useable_qty
            data["quantity_by_product"] = {p: int(q) for p, q in quantities.items()}
        elif self.move_quantity == "move" and self.move_ids.move_line_ids:
            custom_barcodes = defaultdict(list)
            for line in self.move_ids.move_line_ids:
                if line.product_uom_id._has_common_reference(uom_unit):
                    if (line.lot_id or line.lot_name) and int(line.quantity):
                        custom_barcodes[line.product_id.id].append(
                            (line.lot_id.name or line.lot_name, int(line.quantity))
                        )
                        continue
                    quantities[line.product_id.id] += line.quantity
                else:
                    quantities[line.product_id.id] = max(
                        quantities[line.product_id.id], 1
                    )
            data["quantity_by_product"] = {
                p: int(q) for p, q in quantities.items() if q
            }
            data["custom_barcodes"] = custom_barcodes
        dbg.logic.debug(
            "product label layout: format %s move_quantity %s -> report %s, %d products",
            self.print_format,
            self.move_quantity,
            xml_id,
            len(data.get("quantity_by_product") or ()),
        )
        return xml_id, data
