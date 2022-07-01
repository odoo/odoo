# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    repair_type_id = fields.Many2one(
        'stock.picking.type', 'Repair Operation Type',
        domain="[('code', '=', 'repair'), ('company_id', '=', company_id)]", check_company=True)

    def _get_picking_type_update_values(self):
        data = super(StockWarehouse, self)._get_picking_type_update_values()
        data.update({
            'repair_type_id': {
                'active': self.active,
            },
        })
        return data

    def _get_picking_type_create_values(self, max_sequence):
        data, next_sequence = super(StockWarehouse, self)._get_picking_type_create_values(max_sequence)
        data.update({
            'repair_type_id': {
                'name': _('Repair'),
                'code': 'repair',
                'use_create_lots': True,
                'use_existing_lots': True,
                'sequence': next_sequence + 1,
                'sequence_code': 'RO',
                'company_id': self.company_id.id,
            },
        })
        return data, next_sequence + 2

    def _get_sequence_values(self):
        values = super(StockWarehouse, self)._get_sequence_values()
        values.update({
            'repair_type_id': {'name': self.name + ' ' + _('Sequence repair'), 'prefix': self.code + '/RO/', 'padding': 5, 'company_id': self.company_id.id},
        })
        return values
