from collections import defaultdict

from markupsafe import Markup

from odoo import models
from odoo.exceptions import UserError

from ..tools import debug_log as dbg


class ReportStockLabel_Product_Product_View(models.AbstractModel):
    _name = "report.stock.label_product_product_view"
    _description = "Product Label Report"

    def _get_report_values(self, docids, data):
        if data.get("active_model") == "product.template":
            Product = self.env["product.template"]
        elif data.get("active_model") == "product.product":
            Product = self.env["product.product"]
        else:
            raise UserError(
                self.env._(
                    "Product model not defined, Please contact your administrator."
                )
            )

        quantity_by_product = defaultdict(list)
        dbg.logic.debug(
            "product labels for %s: %d products, layout %s",
            data.get("active_model"),
            len(data.get("quantity_by_product") or {}),
            data.get("layout_wizard"),
        )
        for p, q in (data.get("quantity_by_product") or {}).items():
            product = Product.browse(int(p))
            default_code = product.default_code or ""
            product_info = {
                "barcode": product.barcode or "",
                "quantity": q,
                "display_name": product.display_name,
                "default_code": (default_code[:15], default_code[15:30]),
            }
            quantity_by_product[product].append(product_info)
        if data.get("custom_barcodes"):
            for product, barcodes_qtys in data.get("custom_barcodes").items():
                product = Product.browse(int(product))
                default_code = product.default_code or ""
                for barcode_qty in barcodes_qtys:
                    quantity_by_product[product].append(
                        {
                            "barcode": barcode_qty[0],
                            "quantity": barcode_qty[1],
                            "display_name": product.display_name,
                            "default_code": (
                                default_code[:15],
                                default_code[15:30],
                            ),
                        }
                    )
        data["quantity"] = quantity_by_product
        layout_wizard = self.env["product.label.layout"].browse(
            data.get("layout_wizard")
        )
        data["pricelist"] = layout_wizard.pricelist_id
        data["markup"] = Markup

        return data


class ReportStockLabel_Lot_Template_View(models.AbstractModel):
    _name = "report.stock.label_lot_template_view"
    _description = "Lot Label Report"

    def _get_report_values(self, docids, data):
        lots = self.env["stock.lot"].browse(docids)
        lot_list = [
            {
                "display_name": lot.product_id.display_name,
                "name": lot.name,
                "lot_record": lot,
            }
            for lot in lots
        ]
        return {
            "docs": lot_list,
            "markup": Markup,
        }
