# -*- coding: utf-8 -*-
"""Product Barcode label (ป้ายบาร์โค้ดสินค้า) - port of the legacy
``dtr_stock_form`` report ``F-IV-008`` (``product.barcode.report``).

Reached from ``Inventory > Products > Print > Product Barcode``.  The label
always prints in English (``get_locale`` returns ``en_EN``) because barcodes and
prices are not localised.
"""
from odoo import _, fields, models
from odoo.exceptions import UserError


class ProductBarcodeReport(models.TransientModel):
    _name = "product.barcode.report"
    _description = "Product Barcode"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="Product Barcode")
    jasper_file = fields.Char(
        default=lambda self: self.get_jasper_file(__file__)
    )
    p_Show_Price = fields.Boolean(string="Display Sale Price", default=True)
    p_Print = fields.Integer(string="Number to print", required=True, default=1)

    def _legacy_active_ids(self):
        ids = self.env.context.get("active_ids") or []
        if not ids:
            raise UserError(_("No document selected."))
        return ids

    def get_parameters(self):
        """Values handed to jasperstarter as ``-P key=value``."""
        ids = self._legacy_active_ids()
        self.name = "Product Barcode"
        company = self.env.company
        name_en = getattr(company, "name_en", False) or ""
        return {
            "p_Where": "WHERE pt.id in ({0})".format(
                ", ".join(str(i) for i in ids)
            ),
            "p_Print": str(self.p_Print),
            "p_Show_Price": str(self.p_Show_Price),
            "p_Company_Name": str(name_en) if name_en else "",
            "p_Currency": str(company.currency_id.name),
        }

    def get_locale(self):
        return "en_EN"
