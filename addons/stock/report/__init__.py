# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .stock_forecasted import StockForecasted_Product_Product, StockForecasted_Product_Template
from .report_stock_quantity import ReportStockQuantity
from .report_stock_reception import ReportStockReport_Reception
from .report_stock_rule import ReportStockReport_Stock_Rule
from .stock_traceability import StockTraceabilityReport
from .product_label_report import (
    ReportStockLabel_Lot_Template_View,
    ReportStockLabel_Product_Product_View,
)
from .stock_lot_customer import StockLotReport
