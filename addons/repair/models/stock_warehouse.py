# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    repair_type_id = fields.Many2one('stock.picking.type', 'Repair Operation Type', check_company=True, copy=False)

    def _get_sequence_values(self, name=False, code=False):
        values = super(StockWarehouse, self)._get_sequence_values(name=name, code=code)
        values.update({
            'repair_type_id': {
                'name': self.name + ' ' + _('Sequence repair'),
                'prefix': self.code + '/' + (self.repair_type_id.sequence_code or 'RO') + '/',
                'padding': 5,
                'company_id': self.company_id.id
                },
        })
        return values

    def _get_picking_type_create_values(self, max_sequence):
        data, next_sequence = super(StockWarehouse, self)._get_picking_type_create_values(max_sequence)
        prod_location = self.env['stock.location'].search([('usage', '=', 'production'), ('company_id', '=', self.company_id.id)], limit=1)
        scrap_location = self.env['stock.location'].search([('scrap_location', '=', True), ('company_id', 'in', [self.company_id.id, False])], limit=1)
        data.update({
            'repair_type_id': {
                'name': _('Repairs'),
                'code': 'repair_operation',
                'default_location_src_id': self.lot_stock_id.id,
                'default_location_dest_id': prod_location.id,
                'default_remove_location_dest_id':scrap_location.id,
                'default_recycle_location_dest_id': self.lot_stock_id.id,
                'sequence': next_sequence + 1,
                'sequence_code': 'RO',
                'company_id': self.company_id.id,
            },
        })
        return data, max_sequence + 2

    def _get_picking_type_update_values(self):
        data = super(StockWarehouse, self)._get_picking_type_update_values()
        data.update({
            'repair_type_id': {
                'active': self.active,
                'barcode': self.code.replace(" ", "").upper() + "RO",
            },
        })
        return data
