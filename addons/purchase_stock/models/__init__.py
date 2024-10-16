# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .account_invoice import AccountMove
from .account_move_line import AccountMoveLine
from .product import ProductCategory, ProductProduct, ProductSupplierinfo, ProductTemplate
from .stock_replenish_mixin import StockReplenishMixin
from .purchase_order import PurchaseOrder
from .purchase_order_line import PurchaseOrderLine
from .res_config_settings import ResConfigSettings
from .res_partner import ResPartner
from .res_company import ResCompany
from .stock import (
    ProcurementGroup, StockLot, StockPicking, StockReturnPicking, StockWarehouse,
    StockWarehouseOrderpoint,
)
from .stock_move import StockMove
from .stock_rule import StockRule
from .stock_valuation_layer import StockValuationLayer
