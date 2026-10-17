from odoo import models, fields, api


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    pos_type_id = fields.Many2one('stock.picking.type', string="Point of Sale Operation Type", copy=False)

    def _get_sequence_values(self, name=False, code=False):
        sequence_values = super()._get_sequence_values(name=name, code=code)
        sequence_values.update({
            'pos_type_id': {
                'name': self.env._('%(name)s Picking POS', name=name or self.name),
                'prefix': (code or self.code) + '/POS/',
                'padding': 5,
                'company_id': self.company_id.id,
            }
        })
        return sequence_values

    def _get_picking_type_update_values(self):
        picking_type_update_values = super()._get_picking_type_update_values()
        picking_type_update_values.update({
            'pos_type_id': {'default_location_src_id': self.lot_stock_id.id}
        })
        return picking_type_update_values

    def _get_picking_type_create_values(self, max_sequence):
        picking_type_create_values, max_sequence = super()._get_picking_type_create_values(max_sequence)
        picking_type_create_values.update({
            'pos_type_id': {
                'name': self.env._('PoS Orders'),
                'code': 'outgoing',
                'default_location_src_id': self.lot_stock_id.id,
                'default_location_dest_id': self.env.ref('stock.stock_location_customers').id,
                'sequence': max_sequence + 1,
                'company_id': self.company_id.id,
            }
        })
        return picking_type_create_values, max_sequence + 2

    def _update_name_and_code(self, new_name=False, new_code=False):
        super()._update_name_and_code(new_name, new_code)
        for warehouse in self:
            if warehouse.pos_type_id:
                sequence_data = warehouse._get_sequence_values(name=new_name, code=new_code)
                pos_sequence = warehouse.pos_type_id.sequence_id
                if self.env.user.has_group('stock.group_stock_manager'):
                    pos_sequence = pos_sequence.sudo()
                pos_sequence.write({
                    'name': sequence_data['pos_type_id']['name'],
                    'prefix': sequence_data['pos_type_id']['prefix'],
                })

    @api.model
    def _create_missing_pos_picking_types(self):
        warehouses = self.env['stock.warehouse'].search([('pos_type_id', '=', False)])
        for warehouse in warehouses:
            new_vals = warehouse._create_or_update_sequences_and_picking_types()
            warehouse.write(new_vals)
