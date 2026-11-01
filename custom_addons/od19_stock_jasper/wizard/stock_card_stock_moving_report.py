# -*- coding: utf-8 -*-
"""Stock Card - Stock Moving view (บัตรสินค้า ความเคลื่อนไหว) - port of the
legacy ``dtr_stock_report`` report ``stock_card_stock_moving_report``.

The ``.jrxml`` (``jrxml/stock_card_stock_moving_report.jrxml``) is shipped
unchanged except for the ``queryString`` which now targets the Odoo 19 schema.
"""
from odoo import fields, models


class StockCardStockMovingReport(models.TransientModel):
    _name = "stock.card.stock.moving.report"
    _description = "Stock Card (Stock Moving)"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="Stock Card (Stock Moving)")
    jasper_file = fields.Char(
        default=lambda self: self.get_jasper_file(__file__)
    )
    p_Product_No = fields.Many2one(
        "product.product", string="Product", required=True
    )
    p_WH_No = fields.Many2one(
        "stock.location",
        string="Location",
        required=True,
        help="คลัง/ตำแหน่งที่ใช้แยกทิศทางรับ-จ่ายในบัตรสินค้า",
    )
    p_Date_As_Off = fields.Date(
        string="As of Date", required=True, default=fields.Date.today
    )

    def get_parameters(self):
        """Values handed to jasperstarter as ``-P key=value``."""
        self.name = "Stock Card (Stock Moving)"
        return {
            "p_Product_No": str(self.p_Product_No.id),
            "p_WH_No": str(self.p_WH_No.id),
            "p_Date_As_Off": str(self.p_Date_As_Off),
        }
