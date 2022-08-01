# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    subcontracting_to_resupply = fields.Boolean(
        'Resupply Subcontractors', default=True)
    subcontracting_mto_pull_id = fields.Many2one(
        'stock.rule', 'Subcontracting MTO Rule')
    subcontracting_pull_id = fields.Many2one(
        'stock.rule', 'Subcontracting MTS Rule'
    )

    subcontracting_route_id = fields.Many2one('stock.route', 'Resupply Subcontractor', ondelete='restrict')

    subcontracting_type_id = fields.Many2one(
        'stock.picking.type', 'Subcontracting Operation Type',
        domain=[('code', '=', 'mrp_operation')])
    subcontracting_resupply_type_id = fields.Many2one(
        'stock.picking.type', 'Subcontracting Resupply Operation Type',
        domain=[('code', '=', 'outgoing')])

    def get_rules_dict(self):
        result = super(StockWarehouse, self).get_rules_dict()
        subcontract_location_id = self._get_subcontracting_location()
        for warehouse in self:
            result[warehouse.id].update({
                'subcontract': [
                    self.Routing(warehouse.lot_stock_id, subcontract_location_id, warehouse.subcontracting_resupply_type_id, 'pull'),
                ]
            })
        return result

    def _get_routes_values(self):
        routes = super(StockWarehouse, self)._get_routes_values()
        routes.update({
            'subcontracting_route_id': {
                'routing_key': 'subcontract',
                'depends': ['subcontracting_to_resupply'],
                'route_create_values': {
                    'product_categ_selectable': False,
                    'warehouse_selectable': True,
                    'product_selectable': False,
                    'company_id': self.company_id.id,
                    'sequence': 10,
                    'name': self._format_routename(name=_('Resupply Subcontractor'))
                },
                'route_update_values': {
                    'active': self.subcontracting_to_resupply,
                },
                'rules_values': {
                    'active': self.subcontracting_to_resupply,
                }
            }
        })
        return routes

    def _get_global_route_rules_values(self):
        rules = super(StockWarehouse, self)._get_global_route_rules_values()
        subcontract_location_id = self._get_subcontracting_location()
        production_location_id = self._get_production_location()
        rules.update({
            'subcontracting_mto_pull_id': {
                'depends': ['subcontracting_to_resupply'],
                'create_values': {
                    'procure_method': 'make_to_order',
                    'company_id': self.company_id.id,
                    'action': 'pull',
                    'auto': 'manual',
                    'route_id': self._find_global_route('stock.route_warehouse0_mto', _('Make To Order')).id,
                    'name': self._format_rulename(self.lot_stock_id, subcontract_location_id, 'MTO'),
                    'location_dest_id': subcontract_location_id.id,
                    'location_src_id': self.lot_stock_id.id,
                    'picking_type_id': self.subcontracting_resupply_type_id.id
                },
                'update_values': {
                    'active': self.subcontracting_to_resupply
                }
            },
            'subcontracting_pull_id': {
                'depends': ['subcontracting_to_resupply'],
                'create_values': {
                    'procure_method': 'make_to_order',
                    'company_id': self.company_id.id,
                    'action': 'pull',
                    'auto': 'manual',
                    'route_id': self._find_global_route('mrp_subcontracting.route_resupply_subcontractor_mto',
                                                        _('Resupply Subcontractor on Order')).id,
                    'name': self._format_rulename(self.lot_stock_id, subcontract_location_id, False),
                    'location_dest_id': production_location_id.id,
                    'location_src_id': subcontract_location_id.id,
                    'picking_type_id': self.subcontracting_resupply_type_id.id
                },
                'update_values': {
                    'active': self.subcontracting_to_resupply
                }
            },
        })
        return rules

    def _get_picking_type_create_values(self, max_sequence):
        data, next_sequence = super(StockWarehouse, self)._get_picking_type_create_values(max_sequence)
        data.update({
            'subcontracting_type_id': {
                'name': _('Subcontracting'),
                'code': 'mrp_operation',
                'use_create_components_lots': True,
                'sequence': next_sequence + 2,
                'sequence_code': 'SBC',
                'company_id': self.company_id.id,
            },
            'subcontracting_resupply_type_id': {
                'name': _('Resupply Subcontractor'),
                'code': 'outgoing',
                'use_create_lots': False,
                'use_existing_lots': True,
                'default_location_dest_id': self._get_subcontracting_location().id,
                'sequence': next_sequence + 3,
                'sequence_code': 'RES',
                'print_label': True,
                'company_id': self.company_id.id,
            }
        })
        return data, max_sequence + 4

    def _get_sequence_values(self):
        values = super(StockWarehouse, self)._get_sequence_values()
        values.update({
            'subcontracting_type_id': {
                'name': self.name + ' ' + _('Sequence subcontracting'),
                'prefix': self.code + '/SBC/',
                'padding': 5,
                'company_id': self.company_id.id
            },
            'subcontracting_resupply_type_id': {
                'name': self.name + ' ' + _('Sequence Resupply Subcontractor'),
                'prefix': self.code + '/RES/',
                'padding': 5,
                'company_id': self.company_id.id
            },
        })
        return values

    def _get_picking_type_update_values(self):
        data = super(StockWarehouse, self)._get_picking_type_update_values()
        subcontract_location_id = self._get_subcontracting_location()
        production_location_id = self._get_production_location()
        data.update({
            'subcontracting_type_id': {
                'active': False,
                'default_location_src_id': subcontract_location_id.id,
                'default_location_dest_id': production_location_id.id,
            },
            'subcontracting_resupply_type_id': {
                'default_location_src_id': production_location_id.id,
                'default_location_dest_id': subcontract_location_id.id,
                'barcode': self.code.replace(" ", "").upper() + "-RESUPPLY",
            },
        })
        return data

    def _get_subcontracting_location(self):
        return self.company_id.subcontracting_location_id
