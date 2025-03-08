from odoo import models


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    def _get_picking_type_update_values(self):
        values = super()._get_picking_type_update_values()
        if values['pick_type_id'].get('active'):
            values['pick_type_id']['dispatch_management'] = True
        if values['pack_type_id'].get('active'):
            values['pack_type_id']['dispatch_management'] = True
        return values
