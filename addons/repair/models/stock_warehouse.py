# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    repair_type_id = fields.Many2one('stock.picking.type', 'Repair Operation Type', check_company=True, copy=False)
    repair_mto_pull_id = fields.Many2one(
        'stock.rule', 'Repair MTO Rule', copy=False)

    def _get_sequence_values(self, name=False, code=False):
        values = super(StockWarehouse, self)._get_sequence_values(name=name, code=code)
        values.update({
            'repair_type_id': {
                'name': _('%(name)s Sequence repair', name=self.name),
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
                'use_create_lots': True,
                'use_existing_lots': True,
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

    @api.model
    def _get_production_location(self):
        location = self.env['stock.location'].search([('usage', '=', 'production'), ('company_id', '=', self.company_id.id)], limit=1)
        if not location:
            raise UserError(_("Can't find any production location."))
        return location

    def _generate_global_route_rules_values(self):
        rules = super()._generate_global_route_rules_values()
        production_location = self._get_production_location()
        rules.update({
            'repair_mto_pull_id': {
                'depends': ['repair_type_id'],
                'create_values': {
                    'procure_method': 'make_to_order',
                    'company_id': self.company_id.id,
                    'action': 'pull',
                    'auto': 'manual',
                    'route_id': self._find_or_create_global_route('stock.route_warehouse0_mto', _('Replenish on Order (MTO)')).id,
                    'location_dest_id': self.repair_type_id.default_location_dest_id.id,
                    'location_src_id': self.repair_type_id.default_location_src_id.id,
                    'picking_type_id': self.repair_type_id.id
                },
                'update_values': {
                    'name': self._format_rulename(self.lot_stock_id, production_location, 'MTO'),
                    'active': True,
                },
            },
        })
        return rules
