# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .barcode import BarcodeRule
from .ir_actions_report import IrActionsReport
from .product_strategy import ProductRemoval, StockPutawayRule
from .res_company import ResCompany
from .res_partner import ResPartner
from .res_users import ResUsers
from .res_config_settings import ResConfigSettings
from .stock_location import StockLocation, StockRoute
from .stock_move import StockMove
from .stock_move_line import StockMoveLine
from .stock_orderpoint import StockWarehouseOrderpoint
from .stock_lot import StockLot
from .stock_picking import StockPicking, StockPickingType
from .stock_quant import StockQuant, StockQuantPackage
from .stock_replenish_mixin import StockReplenishMixin
from .stock_rule import ProcurementGroup, StockRule
from .stock_warehouse import StockWarehouse
from .stock_scrap import StockScrap, StockScrapReasonTag
from .product import ProductCategory, ProductPackaging, ProductProduct, ProductTemplate, UomUom
from .stock_package_level import StockPackage_Level
from .stock_package_type import StockPackageType
from .stock_storage_category import StockStorageCategory, StockStorageCategoryCapacity
