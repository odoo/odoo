# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .product import ProductTemplate
from .purchase import PurchaseOrderLine
from .res_company import ResCompany
from .res_config_settings import ResConfigSettings
from .stock_landed_cost import (
    StockLandedCost, StockLandedCostLines,
    StockValuationAdjustmentLines,
)
from .account_move import AccountMove, AccountMoveLine
from .stock_valuation_layer import StockValuationLayer
from .stock_move import StockMove
