# -*- coding: utf-8 -*-

from .models import (
    MrpBom, MrpProduction, ProductProduct, ProductSupplierinfo, ResCompany,
    ResPartner, StockLocation, StockMove, StockMoveLine, StockPicking, StockQuant,
    StockReplenishMixin, StockRule, StockWarehouse,
)
from .report import ReportMrpReport_Bom_Structure
from .wizard import (
    ChangeProductionQty, MrpConsumptionWarning, StockReturnPicking,
    StockReturnPickingLine,
)
from . import controllers


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
