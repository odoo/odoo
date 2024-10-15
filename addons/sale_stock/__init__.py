# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from .models import (
    AccountMove, AccountMoveLine, ProcurementGroup, ProductTemplate, ResCompany,
    ResConfigSettings, ResUsers, SaleOrder, SaleOrderLine, StockLot, StockMove, StockMoveLine,
    StockPicking, StockRoute, StockRule,
)
from .report import ReportStockReport_Stock_Rule, SaleReport, StockForecasted_Product_Product
from .wizard import SaleOrderCancel, StockRulesReport
