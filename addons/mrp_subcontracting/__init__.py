# -*- coding: utf-8 -*-

from . import models
from . import report
from . import wizard
from . import controllers

from .models.mrp_bom import MrpBom
from .models.mrp_production import MrpProduction
from .models.product import ProductProduct, ProductSupplierinfo
from .models.res_company import ResCompany
from .models.res_partner import ResPartner
from .models.stock_location import StockLocation
from .models.stock_move import StockMove
from .models.stock_move_line import StockMoveLine
from .models.stock_picking import StockPicking
from .models.stock_quant import StockQuant
from .models.stock_replenish_mixin import StockReplenishMixin
from .models.stock_rule import StockRule
from .models.stock_warehouse import StockWarehouse
from .report.mrp_report_bom_structure import ReportMrpReport_Bom_Structure
from .wizard.change_production_qty import ChangeProductionQty
from .wizard.mrp_consumption_warning import MrpConsumptionWarning
from .wizard.stock_picking_return import StockReturnPicking, StockReturnPickingLine


def uninstall_hook(env):
    warehouses = env["stock.warehouse"].search([])
    subcontracting_routes = warehouses.mapped("subcontracting_route_id")
    warehouses.write({"subcontracting_route_id": False})
    companies = env["res.company"].search([])
    subcontracting_locations = companies.mapped("subcontracting_location_id")
    subcontracting_locations.active = False
    companies.write({"subcontracting_location_id": False})
    operations_type_to_remove = (warehouses.subcontracting_resupply_type_id | warehouses.subcontracting_type_id)
    operations_type_to_remove.active = False
    # Fail unlink means that the route is used somewhere (e.g. route_id on stock.rule). In this case
    # we don't try to do anything.
    try:
        with env.cr.savepoint():
            subcontracting_routes.unlink()
            operations_type_to_remove.unlink()
    except:
        pass
