from odoo import models


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    def _get_picking_type_create_values(self, max_sequence):
        values = super()._get_picking_type_create_values(max_sequence)
        values[0]['pick_type_id']['restrict_scan_source_location'] = 'mandatory'
        values[0]['pick_type_id']['restrict_scan_dest_location'] = 'no'
        return values

    def _get_picking_type_update_values(self):
        values = super()._get_picking_type_update_values()
        # When multi-steps delivery is enabled, the source scan setting for the pick is equal to the
        # delivery type's one, and the scan source for the delivery is disabled (by default).
        if values['pick_type_id'].get('active'):
            if self.out_type_id.restrict_scan_source_location == 'mandatory' and self.pick_type_id.restrict_scan_dest_location == 'optional':
                values['out_type_id']['restrict_scan_source_location'] = 'no'
                values['pick_type_id']['restrict_scan_source_location'] = self.out_type_id.restrict_scan_source_location
            values['pick_type_id']['restrict_scan_dest_location'] = 'no'
        elif not values['pick_type_id'].get('active') and self.pick_type_id.active:
            values['out_type_id']['restrict_scan_source_location'] = self.pick_type_id.restrict_scan_source_location
        return values
