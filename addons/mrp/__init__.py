# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard
from . import report
from . import controller

from .models.ir_attachment import IrAttachment
from .models.mrp_bom import MrpBom, MrpBomByproduct, MrpBomLine
from .models.mrp_production import MrpProduction
from .models.mrp_routing import MrpRoutingWorkcenter
from .models.mrp_unbuild import MrpUnbuild
from .models.mrp_workcenter import (
    MrpWorkcenter, MrpWorkcenterCapacity,
    MrpWorkcenterProductivity, MrpWorkcenterProductivityLoss,
    MrpWorkcenterProductivityLossType, MrpWorkcenterTag,
)
from .models.mrp_workorder import MrpWorkorder
from .models.product import ProductProduct, ProductTemplate
from .models.product_document import ProductDocument
from .models.res_company import ResCompany
from .models.res_config_settings import ResConfigSettings
from .models.stock_lot import StockLot
from .models.stock_move import StockMove, StockMoveLine
from .models.stock_orderpoint import StockWarehouseOrderpoint
from .models.stock_picking import StockPicking, StockPickingType
from .models.stock_quant import StockQuant
from .models.stock_replenish_mixin import StockReplenishMixin
from .models.stock_rule import ProcurementGroup, StockRule
from .models.stock_scrap import StockScrap
from .models.stock_traceability import StockTraceabilityReport
from .models.stock_warehouse import StockWarehouse
from .report.mrp_report_bom_structure import ReportMrpReport_Bom_Structure
from .report.mrp_report_mo_overview import ReportMrpReport_Mo_Overview
from .report.report_stock_reception import ReportStockReport_Reception
from .report.report_stock_rule import ReportStockReport_Stock_Rule
from .report.stock_forecasted import StockForecasted_Product_Product
from .wizard.change_production_qty import ChangeProductionQty
from .wizard.mrp_batch_produce import MrpBatchProduce
from .wizard.mrp_consumption_warning import MrpConsumptionWarning, MrpConsumptionWarningLine
from .wizard.mrp_production_backorder import (
    MrpProductionBackorder,
    MrpProductionBackorderLine,
)
from .wizard.mrp_production_split import (
    MrpProductionSplit, MrpProductionSplitLine,
    MrpProductionSplitMulti,
)
from .wizard.product_replenish import ProductReplenish
from .wizard.stock_label_type import PickingLabelType
from .wizard.stock_warn_insufficient_qty import StockWarnInsufficientQtyUnbuild


def _pre_init_mrp(env):
    """ Allow installing MRP in databases with large stock.move table (>1M records)
        - Creating the computed+stored field stock_move.is_done and
          stock_move.unit_factor is terribly slow with the ORM and leads to "Out of
          Memory" crashes
    """
    env.cr.execute("""ALTER TABLE "stock_move" ADD COLUMN "is_done" bool;""")
    env.cr.execute("""UPDATE stock_move
                     SET is_done=COALESCE(state in ('done', 'cancel'), FALSE);""")
    env.cr.execute("""ALTER TABLE "stock_move" ADD COLUMN "unit_factor" double precision;""")
    env.cr.execute("""UPDATE stock_move
                     SET unit_factor=1;""")

def _create_warehouse_data(env):
    """ This hook is used to add a default manufacture_pull_id, manufacture
    picking_type on every warehouse. It is necessary if the mrp module is
    installed after some warehouses were already created.
    """
    warehouse_ids = env['stock.warehouse'].search([('manufacture_pull_id', '=', False)])
    warehouse_ids.write({'manufacture_to_resupply': True})

def uninstall_hook(env):
    warehouses = env["stock.warehouse"].search([])
    pbm_routes = warehouses.mapped("pbm_route_id")
    warehouses.write({"pbm_route_id": False})
    # Fail unlink means that the route is used somewhere (e.g. route_id on stock.rule). In this case
    # we don't try to do anything.
    try:
        with env.cr.savepoint():
            pbm_routes.unlink()
    except:
        pass
