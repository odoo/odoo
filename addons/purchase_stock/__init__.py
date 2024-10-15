# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .models import (
    AccountMove, AccountMoveLine, ProcurementGroup, ProductCategory,
    ProductProduct, ProductSupplierinfo, ProductTemplate, PurchaseOrder, PurchaseOrderLine,
    ResCompany, ResConfigSettings, ResPartner, StockLot, StockMove, StockPicking,
    StockReplenishMixin, StockReturnPicking, StockRule, StockValuationLayer, StockWarehouse,
    StockWarehouseOrderpoint,
)
from .report import (
    PurchaseReport, ReportStockReport_Stock_Rule, StockForecasted_Product_Product,
    VendorDelayReport,
)
from .wizard import ProductReplenish, StockReplenishmentInfo, StockReplenishmentOption


def _create_buy_rules(env):
    """ This hook is used to add a default buy_pull_id on every warehouse. It is
    necessary if the purchase_stock module is installed after some warehouses
    were already created.
    """
    warehouse_ids = env['stock.warehouse'].search([('buy_pull_id', '=', False)])
    warehouse_ids.write({'buy_to_resupply': True})
