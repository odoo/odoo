# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    subcontracting_to_resupply = fields.Boolean(
        'Resupply Subcontractors', default=True)
    subcontracting_mto_pull_id = fields.Many2one(
        'stock.rule', 'Subcontracting MTO Rule', copy=False)
    subcontracting_pull_id = fields.Many2one(
        'stock.rule', 'Subcontracting MTS Rule', copy=False
    )

    subcontracting_route_id = fields.Many2one('stock.route', 'Resupply Subcontractor', ondelete='restrict', copy=False)

    subcontracting_type_id = fields.Many2one(
        'stock.picking.type', 'Subcontracting Operation Type',
        domain=[('code', '=', 'mrp_operation')], copy=False)
    subcontracting_resupply_type_id = fields.Many2one(
        'stock.picking.type', 'Subcontracting Resupply Operation Type',
        domain=[('code', '=', 'outgoing')], copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        res._update_subcontracting_locations_rules()
        # if new warehouse has resupply enabled, enable global route
        if any([vals.get('subcontracting_to_resupply', False) for vals in vals_list]):
            res._update_global_route_resupply_subcontractor()
        return res

    def write(self, vals):
        res = super().write(vals)
        # if all warehouses have resupply disabled, disable global route, until its enabled on a warehouse
        if 'subcontracting_to_resupply' in vals or 'active' in vals:
            if 'subcontracting_to_resupply' in vals:
                # ignore when warehouse archived since it will auto-archive all of its rules
                self._update_resupply_rules()
            self._update_global_route_resupply_subcontractor()
        return res

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

    def _update_global_route_resupply_subcontractor(self):
        route_id = self._find_or_create_global_route('mrp_subcontracting.route_resupply_subcontractor_mto',
                                           _('Resupply Subcontractor on Order'))
        if not route_id.sudo().rule_ids.filtered(lambda r: r.active):
            route_id.active = False
        else:
            route_id.active = True

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

    def _generate_global_route_rules_values(self):
        rules = super()._generate_global_route_rules_values()
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
                    'route_id': self._find_or_create_global_route('stock.route_warehouse0_mto', _('Replenish on Order (MTO)')).id,
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
                    'route_id': self._find_or_create_global_route('mrp_subcontracting.route_resupply_subcontractor_mto', _('Resupply Subcontractor on Order')).id,
                    'name': self._format_rulename(subcontract_location_id, production_location_id, False),
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

    def _get_sequence_values(self, name=False, code=False):
        values = super(StockWarehouse, self)._get_sequence_values(name=name, code=code)
        count = self.env['ir.sequence'].search_count([('prefix', '=like', self.code + '/SBC%/%')])
        values.update({
            'subcontracting_type_id': {
                'name': self.name + ' ' + _('Sequence subcontracting'),
                'prefix': self.code + '/' + (self.subcontracting_type_id.sequence_code or (('SBC' + str(count)) if count else 'SBC')) + '/',
                'padding': 5,
                'company_id': self.company_id.id
            },
            'subcontracting_resupply_type_id': {
                'name': self.name + ' ' + _('Sequence Resupply Subcontractor'),
                'prefix': self.code + '/' + (self.subcontracting_resupply_type_id.sequence_code or (('RES' + str(count)) if count else 'RES')) + '/',
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
                'default_location_src_id': self.lot_stock_id.id,
                'default_location_dest_id': subcontract_location_id.id,
                'barcode': self.code.replace(" ", "").upper() + "-RESUPPLY",
                'active': self.subcontracting_to_resupply and self.active
            },
        })
        return data

    def _get_subcontracting_location(self):
        return self.company_id.subcontracting_location_id

    def _get_subcontracting_locations(self):
        return self.env['stock.location'].search([
            ('company_id', 'in', self.company_id.ids),
            ('is_subcontracting_location', '=', 'True'),
        ])

    def _update_subcontracting_locations_rules(self):
        subcontracting_locations = self._get_subcontracting_locations()
        subcontracting_locations._activate_subcontracting_location_rules()

    def _update_resupply_rules(self):
        '''update (archive/unarchive) any warehouse subcontracting location resupply rules'''
        subcontracting_locations = self._get_subcontracting_locations()
        warehouses_to_resupply = self.filtered(lambda w: w.subcontracting_to_resupply and w.active)
        if warehouses_to_resupply:
            self.env['stock.rule'].with_context(active_test=False).search([
                '&', ('picking_type_id', 'in', warehouses_to_resupply.subcontracting_resupply_type_id.ids),
                '|', ('location_src_id', 'in', subcontracting_locations.ids),
                ('location_dest_id', 'in', subcontracting_locations.ids)]).action_unarchive()

        warehouses_not_to_resupply = self - warehouses_to_resupply
        if warehouses_not_to_resupply:
            self.env['stock.rule'].search([
                '&', ('picking_type_id', 'in', warehouses_not_to_resupply.subcontracting_resupply_type_id.ids),
                '|', ('location_src_id', 'in', subcontracting_locations.ids),
                ('location_dest_id', 'in', subcontracting_locations.ids)]).action_archive()
