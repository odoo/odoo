# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import namedtuple
from datetime import datetime
from dateutil import relativedelta

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

import logging

_logger = logging.getLogger(__name__)


class Warehouse(models.Model):
    _name = "stock.warehouse"
    _description = "Warehouse"
    # namedtuple used in helper methods generating values for routes
    Routing = namedtuple('Routing', ['from_loc', 'dest_loc', 'picking_type'])

    name = fields.Char('Warehouse Name', index=True, required=True)
    active = fields.Boolean('Active', default=True)
    company_id = fields.Many2one(
        'res.company', 'Company', default=lambda self: self.env['res.company']._company_default_get('stock.inventory'),
        index=True, readonly=True, required=True,
        help='The company is automatically set from your user preferences.')
    partner_id = fields.Many2one('res.partner', 'Address')
    view_location_id = fields.Many2one('stock.location', 'View Location', domain=[('usage', '=', 'view')], required=True)
    lot_stock_id = fields.Many2one('stock.location', 'Location Stock', domain=[('usage', '=', 'internal')], required=True)
    code = fields.Char('Short Name', required=True, size=5, help="Short name used to identify your warehouse")
    route_ids = fields.Many2many(
        'stock.location.route', 'stock_route_warehouse', 'warehouse_id', 'route_id',
        'Routes', domain="[('warehouse_selectable', '=', True)]",
        help='Defaults routes through the warehouse')
    reception_steps = fields.Selection([
        ('one_step', 'Receive goods directly in stock (1 step)'),
        ('two_steps', 'Unload in input location then go to stock (2 steps)'),
        ('three_steps', 'Unload in input location, go through a quality control before being admitted in stock (3 steps)')],
        'Incoming Shipments', default='one_step', required=True,
        help="Default incoming route to follow")
    delivery_steps = fields.Selection([
        ('ship_only', 'Ship directly from stock (Ship only)'),
        ('pick_ship', 'Bring goods to output location before shipping (Pick + Ship)'),
        ('pick_pack_ship', 'Make packages into a dedicated location, then bring them to the output location for shipping (Pick + Pack + Ship)')],
        'Outgoing Shippings', default='ship_only', required=True,
        help="Default outgoing route to follow")
    wh_input_stock_loc_id = fields.Many2one('stock.location', 'Input Location')
    wh_qc_stock_loc_id = fields.Many2one('stock.location', 'Quality Control Location')
    wh_output_stock_loc_id = fields.Many2one('stock.location', 'Output Location')
    wh_pack_stock_loc_id = fields.Many2one('stock.location', 'Packing Location')
    mto_pull_id = fields.Many2one('procurement.rule', 'MTO rule')
    pick_type_id = fields.Many2one('stock.picking.type', 'Pick Type')
    pack_type_id = fields.Many2one('stock.picking.type', 'Pack Type')
    out_type_id = fields.Many2one('stock.picking.type', 'Out Type')
    in_type_id = fields.Many2one('stock.picking.type', 'In Type')
    int_type_id = fields.Many2one('stock.picking.type', 'Internal Type')
    crossdock_route_id = fields.Many2one('stock.location.route', 'Crossdock Route', ondelete='restrict')
    reception_route_id = fields.Many2one('stock.location.route', 'Receipt Route', ondelete='restrict')
    delivery_route_id = fields.Many2one('stock.location.route', 'Delivery Route', ondelete='restrict')
    resupply_wh_ids = fields.Many2many(
        'stock.warehouse', 'stock_wh_resupply_table', 'supplied_wh_id', 'supplier_wh_id',
        'Resupply Warehouses')
    resupply_route_ids = fields.One2many(
        'stock.location.route', 'supplied_wh_id', 'Resupply Routes',
        help="Routes will be created for these resupply warehouses and you can select them on products and product categories")
    default_resupply_wh_id = fields.Many2one(
        'stock.warehouse', 'Default Resupply Warehouse',
        help="Goods will always be resupplied from this warehouse")

    _sql_constraints = [
        ('warehouse_name_uniq', 'unique(name, company_id)', 'The name of the warehouse must be unique per company!'),
        ('warehouse_code_uniq', 'unique(code, company_id)', 'The code of the warehouse must be unique per company!'),
    ]

    @api.depends('default_resupply_wh_id', 'resupply_wh_ids')
    def onchange_resupply_warehouses(self):
        # If we are removing the default resupply, we don't have default_resupply_wh_id # TDE note: and we want one
        self.resupply_wh_ids |= self.default_resupply_wh_id

    @api.model
    def create(self, vals):
        # create view location for warehouse then create all locations
        loc_vals = {'name': _(vals.get('code')), 'usage': 'view',
                    'location_id': self.env.ref('stock.stock_location_locations').id}
        if vals.get('company_id'):
            loc_vals['company_id'] = vals.get('company_id')
        vals['view_location_id'] = self.env['stock.location'].create(loc_vals).id

        def_values = self.default_get(['reception_steps', 'delivery_steps'])
        reception_steps = vals.get('reception_steps',  def_values['reception_steps'])
        delivery_steps = vals.get('delivery_steps', def_values['delivery_steps'])
        sub_locations = {
            'lot_stock_id': {'name': _('Stock'), 'active': True, 'usage': 'internal'},
            'wh_input_stock_loc_id': {'name': _('Input'), 'active': reception_steps != 'one_step', 'usage': 'internal'},
            'wh_qc_stock_loc_id': {'name': _('Quality Control'), 'active': reception_steps == 'three_steps', 'usage': 'internal'},
            'wh_output_stock_loc_id': {'name': _('Output'), 'active': delivery_steps != 'ship_only', 'usage': 'internal'},
            'wh_pack_stock_loc_id': {'name': _('Packing Zone'), 'active': delivery_steps == 'pick_pack_ship', 'usage': 'internal'},
        }
        for field_name, values in sub_locations.iteritems():
            values['location_id'] = vals['view_location_id']
            if vals.get('company_id'):
                values['company_id'] = vals.get('company_id')
            vals[field_name] = self.env['stock.location'].with_context(active_test=False).create(values).id

        # actually create WH
        warehouse = super(Warehouse, self).create(vals)
        # create sequences and operation types
        new_vals = warehouse.create_sequences_and_picking_types()
        warehouse.write(new_vals)  # TDE FIXME: use super ?
        # create routes and push/procurement rules
        route_vals = warehouse.create_routes()
        warehouse.write(route_vals)
        # update partner data if partner assigned
        if vals.get('partner_id'):
            self._update_partner_data(vals['partner_id'], vals.get('company_id'))
        return warehouse

    @api.multi
    def write(self, vals):
        Route = self.env['stock.location.route']
        warehouses = self.with_context(active_test=False)  # TDE FIXME: check this

        if vals.get('code') or vals.get('name'):
            warehouses._update_name_and_code(vals.get('name'), vals.get('code'))

        # activate and deactivate location according to reception and delivery option
        if vals.get('reception_steps'):
            warehouses._update_location_reception(vals['reception_steps'])
        if vals.get('delivery_steps'):
            warehouses._update_location_delivery(vals['delivery_steps'])
        if vals.get('reception_steps') or vals.get('delivery_steps'):
            warehouses._update_reception_delivery_resupply(vals.get('reception_steps'), vals.get('delivery_steps'))

        if vals.get('resupply_wh_ids') and not vals.get('resupply_route_ids'):
            resupply_whs = self.resolve_2many_commands('resupply_wh_ids', vals['resupply_wh_ids'])
            new_resupply_whs = self.browse([wh['id'] for wh in resupply_whs])
            old_resupply_whs = {warehouse.id: warehouse.resupply_wh_ids for warehouse in warehouses}

        if 'default_resupply_wh_id' in vals:
            if vals.get('default_resupply_wh_id') and any(vals['default_resupply_wh_id'] == warehouse.id for warehouse in warehouses):
                raise UserError(_('The default resupply warehouse should be different than the warehouse itself!'))
            for warehouse in warehouses.filtered(lambda wh: wh.default_resupply_wh_id):
                # remove the existing resupplying route on the warehouse
                to_remove_routes = Route.search([('supplied_wh_id', '=', warehouse.id), ('supplier_wh_id', '=', warehouse.default_resupply_wh_id.id)])
                for inter_wh_route in to_remove_routes:
                    warehouse.write({'route_ids': [(3, inter_wh_route.id)]})

        # If another partner assigned
        if vals.get('partner_id'):
            warehouses._update_partner_data(vals['partner_id'], vals.get('company_id'))
        res = super(Warehouse, self).write(vals)

        # check if we need to delete and recreate route
        if vals.get('reception_steps') or vals.get('delivery_steps'):
            warehouses._update_routes()

        if vals.get('resupply_wh_ids') and not vals.get('resupply_route_ids'):
            for warehouse in warehouses:
                to_add = new_resupply_whs - old_resupply_whs[warehouse.id]
                to_remove = old_resupply_whs[warehouse.id] - new_resupply_whs
                if to_add:
                    warehouse.create_resupply_routes(to_add, warehouse.default_resupply_wh_id)
                if to_remove:
                    Route.search([('supplied_wh_id', '=', warehouse.id), ('supplier_wh_id', 'in', to_remove.ids)]).write({'active': False})
                    # TDE FIXME: shouldn't we remove procurement rules also ? because this could make them global (not sure)

        return res

    @api.model
    def _update_partner_data(self, partner_id, company_id):
        if not partner_id:
            return
        ResCompany = self.env['res.company']
        if company_id:
            transit_loc = ResCompany.browse(company_id).internal_transit_location_id.id
        else:
            transit_loc = ResCompany._company_default_get('stock.warehouse').internal_transit_location_id.id
        self.env['res.partner'].browse(partner_id).write({'property_stock_customer': transit_loc, 'property_stock_supplier': transit_loc})

    def create_sequences_and_picking_types(self):
        IrSequenceSudo = self.env['ir.sequence'].sudo()
        PickingType = self.env['stock.picking.type']

        input_loc, output_loc = self._get_input_output_locations(self.reception_steps, self.delivery_steps)

        # choose the next available color for the operation types of this warehouse
        all_used_colors = [res['color'] for res in PickingType.search_read([('warehouse_id', '!=', False), ('color', '!=', False)], ['color'], order='color')]
        available_colors = [zef for zef in [0, 3, 4, 5, 6, 7, 8, 1, 2] if zef not in all_used_colors]
        color = available_colors and available_colors[0] or 0

        # suit for each warehouse: reception, internal, pick, pack, ship
        max_sequence = PickingType.search_read([('sequence', '!=', False)], ['sequence'], limit=1, order='sequence desc')
        max_sequence = max_sequence and max_sequence[0]['sequence'] or 0

        warehouse_data = {}
        sequence_data = self._get_sequence_values()
        # tde todo: backport sequence fix
        create_data = {
            'in_type_id': {
                'name': _('Receipts'),
                'code': 'incoming',
                'use_create_lots': True,
                'use_existing_lots': False,
                'default_location_src_id': False,
                'sequence': max_sequence + 1,
            }, 'out_type_id': {
                'name': _('Delivery Orders'),
                'code': 'outgoing',
                'use_create_lots': False,
                'use_existing_lots': True,
                'default_location_dest_id': False,
                'sequence': max_sequence + 5,
            }, 'pack_type_id': {
                'name': _('Pack'),
                'code': 'internal',
                'use_create_lots': False,
                'use_existing_lots': True,
                'default_location_src_id': self.wh_pack_stock_loc_id.id,
                'default_location_dest_id': output_loc.id,
                'sequence': max_sequence + 4,
            }, 'pick_type_id': {
                'name': _('Pick'),
                'code': 'internal',
                'use_create_lots': False,
                'use_existing_lots': True,
                'default_location_src_id': self.lot_stock_id.id,
                'sequence': max_sequence + 3,
            }, 'int_type_id': {
                'name': _('Internal Transfers'),
                'code': 'internal',
                'use_create_lots': False,
                'use_existing_lots': True,
                'default_location_src_id': self.lot_stock_id.id,
                'default_location_dest_id': self.lot_stock_id.id,
                'active': self.reception_steps != 'one_step' or self.delivery_steps != 'ship_only' or self.user_has_groups('stock.group_stock_multi_locations'),
                'sequence': max_sequence + 2,
            },
        }
        data = self._get_picking_type_values(self.reception_steps, self.delivery_steps, self.wh_pack_stock_loc_id)
        for field_name, values in data.iteritems():
            data[field_name].update(create_data[field_name])

        for picking_type, values in data.iteritems():
            sequence = IrSequenceSudo.create(sequence_data[picking_type])
            values.update(warehouse_id=self.id, color=color, sequence_id=sequence.id)
            warehouse_data[picking_type] = PickingType.create(values).id
        PickingType.browse(warehouse_data['out_type_id']).write({'return_picking_type_id': warehouse_data['in_type_id']})
        PickingType.browse(warehouse_data['in_type_id']).write({'return_picking_type_id': warehouse_data['out_type_id']})
        return warehouse_data

    @api.multi
    def create_routes(self):
        self.ensure_one()
        routes_data = self.get_routes_dict()

        reception_route = self._create_or_update_reception_route(routes_data)
        delivery_route = self._create_or_update_delivery_route(routes_data)
        mto_pull = self._create_or_update_mto_pull(routes_data)
        crossdock_route = self._create_or_update_crossdock_route(routes_data)

        # create route selectable on the product to resupply the warehouse from another one
        self.create_resupply_routes(self.resupply_wh_ids, self.default_resupply_wh_id)

        # return routes and mto procurement rule to store on the warehouse
        return {
            'route_ids': [(4, route.id) for route in reception_route | delivery_route | crossdock_route],
            'mto_pull_id': mto_pull.id,
            'reception_route_id': reception_route.id,
            'delivery_route_id': delivery_route.id,
            'crossdock_route_id': crossdock_route.id,
        }

    def _create_or_update_reception_route(self, routes_data):
        routes_data = routes_data or self.get_routes_dict()
        for warehouse in self:
            if warehouse.reception_route_id:
                reception_route = warehouse.reception_route_id
                reception_route.write({'name':  warehouse._format_routename(route_type=warehouse.reception_steps)})
                reception_route.pull_ids.write({'active': False})
                reception_route.push_ids.write({'active': False})
            else:
                reception_route = self.env['stock.location.route'].create(warehouse._get_reception_delivery_route_values(warehouse.reception_steps))
            # push / procurement (pull) rules for reception
            routings = routes_data[warehouse.id][warehouse.reception_steps]
            push_rules_list, pull_rules_list = warehouse._get_push_pull_rules_values(
                routings, values={'active': True, 'route_id': reception_route.id},
                push_values=None, pull_values={'procure_method': 'make_to_order'})
            for push_vals in push_rules_list:
                existing_push = self.env['stock.location.path'].search([
                    ('picking_type_id', '=', push_vals['picking_type_id']),
                    ('location_from_id', '=', push_vals['location_from_id']),
                    ('location_dest_id', '=', push_vals['location_dest_id']),
                    ('route_id', '=', push_vals['route_id']),
                    ('active', '=', False),
                ])
                if not existing_push:
                    self.env['stock.location.path'].create(push_vals)
                else:
                    existing_push.write({'active': True})
            for pull_vals in pull_rules_list:
                existing_pull = self.env['procurement.rule'].search([
                    ('picking_type_id', '=', pull_vals['picking_type_id']),
                    ('location_src_id', '=', pull_vals['location_src_id']),
                    ('location_id', '=', pull_vals['location_id']),
                    ('route_id', '=', pull_vals['route_id']),
                    ('active', '=', False),
                ])
                if not existing_pull:
                    self.env['procurement.rule'].create(pull_vals)
                else:
                    existing_pull.write({'active': True})
        return reception_route

    def _create_or_update_delivery_route(self, routes_data):
        """ Delivery (MTS) route """
        routes_data = routes_data or self.get_routes_dict()
        for warehouse in self:
            if warehouse.delivery_route_id:
                delivery_route = warehouse.delivery_route_id
                delivery_route.write({'name': warehouse._format_routename(route_type=warehouse.delivery_steps)})
                delivery_route.pull_ids.write({'active': False})
            else:
                delivery_route = self.env['stock.location.route'].create(warehouse._get_reception_delivery_route_values(warehouse.delivery_steps))
            # procurement (pull) rules for delivery
            routings = routes_data[warehouse.id][warehouse.delivery_steps]
            dummy, pull_rules_list = warehouse._get_push_pull_rules_values(
                routings, values={'active': True, 'route_id': delivery_route.id})
            for pull_vals in pull_rules_list:
                existing_pull = self.env['procurement.rule'].search([
                    ('picking_type_id', '=', pull_vals['picking_type_id']),
                    ('location_src_id', '=', pull_vals['location_src_id']),
                    ('location_id', '=', pull_vals['location_id']),
                    ('route_id', '=', pull_vals['route_id']),
                    ('active', '=', False),
                ])
                if not existing_pull:
                    self.env['procurement.rule'].create(pull_vals)
                else:
                    existing_pull.write({'active': True})
        return delivery_route

    def _create_or_update_mto_pull(self, routes_data):
        """ Create MTO procurement rule and link it to the generic MTO route """
        routes_data = routes_data or self.get_routes_dict()
        for warehouse in self:
            routings = routes_data[warehouse.id][warehouse.delivery_steps]
            if warehouse.mto_pull_id:
                mto_pull = warehouse.mto_pull_id
                mto_pull.write(warehouse._get_mto_pull_rules_values(routings)[0])
            else:
                mto_pull = self.env['procurement.rule'].create(warehouse._get_mto_pull_rules_values(routings)[0])
        return mto_pull

    def _create_or_update_crossdock_route(self, routes_data):
        """ Create or update the cross dock operations route, that can be set on
        products and product categories """
        routes_data = routes_data or self.get_routes_dict()
        for warehouse in self:
            if warehouse.crossdock_route_id:
                crossdock_route = warehouse.crossdock_route_id
                crossdock_route.write({'active': warehouse.reception_steps != 'one_step' and warehouse.delivery_steps != 'ship_only'})
            else:
                crossdock_route = self.env['stock.location.route'].create(warehouse._get_crossdock_route_values())
                # note: fixed cross-dock is logically mto
                routings = routes_data[warehouse.id]['crossdock']
                dummy, pull_rules_list = warehouse._get_push_pull_rules_values(
                    routings,
                    values={'active': warehouse.delivery_steps != 'ship_only' and warehouse.reception_steps != 'one_step', 'route_id': crossdock_route.id},
                    push_values=None, pull_values={'procure_method': 'make_to_order'})
                for pull_vals in pull_rules_list:
                    self.env['procurement.rule'].create(pull_vals)
        return crossdock_route

    def create_resupply_routes(self, supplier_warehouses, default_resupply_wh):
        Route = self.env['stock.location.route']
        Pull = self.env['procurement.rule']

        input_location, output_location = self._get_input_output_locations(self.reception_steps, self.delivery_steps)
        internal_transit_location, external_transit_location = self._get_transit_locations()

        for supplier_wh in supplier_warehouses:
            transit_location = internal_transit_location if supplier_wh.company_id == self.company_id else external_transit_location
            if not transit_location:
                continue
            output_location = supplier_wh.lot_stock_id if supplier_wh.delivery_steps == 'ship_only' else supplier_wh.wh_output_stock_loc_id
            # Create extra MTO rule (only for 'ship only' because in the other cases MTO rules already exists)
            if supplier_wh.delivery_steps == 'ship_only':
                Pull.create(supplier_wh._get_mto_pull_rules_values([
                    self.Routing(output_location, transit_location, supplier_wh.out_type_id)])[0])

            inter_wh_route = Route.create(self._get_inter_warehouse_route_values(supplier_wh))

            pull_rules_list = supplier_wh._get_supply_pull_rules_values(
                [self.Routing(output_location, transit_location, supplier_wh.out_type_id)],
                values={'route_id': inter_wh_route.id, 'propagate_warehouse_id': self.id})
            pull_rules_list += self._get_supply_pull_rules_values(
                [self.Routing(transit_location, input_location, self.in_type_id)],
                values={'route_id': inter_wh_route.id, 'propagate_warehouse_id': supplier_wh.id})
            for pull_rule_vals in pull_rules_list:
                Pull.create(pull_rule_vals)

            # if the warehouse is also set as default resupply method, assign this route automatically to the warehouse
            if supplier_wh == default_resupply_wh:
                (self | supplier_wh).write({'route_ids': [(4, inter_wh_route.id)]})

    # Routing tools
    # ------------------------------------------------------------

    def _get_input_output_locations(self, reception_steps, delivery_steps):
        return (self.lot_stock_id if reception_steps == 'one_step' else self.wh_input_stock_loc_id,
                self.lot_stock_id if delivery_steps == 'ship_only' else self.wh_output_stock_loc_id)

    def _get_transit_locations(self):
        return self.company_id.internal_transit_location_id, self.env.ref('stock.stock_location_inter_wh', raise_if_not_found=False) or self.env['stock.location']

    @api.model
    def _get_partner_locations(self):
        ''' returns a tuple made of the browse record of customer location and the browse record of supplier location'''
        Location = self.env['stock.location']
        customer_loc = self.env.ref('stock.stock_location_customers', raise_if_not_found=False)
        supplier_loc = self.env.ref('stock.stock_location_suppliers', raise_if_not_found=False)
        if not customer_loc:
            customer_loc = Location.search([('usage', '=', 'customer')], limit=1)
        if not supplier_loc:
            supplier_loc = Location.search([('usage', '=', 'supplier')], limit=1)
        if not customer_loc and not supplier_loc:
            raise UserError(_('Can\'t find any customer or supplier location.'))
        return customer_loc, supplier_loc

    def _get_route_name(self, route_type):
        names = {'one_step': _('Receipt in 1 step'), 'two_steps': _('Receipt in 2 steps'),
                 'three_steps': _('Receipt in 3 steps'), 'crossdock': _('Cross-Dock'),
                 'ship_only': _('Ship Only'), 'pick_ship': _('Pick + Ship'),
                 'pick_pack_ship': _('Pick + Pack + Ship')}
        return names[route_type]

    def get_routes_dict(self):
        # TDE todo: rename me (was get_routes_dict)
        customer_loc, supplier_loc = self._get_partner_locations()
        return dict((warehouse.id, {
            'one_step': [],
            'two_steps': [self.Routing(warehouse.wh_input_stock_loc_id, warehouse.lot_stock_id, warehouse.int_type_id)],
            'three_steps': [
                self.Routing(warehouse.wh_input_stock_loc_id, warehouse.wh_qc_stock_loc_id, warehouse.int_type_id),
                self.Routing(warehouse.wh_qc_stock_loc_id, warehouse.lot_stock_id, warehouse.int_type_id)],
            'crossdock': [
                self.Routing(warehouse.wh_input_stock_loc_id, warehouse.wh_output_stock_loc_id, warehouse.int_type_id),
                self.Routing(warehouse.wh_output_stock_loc_id, customer_loc, warehouse.out_type_id)],
            'ship_only': [self.Routing(warehouse.lot_stock_id, customer_loc, warehouse.out_type_id)],
            'pick_ship': [
                self.Routing(warehouse.lot_stock_id, warehouse.wh_output_stock_loc_id, warehouse.pick_type_id),
                self.Routing(warehouse.wh_output_stock_loc_id, customer_loc, warehouse.out_type_id)],
            'pick_pack_ship': [
                self.Routing(warehouse.lot_stock_id, warehouse.wh_pack_stock_loc_id, warehouse.pick_type_id),
                self.Routing(warehouse.wh_pack_stock_loc_id, warehouse.wh_output_stock_loc_id, warehouse.pack_type_id),
                self.Routing(warehouse.wh_output_stock_loc_id, customer_loc, warehouse.out_type_id)],
        }) for warehouse in self)

    @api.multi
    def _get_reception_delivery_route_values(self, route_type):
        return {
            'name': self._format_routename(route_type=route_type),
            'product_categ_selectable': True,
            'product_selectable': False,
            'sequence': 10,
        }

    @api.model
    @api.returns('stock.location.route', lambda value: value.id)
    def _get_mto_route(self):
        mto_route = self.env.ref('stock.route_warehouse0_mto', raise_if_not_found=False)
        if not mto_route:
            mto_route = self.env['stock.location.route'].search([('name', 'like', _('Make To Order'))], limit=1)
        if not mto_route:
            raise UserError(_('Can\'t find any generic Make To Order route.'))
        return mto_route

    def _get_inter_warehouse_route_values(self, supplier_warehouse):
        return {
            'name': _('%s: Supply Product from %s') % (self.name, supplier_warehouse.name),
            'warehouse_selectable': False,
            'product_selectable': True,
            'product_categ_selectable': True,
            'supplied_wh_id': self.id,
            'supplier_wh_id': supplier_warehouse.id}

    def _get_crossdock_route_values(self):
        return {
            'name': self._format_routename(route_type='crossdock'),
            'warehouse_selectable': False,
            'product_selectable': True,
            'product_categ_selectable': True,
            'active': self.delivery_steps != 'ship_only' and self.reception_steps != 'one_step',
            'sequence': 20}

    # Pull / Push tools
    # ------------------------------------------------------------

    @api.multi
    def _get_push_pull_rules_values(self, route_values, values=None, push_values=None, pull_values=None, name_suffix=''):
        first_rule = True
        push_rules_list, pull_rules_list = [], []
        for routing in route_values:
            route_push_values = {
                'name': self._format_rulename(routing.from_loc, routing.dest_loc, name_suffix),
                'location_from_id': routing.from_loc.id,
                'location_dest_id': routing.dest_loc.id,
                'auto': 'manual',
                'picking_type_id': routing.picking_type.id,
                'warehouse_id': self.id}
            route_push_values.update((values or {}).items() + (push_values or {}).items())
            push_rules_list.append(route_push_values)
            route_pull_values = {
                'name': self._format_rulename(routing.from_loc, routing.dest_loc, name_suffix),
                'location_src_id': routing.from_loc.id,
                'location_id': routing.dest_loc.id,
                'action': 'move',
                'picking_type_id': routing.picking_type.id,
                'procure_method': first_rule is True and 'make_to_stock' or 'make_to_order',
                'warehouse_id': self.id}
            route_pull_values.update((values or {}).items() + (pull_values or {}).items())
            pull_rules_list.append(route_pull_values)
            first_rule = False
        return push_rules_list, pull_rules_list

    def _get_mto_pull_rules_values(self, route_values):
        mto_route = self._get_mto_route()
        dummy, pull_rules_list = self._get_push_pull_rules_values(route_values, pull_values={
            'route_id': mto_route.id,
            'procure_method': 'make_to_order',
            'active': True}, name_suffix=_('MTO'))
        return pull_rules_list

    def _get_supply_pull_rules_values(self, route_values, values=None):
        dummy, pull_rules_list = self._get_push_pull_rules_values(route_values, values=values, pull_values={'active': True})
        for pull_rules in pull_rules_list:
            pull_rules['procure_method'] = self.lot_stock_id.id != pull_rules['location_src_id'] and 'make_to_order' or 'make_to_stock'  # first part of the resuply route is MTS
        return pull_rules_list

    def _update_reception_delivery_resupply(self, reception_new, delivery_new):
        """ Check if we need to change something to resupply warehouses and associated MTO rules """
        input_loc, output_loc = self._get_input_output_locations(reception_new, delivery_new)
        for warehouse in self:
            if reception_new and warehouse.reception_steps != reception_new and (warehouse.reception_steps == 'one_step' or reception_new == 'one_step'):
                warehouse._check_reception_resupply(input_loc)
            if delivery_new and warehouse.delivery_steps != delivery_new and (warehouse.delivery_steps == 'ship_only' or delivery_new == 'ship_only'):
                change_to_multiple = warehouse.delivery_steps == 'ship_only'
                warehouse._check_delivery_resupply(output_loc, change_to_multiple)

    def _check_delivery_resupply(self, new_location, change_to_multiple):
        """ Check if the resupply routes from this warehouse follow the changes of number of delivery steps
        Check routes being delivery bu this warehouse and change the rule going to transit location """
        Pull = self.env["procurement.rule"]
        routes = self.env['stock.location.route'].search([('supplier_wh_id', '=', self.id)])
        pulls = Pull.search(['&', ('route_id', 'in', routes.ids), ('location_id.usage', '=', 'transit')])
        pulls.write({
            'location_src_id': new_location.id,
            'procure_method': change_to_multiple and "make_to_order" or "make_to_stock"})
        if not change_to_multiple:
            # If single delivery we should create the necessary MTO rules for the resupply
            routings = [self.Routing(self.lot_stock_id , location, self.out_type_id) for location in pulls.mapped('location_id')]
            mto_pull_vals = self._get_mto_pull_rules_values(routings)
            for mto_pull_val in mto_pull_vals:
                Pull.create(mto_pull_val)
        else:
            # We need to delete all the MTO procurement rules, otherwise they risk to be used in the system
            Pull.search([
                '&', ('route_id', '=', self._get_mto_route().id),
                ('location_id.usage', '=', 'transit'),
                ('location_src_id', '=', self.lot_stock_id.id)]).write({'active': False})

    def _check_reception_resupply(self, new_location):
        """ Check routes being delivered by the warehouses (resupply routes) and
        change their rule coming from the transit location """
        routes = self.env['stock.location.route'].search([('supplied_wh_id', 'in', self.ids)])
        self.env['procurement.rule'].search([
            '&', ('route_id', 'in', routes.ids),
            ('location_src_id.usage', '=', 'transit')]).write({'location_id': new_location.id})

    @api.multi
    def _update_routes(self):
        routes_data = self.get_routes_dict()
        # change the default source and destination location and (de)activate operation types
        self._update_picking_type()
        self._create_or_update_delivery_route(routes_data)
        self._create_or_update_reception_route(routes_data)
        self._create_or_update_crossdock_route(routes_data)
        self._create_or_update_mto_pull(routes_data)
        return True

    @api.one
    def _update_picking_type(self):
        picking_type_values = self._get_picking_type_values(self.reception_steps, self.delivery_steps, self.wh_pack_stock_loc_id)
        for field_name, values in picking_type_values.iteritems():
            getattr(self, field_name).write(values)

    @api.multi
    def _update_name_and_code(self, new_name=False, new_code=False):
        if new_code:
            self.mapped('lot_stock_id').mapped('location_id').write({'name': new_code})
        if new_name:
            # TDE FIXME: replacing the route name ? not better to re-generate the route naming ?
            for warehouse in self:
                routes = warehouse.route_ids
                for route in routes:
                    route.write({'name': route.name.replace(warehouse.name, new_name, 1)})
                    for pull in route.pull_ids:
                        pull.write({'name': pull.name.replace(warehouse.name, new_name, 1)})
                    for push in route.push_ids:
                        push.write({'name': push.name.replace(warehouse.name, new_name, 1)})
                warehouse.mto_pull_id.write({'name': warehouse.mto_pull_id.name.replace(warehouse.name, new_name, 1)})
        for warehouse in self:
            sequence_data = warehouse._get_sequence_values()
            warehouse.in_type_id.sequence_id.write(sequence_data['in_type_id'])
            warehouse.out_type_id.sequence_id.write(sequence_data['out_type_id'])
            warehouse.pack_type_id.sequence_id.write(sequence_data['pack_type_id'])
            warehouse.pick_type_id.sequence_id.write(sequence_data['pick_type_id'])
            warehouse.int_type_id.sequence_id.write(sequence_data['int_type_id'])

    def _update_location_reception(self, new_reception_step):
        switch_warehouses = self.filtered(lambda wh: wh.reception_steps != new_reception_step and not wh._location_used(wh.wh_input_stock_loc_id))
        if switch_warehouses:
            (switch_warehouses.mapped('wh_input_stock_loc_id') + switch_warehouses.mapped('wh_qc_stock_loc_id')).write({'active': False})
        if new_reception_step == 'three_steps':
            self.mapped('wh_qc_stock_loc_id').write({'active': True})
        if new_reception_step != 'one_step':
            self.mapped('wh_input_stock_loc_id').write({'active': True})

    def _update_location_delivery(self, new_delivery_step):
        switch_warehouses = self.filtered(lambda wh: wh.delivery_steps != new_delivery_step)
        loc_warehouse = switch_warehouses.filtered(lambda wh: not wh._location_used(wh.wh_output_stock_loc_id))
        if loc_warehouse:
            loc_warehouse.mapped('wh_output_stock_loc_id').write({'active': False})
        loc_warehouse = switch_warehouses.filtered(lambda wh: not wh._location_used(wh.wh_pack_stock_loc_id))
        if loc_warehouse:
            loc_warehouse.mapped('wh_pack_stock_loc_id').write({'active': False})
        if new_delivery_step == 'pick_pack_ship':
            self.mapped('wh_pack_stock_loc_id').write({'active': True})
        if new_delivery_step != 'ship_only':
            self.mapped('wh_output_stock_loc_id').write({'active': True})

    def _location_used(self, location):
        pulls = self.env['procurement.rule'].search_count([
            '&',
            ('route_id', 'not in', [x.id for x in self.route_ids]),
            '|', ('location_src_id', '=', location.id),
            ('location_id', '=', location.id)])
        if pulls:
            return True
        pushs = self.env['stock.location.path'].search_count([
            '&',
            ('route_id', 'not in', [x.id for x in self.route_ids]),
            '|', ('location_from_id', '=', location.id),
            ('location_dest_id', '=', location.id)])
        if pushs:
            return True
        return False

    # Misc
    # ------------------------------------------------------------

    def _get_picking_type_values(self, reception_steps, delivery_steps, pack_stop_location):
        input_loc, output_loc = self._get_input_output_locations(reception_steps, delivery_steps)
        return {
            'in_type_id': {'default_location_dest_id': input_loc.id},
            'out_type_id': {'default_location_src_id': output_loc.id},
            'pick_type_id': {
                'active': delivery_steps != 'ship_only',
                'default_location_dest_id': output_loc.id if delivery_steps == 'pick_ship' else pack_stop_location.id},
            'pack_type_id': {'active': delivery_steps == 'pick_pack_ship'},
            'int_type_id': {},
        }

    def _get_sequence_values(self):
        return {
            'in_type_id': {'name': self.name + _('Sequence in'), 'prefix': self.code + '/IN/', 'padding': 5},
            'out_type_id': {'name': self.name + _('Sequence out'), 'prefix': self.code + '/OUT/', 'padding': 5},
            'pack_type_id': {'name': self.name + _('Sequence packing'), 'prefix': self.code + '/PACK/', 'padding': 5},
            'pick_type_id': {'name': self.name + _('Sequence picking'), 'prefix': self.code + '/PICK/', 'padding': 5},
            'int_type_id': {'name': self.name + _('Sequence internal'), 'prefix': self.code + '/INT/', 'padding': 5},
        }

    @api.multi
    def _format_rulename(self, from_loc, dest_loc, suffix):
        return '%s: %s -> %s%s' % (self.code, from_loc.name, dest_loc.name, suffix)

    @api.multi
    def _format_routename(self, name=None, route_type=None):
        if route_type:
            name = self._get_route_name(route_type)
        return '%s: %s' % (self.name, name)

    @api.returns('self')
    @api.multi
    def _get_all_routes(self):
        # TDE FIXME: check overrides
        routes = self.mapped('route_ids') | self.mapped('mto_pull_id').mapped('route_id')
        routes |= self.env["stock.location.route"].search([('supplied_wh_id', 'in', self.ids)])
        return routes
    get_all_routes_for_wh = _get_all_routes

    @api.multi
    def action_view_all_routes(self):
        routes = self._get_all_routes()
        return {
            'name': _('Warehouse\'s Routes'),
            'domain': [('id', 'in', routes.ids)],
            'res_model': 'stock.location.route',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'tree,form',
            'view_type': 'form',
            'limit': 20
        }


