# -*- coding: utf-8 -*-

from . import models
from . import report
from . import wizard
from . import controllers


def uninstall_hook(env):
    warehouses = env["stock.warehouse"].search([])
    subcontracting_routes = warehouses.subcontracting_route_id
    warehouses.write({"subcontracting_route_id": False})
    companies = env["res.company"].search([])
    subcontracting_locations = companies.subcontracting_location_id
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
