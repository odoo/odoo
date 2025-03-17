from odoo import models

class Warehouse(models.Model):
    _inherit = "stock.warehouse"

    def _get_routes_values(self):
        routes = super()._get_routes_values()
        if routes.get('crossdock_route_id'):
            routes['crossdock_route_id']['route_update_values']['sale_selectable'] = True
            routes['crossdock_route_id']['route_create_values']['sale_selectable'] = True
        return routes
