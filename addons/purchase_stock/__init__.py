# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import report
from . import wizard

from .models.account_invoice import AccountMove
from .models.account_move_line import AccountMoveLine
from .models.product import (
    ProductCategory, ProductProduct, ProductSupplierinfo,
    ProductTemplate,
)
from .models.purchase_order import PurchaseOrder
from .models.purchase_order_line import PurchaseOrderLine
from .models.res_company import ResCompany
from .models.res_config_settings import ResConfigSettings
from .models.res_partner import ResPartner
from .models.stock import (
    ProcurementGroup, StockLot, StockPicking, StockReturnPicking,
    StockWarehouse, StockWarehouseOrderpoint,
)
from .models.stock_move import StockMove
from .models.stock_replenish_mixin import StockReplenishMixin
from .models.stock_rule import StockRule
from .models.stock_valuation_layer import StockValuationLayer
from .report.purchase_report import PurchaseReport
from .report.report_stock_rule import ReportStockReport_Stock_Rule
from .report.stock_forecasted import StockForecasted_Product_Product
from .report.vendor_delay_report import VendorDelayReport
from .wizard.product_replenish import ProductReplenish
from .wizard.stock_replenishment_info import StockReplenishmentInfo, StockReplenishmentOption


def _create_buy_rules(env):
    """ This hook is used to add a default buy_pull_id on every warehouse. It is
    necessary if the purchase_stock module is installed after some warehouses
    were already created.
    """
    warehouse_ids = env['stock.warehouse'].search([('buy_pull_id', '=', False)])
    warehouse_ids.write({'buy_to_resupply': True})
