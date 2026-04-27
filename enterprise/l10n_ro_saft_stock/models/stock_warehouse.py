from odoo import models


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    def _create_or_update_sequences_and_picking_types(self):
        # EXTENDS stock
        # to set correct return picking types for Romanian companies
        warehouse_data = super()._create_or_update_sequences_and_picking_types()
        company = self.company_id or self.env.company

        if company.country_code == 'RO':
            PickingType = self.env['stock.picking.type']
            PickingType.browse(warehouse_data['in_type_id']).write({
                'return_picking_type_id': self.env['stock.picking.type'].create({
                    'name': self.env._('Return of purchase'),
                    'code': 'outgoing',
                    'sequence_code': 'INR',
                    'company_id': company.id,
                    'warehouse_id': self.id,
                    'l10n_ro_stock_movement_type': '50',
                }).id,
            })
            PickingType.browse(warehouse_data['out_type_id']).write({
                'return_picking_type_id': self.env['stock.picking.type'].create({
                    'name': self.env._('Return of sales'),
                    'code': 'incoming',
                    'sequence_code': 'OUTR',
                    'company_id': company.id,
                    'warehouse_id': self.id,
                    'l10n_ro_stock_movement_type': '40',
                }).id,
            })

        return warehouse_data
