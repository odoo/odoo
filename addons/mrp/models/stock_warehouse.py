# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    manufacture_to_resupply = fields.Boolean(
        'Manufacture to Resupply', default=True,
        help="When products are manufactured, they can be manufactured in this warehouse.")
    manufacture_pull_id = fields.Many2one(
        'stock.rule', 'Manufacture Rule')
    pbm_mto_pull_id = fields.Many2one(
        'stock.rule', 'Picking Before Manufacturing MTO Rule')
    sam_rule_id = fields.Many2one(
        'stock.rule', 'Stock After Manufacturing Rule')
    manu_type_id = fields.Many2one(
        'stock.picking.type', 'Manufacturing Operation Type',
        domain=[('code', '=', 'mrp_operation')])

    pbm_type_id = fields.Many2one('stock.picking.type', 'Picking Before Manufacturing Operation Type')
    sam_type_id = fields.Many2one('stock.picking.type', 'Stock After Manufacturing Operation Type')

    manufacture_steps = fields.Selection([
        ('mrp_one_step', 'Manufacture (1 step)'),
        ('pbm', 'Pick components and then manufacture (2 steps)'),
        ('pbm_sam', 'Pick components, manufacture and then store products (3 steps)')],
        'Manufacture', default='mrp_one_step', required=True,
        help="Produce : Move the raw materials to the production location\
        directly and start the manufacturing process.\nPick / Produce : Unload\
        the raw materials from the Stock to Input location first, and then\
        transfer it to the Production location.")

    pbm_route_id = fields.Many2one('stock.location.route', 'Picking Before Manufacturing Route', ondelete='restrict')

    pbm_loc_id = fields.Many2one('stock.location', 'Picking before Manufacturing Location')
    sam_loc_id = fields.Many2one('stock.location', 'Stock after Manufacturing Location')

    def get_rules_dict(self):
        result = super(StockWarehouse, self).get_rules_dict()
        production_location_id = self._get_production_location()
        for warehouse in self:
            result[warehouse.id].update({
                'mrp_one_step': [],
                'pbm': [
                    self.Routing(warehouse.lot_stock_id, warehouse.pbm_loc_id, warehouse.pbm_type_id, 'pull'),
                    self.Routing(warehouse.pbm_loc_id, production_location_id, warehouse.manu_type_id, 'pull'),
                ],
                'pbm_sam': [
                    self.Routing(warehouse.lot_stock_id, warehouse.pbm_loc_id, warehouse.pbm_type_id, 'pull'),
                    self.Routing(warehouse.pbm_loc_id, production_location_id, warehouse.manu_type_id, 'pull'),
                    self.Routing(warehouse.sam_loc_id, warehouse.lot_stock_id, warehouse.sam_type_id, 'push'),
                ],
            })
        return result

    @api.model
    def _get_production_location(self):
        location = self.env.ref('stock.location_production', raise_if_not_found=False)
        if not location:
            location = self.env['stock.location'].search([('usage', '=', 'production')], limit=1)
        if not location:
            raise UserError(_('Can\'t find any production location.'))
        return location

    def _get_routes_values(self):
        routes = super(StockWarehouse, self)._get_routes_values()
        routes.update({
            'pbm_route_id': {
                'routing_key': self.manufacture_steps,
                'depends': ['manufacture_steps', 'manufacture_to_resupply'],
                'route_update_values': {
                    'name': self._format_routename(route_type=self.manufacture_steps),
                    'active': self.manufacture_steps != 'mrp_one_step',
                },
                'route_create_values': {
                    'product_categ_selectable': True,
                    'warehouse_selectable': True,
                    'product_selectable': False,
                    'company_id': self.company_id.id,
                    'sequence': 10,
                },
                'rules_values': {
                    'active': True,
                }
            }
        })
        return routes

    def _get_route_name(self, route_type):
        names = {
            'mrp_one_step': _('Manufacture (1 step)'),
            'pbm': _('Pick components and then manufacture'),
            'pbm_sam': _('Pick components, manufacture and then store products (3 steps)'),
        }
        if route_type in names:
            return names[route_type]
        else:
            return super(StockWarehouse, self)._get_route_name(route_type)

    def _get_global_route_rules_values(self):
        rules = super(StockWarehouse, self)._get_global_route_rules_values()
        location_id = self.manufacture_steps == 'pbm_sam' and self.sam_loc_id or self.lot_stock_id
        rules.update({
            'manufacture_pull_id': {
                'depends': ['manufacture_steps', 'manufacture_to_resupply'],
                'create_values': {
                    'action': 'manufacture',
                    'procure_method': 'make_to_order',
                    'company_id': self.company_id.id,
                    'picking_type_id': self.manu_type_id.id,
                    'route_id': self._find_global_route('mrp.route_warehouse0_manufacture', _('Manufacture')).id
                },
                'update_values': {
                    'active': self.manufacture_to_resupply,
                    'name': self._format_rulename(location_id, False, 'Production'),
                    'location_id': location_id.id,
                }
            },
            'pbm_mto_pull_id': {
                'depends': ['manufacture_steps', 'manufacture_to_resupply'],
                'create_values': {
                    'procure_method': 'make_to_order',
                    'company_id': self.company_id.id,
                    'action': 'pull',
                    'auto': 'manual',
                    'propagate': True,
                    'route_id': self._find_global_route('stock.route_warehouse0_mto', _('Make To Order')).id,
                    'name': self._format_rulename(self.lot_stock_id, self.pbm_loc_id, 'MTO'),
                    'location_id': self.pbm_loc_id.id,
                    'location_src_id': self.lot_stock_id.id,
                    'picking_type_id': self.pbm_type_id.id
                },
                'update_values': {
                    'active': self.manufacture_steps != 'mrp_one_step' and self.manufacture_to_resupply,
                }
            },
            # The purpose to move sam rule in the manufacture route instead of
            # pbm_route_id is to avoid conflict with receipt in multiple
            # step. For example if the product is manufacture and receipt in two
            # step it would conflict in WH/Stock since product could come from
            # WH/post-prod or WH/input. We do not have this conflict with
            # manufacture route since it is set on the product.
            'sam_rule_id': {
                'depends': ['manufacture_steps', 'manufacture_to_resupply'],
                'create_values': {
                    'procure_method': 'make_to_order',
                    'company_id': self.company_id.id,
                    'action': 'pull',
                    'auto': 'manual',
                    'propagate': True,
                    'route_id': self._find_global_route('mrp.route_warehouse0_manufacture', _('Manufacture')).id,
                    'name': self._format_rulename(self.sam_loc_id, self.lot_stock_id, False),
                    'location_id': self.lot_stock_id.id,
                    'location_src_id': self.sam_loc_id.id,
                    'picking_type_id': self.sam_type_id.id
                },
                'update_values': {
                    'active': self.manufacture_steps == 'pbm_sam' and self.manufacture_to_resupply,
                }
            }

        })
        return rules

    def _get_locations_values(self, vals):
        values = super(StockWarehouse, self)._get_locations_values(vals)
        def_values = self.default_get(['manufacture_steps'])
        manufacture_steps = vals.get('manufacture_steps', def_values['manufacture_steps'])
        code = vals.get('code') or self.code or ''
        code = code.replace(' ', '').upper()
        company_id = vals.get('company_id', self.company_id.id)
        values.update({
            'pbm_loc_id': {
                'name': _('Pre-Production'),
                'active': manufacture_steps in ('pbm', 'pbm_sam'),
                'usage': 'internal',
                'barcode': self._valid_barcode(code + '-PREPRODUCTION', company_id)
            },
            'sam_loc_id': {
                'name': _('Post-Production'),
                'active': manufacture_steps == 'pbm_sam',
                'usage': 'internal',
                'barcode': self._valid_barcode(code + '-POSTPRODUCTION', company_id)
            },
        })
        return values

    def _get_sequence_values(self):
        values = super(StockWarehouse, self)._get_sequence_values()
        values.update({
            'pbm_type_id': {'name': self.name + ' ' + _('Sequence picking before manufacturing'), 'prefix': self.code + '/PC/', 'padding': 5},
            'sam_type_id': {'name': self.name + ' ' + _('Sequence stock after manufacturing'), 'prefix': self.code + '/SFP/', 'padding': 5},
            'manu_type_id': {'name': self.name + ' ' + _('Sequence production'), 'prefix': self.code + '/MO/', 'padding': 5},
        })
        return values

    def _get_picking_type_create_values(self, max_sequence):
        data, next_sequence = super(StockWarehouse, self)._get_picking_type_create_values(max_sequence)
        data.update({
            'pbm_type_id': {
                'name': _('Pick Components'),
                'code': 'internal',
                'use_create_lots': True,
                'use_existing_lots': True,
                'default_location_src_id': self.lot_stock_id.id,
                'default_location_dest_id': self.pbm_loc_id.id,
                'sequence': next_sequence + 1
            },
            'sam_type_id': {
                'name': _('Store Finished Product'),
                'code': 'internal',
                'use_create_lots': True,
                'use_existing_lots': True,
                'default_location_src_id': self.sam_loc_id.id,
                'default_location_dest_id': self.lot_stock_id.id,
                'sequence': next_sequence + 3
            },
            'manu_type_id': {
                'name': _('Manufacturing'),
                'code': 'mrp_operation',
                'use_create_lots': True,
                'use_existing_lots': True,
                'sequence': next_sequence + 2
            },
        })
        return data, max_sequence + 4

    def _get_picking_type_update_values(self):
        data = super(StockWarehouse, self)._get_picking_type_update_values()
        data.update({
            'pbm_type_id': {'active': self.manufacture_to_resupply and self.manufacture_steps in ('pbm', 'pbm_sam')},
            'sam_type_id': {'active': self.manufacture_to_resupply and self.manufacture_steps == 'pbm_sam'},
            'manu_type_id': {
                'active': self.manufacture_to_resupply,
                'default_location_src_id': self.manufacture_steps in ('pbm', 'pbm_sam') and self.pbm_loc_id.id or self.lot_stock_id.id,
                'default_location_dest_id': self.manufacture_steps == 'pbm_sam' and self.sam_loc_id.id or self.lot_stock_id.id,
            },
        })
        return data

    @api.multi
    def write(self, vals):
        if any(field in vals for field in ('manufacture_steps', 'manufacture_to_resupply')):
            for warehouse in self:
                warehouse._update_location_manufacture(vals.get('manufacture_steps', warehouse.manufacture_steps))
        return super(StockWarehouse, self).write(vals)

    @api.multi
    def _get_all_routes(self):
        routes = super(StockWarehouse, self)._get_all_routes()
        routes |= self.filtered(lambda self: self.manufacture_to_resupply and self.manufacture_pull_id and self.manufacture_pull_id.route_id).mapped('manufacture_pull_id').mapped('route_id')
        return routes

    def _update_location_manufacture(self, new_manufacture_step):
        switch_warehouses = self.filtered(lambda wh: wh.manufacture_steps != new_manufacture_step)
        loc_warehouse = switch_warehouses.filtered(lambda wh: not wh._location_used(wh.pbm_loc_id))
        if loc_warehouse:
            loc_warehouse.mapped('pbm_loc_id').write({'active': False})
        loc_warehouse = switch_warehouses.filtered(lambda wh: not wh._location_used(wh.sam_loc_id))
        if loc_warehouse:
            loc_warehouse.mapped('sam_loc_id').write({'active': False})
        if new_manufacture_step != 'mrp_one_step':
            self.mapped('pbm_loc_id').write({'active': True})
        if new_manufacture_step == 'pbm_sam':
            self.mapped('sam_loc_id').write({'active': True})

    @api.multi
    def _update_name_and_code(self, name=False, code=False):
        res = super(StockWarehouse, self)._update_name_and_code(name, code)
        # change the manufacture stock rule name
        for warehouse in self:
            if warehouse.manufacture_pull_id and name:
                warehouse.manufacture_pull_id.write({'name': warehouse.manufacture_pull_id.name.replace(warehouse.name, name, 1)})
        return res
