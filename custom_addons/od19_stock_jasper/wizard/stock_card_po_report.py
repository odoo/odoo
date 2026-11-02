# -*- coding: utf-8 -*-
"""Stock Card - Purchase view (บัตรสินค้า มุมมองจัดซื้อ) - port of the legacy
``dtr_stock_report`` report ``stock_card_po_report``.

The ``.jrxml`` (``jrxml/stock_card_po_report.jrxml``) is shipped unchanged
except for the ``queryString`` which now targets the Odoo 19 schema.
"""
from odoo import fields, models


class StockCardPoReport(models.TransientModel):
    _name = "stock.card.po.report"
    _description = "Stock Card (Purchase)"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="Stock Card (Purchase)")
    jasper_file = fields.Char(
        default=lambda self: self.get_jasper_file(__file__)
    )
    p_Product_No = fields.Many2one(
        "product.product", string="Product", required=True
    )
    p_Date_As_Off = fields.Date(
        string="As of Date", required=True, default=fields.Date.today
    )

    def get_parameters(self):
        """Values handed to jasperstarter as ``-P key=value``."""
        self.name = "Stock Card (Purchase)"
        return {
            "p_Product_No": str(self.p_Product_No.id),
            "p_Date_As_Off": str(self.p_Date_As_Off),
        }
