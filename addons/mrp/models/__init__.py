# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .ir_attachment import IrAttachment
from .product_document import ProductDocument
from .res_config_settings import ResConfigSettings
from .mrp_bom import MrpBom, MrpBomByproduct, MrpBomLine
from .mrp_routing import MrpRoutingWorkcenter
from .mrp_workcenter import (
    MrpWorkcenter, MrpWorkcenterCapacity, MrpWorkcenterProductivity,
    MrpWorkcenterProductivityLoss, MrpWorkcenterProductivityLossType, MrpWorkcenterTag,
)
from .mrp_production import MrpProduction
from .stock_traceability import StockTraceabilityReport
from .mrp_unbuild import MrpUnbuild
from .mrp_workorder import MrpWorkorder
from .product import ProductProduct, ProductTemplate
from .res_company import ResCompany
from .stock_move import StockMove, StockMoveLine
from . import stock_orderpoint
from .stock_picking import StockPicking, StockPickingType
from .stock_lot import StockLot
from .stock_rule import ProcurementGroup, StockRule
from .stock_scrap import StockScrap
from .stock_warehouse import StockWarehouse, StockWarehouseOrderpoint
from .stock_quant import StockQuant
from .stock_replenish_mixin import StockReplenishMixin