class Orderpoint(models.Model):
    """ Defines Minimum stock rules. """
    _name = "stock.warehouse.orderpoint"
    _description = "Minimum Inventory Rule"

    @api.model
    def default_get(self, fields):
        res = super(Orderpoint, self).default_get(fields)
        warehouse = None
        if 'warehouse_id' not in res and res.get('company_id'):
            warehouse = self.env['stock.warehouse'].search([('company_id', '=', res['company_id'])], limit=1)
        if warehouse:
            res['warehouse_id'] = warehouse.id
            res['location_id'] = warehouse.lot_stock_id.id
        return res

    name = fields.Char(
        'Name', copy=False, required=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('stock.orderpoint'))
    active = fields.Boolean(
        'Active', default=True,
        help="If the active field is set to False, it will allow you to hide the orderpoint without removing it.")
    warehouse_id = fields.Many2one(
        'stock.warehouse', 'Warehouse',
        ondelete="cascade", required=True)
    location_id = fields.Many2one(
        'stock.location', 'Location',
        ondelete="cascade", required=True)
    product_id = fields.Many2one(
        'product.product', 'Product',
        domain=[('type', '=', 'product')], ondelete='cascade', required=True)
    product_uom = fields.Many2one(
        'product.uom', 'Product Unit of Measure', related='product_id.uom_id',
        readonly=True, required=True,
        default=lambda self: self._context.get('product_uom', False))
    product_min_qty = fields.Float(
        'Minimum Quantity', digits=dp.get_precision('Product Unit of Measure'), required=True,
        help="When the virtual stock goes below the Min Quantity specified for this field, Odoo generates "
             "a procurement to bring the forecasted quantity to the Max Quantity.")
    product_max_qty = fields.Float(
        'Maximum Quantity', digits=dp.get_precision('Product Unit of Measure'), required=True,
        help="When the virtual stock goes below the Min Quantity, Odoo generates "
             "a procurement to bring the forecasted quantity to the Quantity specified as Max Quantity.")
    qty_multiple = fields.Float(
        'Qty Multiple', digits=dp.get_precision('Product Unit of Measure'),
        default=1, required=True,
        help="The procurement quantity will be rounded up to this multiple.  If it is 0, the exact quantity will be used.")
    procurement_ids = fields.One2many('procurement.order', 'orderpoint_id', 'Created Procurements')
    group_id = fields.Many2one(
        'procurement.group', 'Procurement Group', copy=False,
        help="Moves created through this orderpoint will be put in this procurement group. If none is given, the moves generated by procurement rules will be grouped into one big picking.")
    company_id = fields.Many2one(
        'res.company', 'Company', required=True,
        default=lambda self: self.env['res.company']._company_default_get('stock.warehouse.orderpoint'))
    lead_days = fields.Integer(
        'Lead Time', default=1,
        help="Number of days after the orderpoint is triggered to receive the products or to order to the vendor")
    lead_type = fields.Selection(
        [('net', 'Day(s) to get the products'), ('supplier', 'Day(s) to purchase')], 'Lead Type',
        required=True, default='supplier')

    _sql_constraints = [
        ('qty_multiple_check', 'CHECK( qty_multiple >= 0 )', 'Qty Multiple must be greater than or equal to zero.'),
    ]

    @api.constrains('product_id')
    def _check_product_uom(self):
        ''' Check if the UoM has the same category as the product standard UoM '''
        if any(orderpoint.product_id.uom_id.category_id != orderpoint.product_uom.category_id for orderpoint in self):
            raise ValidationError(_('You have to select a product unit of measure in the same category than the default unit of measure of the product'))

    @api.onchange('warehouse_id')
    def onchange_warehouse_id(self):
        """ Finds location id for changed warehouse. """
        if self.warehouse_id:
            self.location_id = self.warehouse_id.lot_stock_id.id

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.product_uom = self.product_id.uom_id.id
            return {'domain':  {'product_uom': [('category_id', '=', self.product_id.uom_id.category_id.id)]}}
        return {'domain': {'product_uom': []}}

    @api.multi
    def subtract_procurements_from_orderpoints(self):
        '''This function returns quantity of product that needs to be deducted from the orderpoint computed quantity because there's already a procurement created with aim to fulfill it.
        '''
        self._cr.execute("""SELECT orderpoint.id, procurement.id, procurement.product_uom, procurement.product_qty, template.uom_id, move.product_qty
            FROM stock_warehouse_orderpoint orderpoint
            JOIN procurement_order AS procurement ON procurement.orderpoint_id = orderpoint.id
            JOIN product_product AS product ON product.id = procurement.product_id
            JOIN product_template AS template ON template.id = product.product_tmpl_id
            LEFT JOIN stock_move AS move ON move.procurement_id = procurement.id
            WHERE procurement.state not in ('done', 'cancel')
                AND (move.state IS NULL OR move.state != 'draft')
                AND orderpoint.id IN %s
            ORDER BY orderpoint.id, procurement.id
        """, (tuple(self.ids),))
        UoM = self.env["product.uom"]
        procurements_done = set()
        res = dict.fromkeys(self.ids, 0.0)
        for orderpoint_id, procurement_id, product_uom_id, procurement_qty, template_uom_id, move_qty in self._cr.fetchall():
            if procurement_id not in procurements_done:  # count procurement once, if multiple move in this orderpoint/procurement combo
                procurements_done.add(procurement_id)
                res[orderpoint_id] += UoM.browse(product_uom_id)._compute_quantity(procurement_qty, UoM.browse(template_uom_id), round=False)
            if move_qty:
                res[orderpoint_id] -= move_qty
        return res

    def _get_date_planned(self, product_qty, start_date):
        days = self.lead_days or 0.0
        if self.lead_type == 'supplier':
            # These days will be substracted when creating the PO
            days += self.product_id._select_seller(
                quantity=product_qty,
                date=fields.Date.to_string(start_date),
                uom_id=self.product_uom).delay or 0.0
        date_planned = start_date + relativedelta.relativedelta(days=days)
        return date_planned.strftime(DEFAULT_SERVER_DATE_FORMAT)

    @api.multi
    def _prepare_procurement_values(self, product_qty, date=False, group=False):
        return {
            'name': self.name,
            'date_planned': date or self._get_date_planned(product_qty, datetime.today()),
            'product_id': self.product_id.id,
            'product_qty': product_qty,
            'company_id': self.company_id.id,
            'product_uom': self.product_uom.id,
            'location_id': self.location_id.id,
            'origin': self.name,
            'warehouse_id': self.warehouse_id.id,
            'orderpoint_id': self.id,
            'group_id': group or self.group_id.id,
        }
