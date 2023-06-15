# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import split_every


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    manufacture_to_resupply = fields.Boolean(
        'Manufacture to Resupply', default=True,
        help="When products are manufactured, they can be manufactured in this warehouse.")
    manufacture_pull_id = fields.Many2one(
        'stock.rule', 'Manufacture Rule')
    manufacture_mto_pull_id = fields.Many2one(
        'stock.rule', 'Manufacture MTO Rule')
    pbm_mto_pull_id = fields.Many2one(
        'stock.rule', 'Picking Before Manufacturing MTO Rule')
    sam_rule_id = fields.Many2one(
        'stock.rule', 'Stock After Manufacturing Rule')
    manu_type_id = fields.Many2one(
        'stock.picking.type', 'Manufacturing Operation Type',
        domain="[('code', '=', 'mrp_operation'), ('company_id', '=', company_id)]", check_company=True)

    pbm_type_id = fields.Many2one('stock.picking.type', 'Picking Before Manufacturing Operation Type', check_company=True)
    sam_type_id = fields.Many2one('stock.picking.type', 'Stock After Manufacturing Operation Type', check_company=True)

    manufacture_steps = fields.Selection([
        ('mrp_one_step', 'Manufacture (1 step)'),
        ('pbm', 'Pick components and then manufacture (2 steps)'),
        ('pbm_sam', 'Pick components, manufacture and then store products (3 steps)')],
        'Manufacture', default='mrp_one_step', required=True,
        help="Produce : Move the components to the production location\
        directly and start the manufacturing process.\nPick / Produce : Unload\
        the components from the Stock to Input location first, and then\
        transfer it to the Production location.")

    pbm_route_id = fields.Many2one('stock.route', 'Picking Before Manufacturing Route', ondelete='restrict')

    pbm_loc_id = fields.Many2one('stock.location', 'Picking before Manufacturing Location', check_company=True)
    sam_loc_id = fields.Many2one('stock.location', 'Stock after Manufacturing Location', check_company=True)

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
            result[warehouse.id].update(warehouse._get_receive_rules_dict())
        return result

    @api.model
    def _get_production_location(self):
        location = self.env['stock.location'].search([('usage', '=', 'production'), ('company_id', '=', self.company_id.id)], limit=1)
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
        routes.update(self._get_receive_routes_values('manufacture_to_resupply'))
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
        location_src = self.manufacture_steps == 'mrp_one_step' and self.lot_stock_id or self.pbm_loc_id
        production_location = self._get_production_location()
        location_dest_id = self.manufacture_steps == 'pbm_sam' and self.sam_loc_id or self.lot_stock_id
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
                    'name': self._format_rulename(location_dest_id, False, 'Production'),
                    'location_dest_id': location_dest_id.id,
                    'propagate_cancel': self.manufacture_steps == 'pbm_sam'
                },
            },
            'manufacture_mto_pull_id': {
                'depends': ['manufacture_steps', 'manufacture_to_resupply'],
                'create_values': {
                    'procure_method': 'mts_else_mto',
                    'company_id': self.company_id.id,
                    'action': 'pull',
                    'auto': 'manual',
                    'route_id': self._find_global_route('stock.route_warehouse0_mto', _('Make To Order')).id,
                    'location_dest_id': production_location.id,
                    'location_src_id': location_src.id,
                    'picking_type_id': self.manu_type_id.id
                },
                'update_values': {
                    'name': self._format_rulename(location_src, production_location, 'MTO'),
                    'active': self.manufacture_to_resupply,
                },
            },
            'pbm_mto_pull_id': {
                'depends': ['manufacture_steps', 'manufacture_to_resupply'],
                'create_values': {
                    'procure_method': 'make_to_order',
                    'company_id': self.company_id.id,
                    'action': 'pull',
                    'auto': 'manual',
                    'route_id': self._find_global_route('stock.route_warehouse0_mto', _('Make To Order')).id,
                    'name': self._format_rulename(self.lot_stock_id, self.pbm_loc_id, 'MTO'),
                    'location_dest_id': self.pbm_loc_id.id,
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
                    'route_id': self._find_global_route('mrp.route_warehouse0_manufacture', _('Manufacture')).id,
                    'name': self._format_rulename(self.sam_loc_id, self.lot_stock_id, False),
                    'location_dest_id': self.lot_stock_id.id,
                    'location_src_id': self.sam_loc_id.id,
                    'picking_type_id': self.sam_type_id.id
                },
                'update_values': {
                    'active': self.manufacture_steps == 'pbm_sam' and self.manufacture_to_resupply,
                }
            }

        })
        return rules

    def _get_locations_values(self, vals, code=False):
        values = super(StockWarehouse, self)._get_locations_values(vals, code=code)
        def_values = self.default_get(['company_id', 'manufacture_steps'])
        manufacture_steps = vals.get('manufacture_steps', def_values['manufacture_steps'])
        code = vals.get('code') or code or ''
        code = code.replace(' ', '').upper()
        company_id = vals.get('company_id', def_values['company_id'])
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

    def _get_sequence_values(self, name=False, code=False):
        values = super(StockWarehouse, self)._get_sequence_values(name=name, code=code)
        values.update({
            'pbm_type_id': {'name': self.name + ' ' + _('Sequence picking before manufacturing'), 'prefix': self.code + '/PC/', 'padding': 5, 'company_id': self.company_id.id},
            'sam_type_id': {'name': self.name + ' ' + _('Sequence stock after manufacturing'), 'prefix': self.code + '/SFP/', 'padding': 5, 'company_id': self.company_id.id},
            'manu_type_id': {'name': self.name + ' ' + _('Sequence production'), 'prefix': self.code + '/MO/', 'padding': 5, 'company_id': self.company_id.id},
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
                'sequence': next_sequence + 1,
                'sequence_code': 'PC',
                'company_id': self.company_id.id,
            },
            'sam_type_id': {
                'name': _('Store Finished Product'),
                'code': 'internal',
                'use_create_lots': True,
                'use_existing_lots': True,
                'default_location_src_id': self.sam_loc_id.id,
                'default_location_dest_id': self.lot_stock_id.id,
                'sequence': next_sequence + 3,
                'sequence_code': 'SFP',
                'company_id': self.company_id.id,
            },
            'manu_type_id': {
                'name': _('Manufacturing'),
                'code': 'mrp_operation',
                'use_create_lots': True,
                'use_existing_lots': True,
                'sequence': next_sequence + 2,
                'sequence_code': 'MO',
                'company_id': self.company_id.id,
            },
        })
        return data, max_sequence + 4

    def _get_picking_type_update_values(self):
        data = super(StockWarehouse, self)._get_picking_type_update_values()
        data.update({
            'pbm_type_id': {
                'active': self.manufacture_to_resupply and self.manufacture_steps in ('pbm', 'pbm_sam') and self.active,
                'barcode': self.code.replace(" ", "").upper() + "-PC",
            },
            'sam_type_id': {
                'active': self.manufacture_to_resupply and self.manufacture_steps == 'pbm_sam' and self.active,
                'barcode': self.code.replace(" ", "").upper() + "-SFP",
            },
            'manu_type_id': {
                'active': self.manufacture_to_resupply and self.active,
                'default_location_src_id': self.manufacture_steps in ('pbm', 'pbm_sam') and self.pbm_loc_id.id or self.lot_stock_id.id,
                'default_location_dest_id': self.manufacture_steps == 'pbm_sam' and self.sam_loc_id.id or self.lot_stock_id.id,
            },
        })
        return data

    def _create_missing_locations(self, vals):
        super()._create_missing_locations(vals)
        for company_id in self.company_id:
            location = self.env['stock.location'].search([('usage', '=', 'production'), ('company_id', '=', company_id.id)], limit=1)
            if not location:
                company_id._create_production_location()

    def write(self, vals):
        if any(field in vals for field in ('manufacture_steps', 'manufacture_to_resupply')):
            for warehouse in self:
                warehouse._update_location_manufacture(vals.get('manufacture_steps', warehouse.manufacture_steps))
        return super(StockWarehouse, self).write(vals)

    def _get_all_routes(self):
        routes = super(StockWarehouse, self)._get_all_routes()
        routes |= self.filtered(lambda self: self.manufacture_to_resupply and self.manufacture_pull_id and self.manufacture_pull_id.route_id).mapped('manufacture_pull_id').mapped('route_id')
        return routes

    def _update_location_manufacture(self, new_manufacture_step):
        self.mapped('pbm_loc_id').write({'active': new_manufacture_step != 'mrp_one_step'})
        self.mapped('sam_loc_id').write({'active': new_manufacture_step == 'pbm_sam'})

    def _update_name_and_code(self, name=False, code=False):
        res = super(StockWarehouse, self)._update_name_and_code(name, code)
        # change the manufacture stock rule name
        for warehouse in self:
            if warehouse.manufacture_pull_id and name:
                warehouse.manufacture_pull_id.write({'name': warehouse.manufacture_pull_id.name.replace(warehouse.name, name, 1)})
        return res

class Orderpoint(models.Model):
    _inherit = "stock.warehouse.orderpoint"

    @api.constrains('product_id')
    def check_product_is_not_kit(self):
        if self.env['mrp.bom'].search(['|', ('product_id', 'in', self.product_id.ids),
                                            '&', ('product_id', '=', False), ('product_tmpl_id', 'in', self.product_id.product_tmpl_id.ids),
                                       ('type', '=', 'phantom')], count=True):
            raise ValidationError(_("A product with a kit-type bill of materials can not have a reordering rule."))

    def _get_orderpoint_products(self):
        non_kit_ids = []
        for products in split_every(2000, super()._get_orderpoint_products().ids, self.env['product.product'].browse):
            kit_ids = set(k.id for k in self.env['mrp.bom']._bom_find(products, bom_type='phantom').keys())
            non_kit_ids.extend(id_ for id_ in products.ids if id_ not in kit_ids)
            products.invalidate_recordset()
        return self.env['product.product'].browse(non_kit_ids)
