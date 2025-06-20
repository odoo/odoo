from odoo import models


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    def _get_picking_type_update_values(self):
        values = super()._get_picking_type_update_values()
        if self.delivery_steps == 'pick_pack_ship':
            if values.get('pack_type_id'):
                values['pack_type_id']['dispatch_management'] = True
        elif self.delivery_steps == 'pick_ship':
            if values.get('pick_type_id'):
                values['pick_type_id']['dispatch_management'] = True

        if values.get('out_type_id'):
            values['out_type_id']['dispatch_management'] = True
        if values.get('in_type_id'):
            values['in_type_id']['dispatch_management'] = True

        return values
