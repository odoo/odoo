# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import namedtuple
from datetime import datetime
from dateutil import relativedelta

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

import logging

_logger = logging.getLogger(__name__)


class Warehouse(models.Model):
    _name = "stock.warehouse"
    _description = "Warehouse"
    # namedtuple used in helper methods generating values for routes
    Routing = namedtuple('Routing', ['from_loc', 'dest_loc', 'picking_type', 'action'])

    name = fields.Char('Warehouse', index=True, required=True, default=lambda self: self.env['res.company']._company_default_get('stock.inventory').name)
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
        ('one_step', 'Receive goods directly (1 step)'),
        ('two_steps', 'Receive goods in input and then stock (2 steps)'),
        ('three_steps', 'Receive goods in input, then quality and then stock (3 steps)')],
        'Incoming Shipments', default='one_step', required=True,
        help="Default incoming route to follow")
    delivery_steps = fields.Selection([
        ('ship_only', 'Deliver goods directly (1 step)'),
        ('pick_ship', 'Send goods in output and then deliver (2 steps)'),
        ('pick_pack_ship', 'Pack goods, send goods in output and then deliver (3 steps)')],
        'Outgoing Shipments', default='ship_only', required=True,
        help="Default outgoing route to follow")
    wh_input_stock_loc_id = fields.Many2one('stock.location', 'Input Location')
    wh_qc_stock_loc_id = fields.Many2one('stock.location', 'Quality Control Location')
    wh_output_stock_loc_id = fields.Many2one('stock.location', 'Output Location')
    wh_pack_stock_loc_id = fields.Many2one('stock.location', 'Packing Location')
    mto_pull_id = fields.Many2one('stock.rule', 'MTO rule')
    pick_type_id = fields.Many2one('stock.picking.type', 'Pick Type')
    pack_type_id = fields.Many2one('stock.picking.type', 'Pack Type')
    out_type_id = fields.Many2one('stock.picking.type', 'Out Type')
    in_type_id = fields.Many2one('stock.picking.type', 'In Type')
    int_type_id = fields.Many2one('stock.picking.type', 'Internal Type')
    crossdock_route_id = fields.Many2one('stock.location.route', 'Crossdock Route', ondelete='restrict')
    reception_route_id = fields.Many2one('stock.location.route', 'Receipt Route', ondelete='restrict')
    delivery_route_id = fields.Many2one('stock.location.route', 'Delivery Route', ondelete='restrict')
    warehouse_count = fields.Integer(compute='_compute_warehouse_count')
    resupply_wh_ids = fields.Many2many(
        'stock.warehouse', 'stock_wh_resupply_table', 'supplied_wh_id', 'supplier_wh_id',
        'Resupply From', help="Routes will be created automatically to resupply this warehouse from the warehouses ticked")
    resupply_route_ids = fields.One2many(
        'stock.location.route', 'supplied_wh_id', 'Resupply Routes',
        help="Routes will be created for these resupply warehouses and you can select them on products and product categories")
    warehouse_count = fields.Integer(compute='_compute_warehouse_count')
    show_resupply = fields.Boolean(compute="_compute_show_resupply")
    _sql_constraints = [
        ('warehouse_name_uniq', 'unique(name, company_id)', 'The name of the warehouse must be unique per company!'),
        ('warehouse_code_uniq', 'unique(code, company_id)', 'The code of the warehouse must be unique per company!'),
    ]

    @api.depends('name')
    def _compute_warehouse_count(self):
        for warehouse in self:
            warehouse.warehouse_count = self.env['stock.warehouse'].search_count([('id', 'not in', warehouse.ids)])

    def _compute_show_resupply(self):
        for warehouse in self:
            warehouse.show_resupply = warehouse.user_has_groups("stock.group_stock_multi_warehouses") and warehouse.warehouse_count

    @api.model
    def create(self, vals):
        # create view location for warehouse then create all locations
        loc_vals = {'name': _(vals.get('code')), 'usage': 'view',
                    'location_id': self.env.ref('stock.stock_location_locations').id}
        if vals.get('company_id'):
            loc_vals['company_id'] = vals.get('company_id')
        vals['view_location_id'] = self.env['stock.location'].create(loc_vals).id
        sub_locations = self._get_locations_values(vals)

        for field_name, values in sub_locations.items():
            values['location_id'] = vals['view_location_id']
            if vals.get('company_id'):
                values['company_id'] = vals.get('company_id')
            vals[field_name] = self.env['stock.location'].with_context(active_test=False).create(values).id

        # actually create WH
        warehouse = super(Warehouse, self).create(vals)
        # create sequences and operation types
        new_vals = warehouse._create_or_update_sequences_and_picking_types()
        warehouse.write(new_vals)  # TDE FIXME: use super ?
        # create routes and push/stock rules
        route_vals = warehouse._create_or_update_route()
        warehouse.write(route_vals)

        # Update global route with specific warehouse rule.
        warehouse._create_or_update_global_routes_rules()

        # create route selectable on the product to resupply the warehouse from another one
        warehouse.create_resupply_routes(warehouse.resupply_wh_ids)

        # update partner data if partner assigned
        if vals.get('partner_id'):
            self._update_partner_data(vals['partner_id'], vals.get('company_id'))
        return warehouse

    def write(self, vals):
        Route = self.env['stock.location.route']
        warehouses = self.with_context(active_test=False)  # TDE FIXME: check this

        if vals.get('code') or vals.get('name'):
            warehouses._update_name_and_code(vals.get('name'), vals.get('code'))

        warehouses._create_missing_locations(vals)

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

        # If another partner assigned
        if vals.get('partner_id'):
            warehouses._update_partner_data(vals['partner_id'], vals.get('company_id'))

        res = super(Warehouse, self).write(vals)

        for warehouse in self:
            # check if we need to delete and recreate route
            depends = [depend for depends in [value['depends'] for value in warehouse._get_routes_values().values()] for depend in depends]
            if any(depend in vals for depend in depends):
                picking_type_vals = warehouse._create_or_update_sequences_and_picking_types()
                if picking_type_vals:
                    warehouse.write(picking_type_vals)
                route_vals = warehouse._create_or_update_route()
                if route_vals:
                    warehouse.write(route_vals)
            # Check if a global rule(mto, buy, ...) need to be modify.
            # The field that impact those rules are listed in the
            # _get_global_route_rules_values method under the key named
            # 'depends'.
            global_rules = warehouse._get_global_route_rules_values()
            depends = [depend for depends in [value['depends'] for value in global_rules.values()] for depend in depends]
            if any(rule in vals for rule in global_rules) or\
                    any(depend in vals for depend in depends):
                warehouse._create_or_update_global_routes_rules()

        if vals.get('resupply_wh_ids') and not vals.get('resupply_route_ids'):
            for warehouse in warehouses:
                to_add = new_resupply_whs - old_resupply_whs[warehouse.id]
                to_remove = old_resupply_whs[warehouse.id] - new_resupply_whs
                if to_add:
                    warehouse.create_resupply_routes(to_add)
                if to_remove:
                    Route.search([('supplied_wh_id', '=', warehouse.id), ('supplier_wh_id', 'in', to_remove.ids)]).write({'active': False})
                    # TDE FIXME: shouldn't we remove stock rules also ? because this could make them global (not sure)

        return res

    @api.model
    def _update_partner_data(self, partner_id, company_id):
        if not partner_id:
            return
        ResCompany = self.env['res.company']
        if company_id:
            transit_loc = ResCompany.browse(company_id).internal_transit_location_id.id
            self.env['res.partner'].browse(partner_id).with_context(force_company=company_id).write({'property_stock_customer': transit_loc, 'property_stock_supplier': transit_loc})
        else:
            transit_loc = ResCompany._company_default_get('stock.warehouse').internal_transit_location_id.id
            self.env['res.partner'].browse(partner_id).write({'property_stock_customer': transit_loc, 'property_stock_supplier': transit_loc})

    def _create_or_update_sequences_and_picking_types(self):
        """ Create or update existing picking types for a warehouse.
        Pikcing types are stored on the warehouse in a many2one. If the picking
        type exist this method will update it. The update values can be found in
        the method _get_picking_type_update_values. If the picking type does not
        exist it will be created with a new sequence associated to it.
        """
        self.ensure_one()
        IrSequenceSudo = self.env['ir.sequence'].sudo()
        PickingType = self.env['stock.picking.type']

        # choose the next available color for the operation types of this warehouse
        all_used_colors = [res['color'] for res in PickingType.search_read([('warehouse_id', '!=', False), ('color', '!=', False)], ['color'], order='color')]
        available_colors = [zef for zef in range(0, 12) if zef not in all_used_colors]
        color = available_colors[0] if available_colors else 0

        warehouse_data = {}
        sequence_data = self._get_sequence_values()

        # suit for each warehouse: reception, internal, pick, pack, ship
        max_sequence = self.env['stock.picking.type'].search_read([('sequence', '!=', False)], ['sequence'], limit=1, order='sequence desc')
        max_sequence = max_sequence and max_sequence[0]['sequence'] or 0

        data = self._get_picking_type_update_values()
        create_data, max_sequence = self._get_picking_type_create_values(max_sequence)

        for picking_type, values in data.items():
            if self[picking_type]:
                self[picking_type].update(values)
            else:
                data[picking_type].update(create_data[picking_type])
                sequence = IrSequenceSudo.create(sequence_data[picking_type])
                values.update(warehouse_id=self.id, color=color, sequence_id=sequence.id)
                warehouse_data[picking_type] = PickingType.create(values).id

        if 'out_type_id' in warehouse_data:
            PickingType.browse(warehouse_data['out_type_id']).write({'return_picking_type_id': warehouse_data.get('in_type_id', False)})
        if 'in_type_id' in warehouse_data:
            PickingType.browse(warehouse_data['in_type_id']).write({'return_picking_type_id': warehouse_data.get('out_type_id', False)})
        return warehouse_data

    def _create_or_update_global_routes_rules(self):
        """ Some rules are not specific to a warehouse(e.g MTO, Buy, ...)
        however they contain rule(s) for a specific warehouse. This method will
        update the rules contained in global routes in order to make them match
        with the wanted reception, delivery,... steps.
        """
        for rule_field, rule_details in self._get_global_route_rules_values().items():
            values = rule_details['update_values']
            if self[rule_field]:
                self[rule_field].write(values)
            else:
                values.update(rule_details['create_values'])
                values.update({'warehouse_id': self.id})
                self[rule_field] = self.env['stock.rule'].create(values)
        return True

    def _find_global_route(self, xml_id, route_name):
        """ return a route record set from an xml_id or its name. """
        route = self.env.ref(xml_id, raise_if_not_found=False)
        if not route:
            route = self.env['stock.location.route'].search([('name', 'like', route_name)], limit=1)
        if not route:
            raise UserError(_('Can\'t find any generic route %s.') % (route_name))
        return route

    def _get_global_route_rules_values(self):
        """ Method used by _create_or_update_global_routes_rules. It's
        purpose is to return a dict with this format.
        key: The rule contained in a global route that have to be create/update
        entry a dict with the following values:
            -depends: Field that impact the rule. When a field in depends is
            write on the warehouse the rule set as key have to be update.
            -create_values: values used in order to create the rule if it does
            not exist.
            -update_values: values used to update the route when a field in
            depends is modify on the warehouse.
        """
        # We use 0 since routing are order from stock to cust. If the routing
        # order is modify, the mto rule will be wrong.
        rule = self.get_rules_dict()[self.id][self.delivery_steps]
        rule = [r for r in rule if r.from_loc == self.lot_stock_id][0]
        location_id = rule.from_loc
        location_dest_id = rule.dest_loc
        picking_type_id = rule.picking_type
        return {
            'mto_pull_id': {
                'depends': ['delivery_steps'],
                'create_values': {
                    'active': True,
                    'procure_method': 'make_to_order',
                    'company_id': self.company_id.id,
                    'action': 'pull',
                    'auto': 'manual',
                    'propagate': True,
                    'route_id': self._find_global_route('stock.route_warehouse0_mto', _('Make To Order')).id
                },
                'update_values': {
                    'name': self._format_rulename(location_id, location_dest_id, 'MTO'),
                    'location_id': location_dest_id.id,
                    'location_src_id': location_id.id,
                    'picking_type_id': picking_type_id.id,
                }
            }
        }

    def _create_or_update_route(self):
        """ Create or update the warehouse's routes.
        _get_routes_values method return a dict with:
            - route field name (e.g: crossdock_route_id).
            - field that trigger an update on the route (key 'depends').
            - routing_key used in order to find rules contained in the route.
            - create values.
            - update values when a field in depends is modified.
            - rules default values.
        This method do an iteration on each route returned and update/create
        them. In order to update the rules contained in the route it will
        use the get_rules_dict that return a dict:
            - a receptions/delivery,... step value as key (e.g  'pick_ship')
            - a list of routing object that represents the rules needed to
            fullfil the pupose of the route.
        The routing_key from _get_routes_values is match with the get_rules_dict
        key in order to create/update the rules in the route
        (_find_existing_rule_or_create method is responsible for this part).
        """
        # Create routes and active/create their related rules.
        routes = []
        rules_dict = self.get_rules_dict()
        for route_field, route_data in self._get_routes_values().items():
            # If the route exists update it
            if self[route_field]:
                route = self[route_field]
                route.write(route_data['route_update_values'])
                route.rule_ids.write({'active': False})
            # Create the route
            else:
                route_data['route_create_values'].update(route_data['route_update_values'])
                route = self.env['stock.location.route'].create(route_data['route_create_values'])
                self[route_field] = route
            # Get rules needed for the route
            routing_key = route_data.get('routing_key')
            rules = rules_dict[self.id][routing_key]
            if 'rules_values' in route_data:
                route_data['rules_values'].update({'route_id': route.id})
            else:
                route_data['rules_values'] = {'route_id': route.id}
            rules_list = self._get_rule_values(
                rules, values=route_data['rules_values'])
            # Create/Active rules
            self._find_existing_rule_or_create(rules_list)
            if route_data['route_create_values'].get('warehouse_selectable', False) or route_data['route_update_values'].get('warehouse_selectable', False):
                routes.append(self[route_field])
        return {
            'route_ids': [(4, route.id) for route in routes],
        }

    def _get_routes_values(self):
        """ Return information in order to update warehouse routes.
        - The key is a route field sotred as a Many2one on the warehouse
        - This key contains a dict with route values:
            - routing_key: a key used in order to match rules from
            get_rules_dict function. It would be usefull in order to generate
            the route's rules.
            - route_create_values: When the Many2one does not exist the route
            is created based on values contained in this dict.
            - route_update_values: When a field contained in 'depends' key is
            modified and the Many2one exist on the warehouse, the route will be
            update with the values contained in this dict.
            - rules_values: values added to the routing in order to create the
            route's rules.
        """
        return {
            'reception_route_id': {
                'routing_key': self.reception_steps,
                'depends': ['reception_steps'],
                'route_update_values': {
                    'name': self._format_routename(route_type=self.reception_steps)
                },
                'route_create_values': {
                    'product_categ_selectable': True,
                    'warehouse_selectable': True,
                    'product_selectable': False,
                    'company_id': self.company_id.id,
                    'sequence': 9,
                },
                'rules_values': {
                    'active': True,
                    'procure_method': 'make_to_order'
                }
            },
            'delivery_route_id': {
                'routing_key': self.delivery_steps,
                'depends': ['delivery_steps'],
                'route_update_values': {
                    'name': self._format_routename(route_type=self.delivery_steps)
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
            },
            'crossdock_route_id': {
                'routing_key': 'crossdock',
                'depends': ['delivery_steps', 'reception_steps'],
                'route_update_values': {
                    'name': self._format_routename(route_type='crossdock'),
                    'active': self.reception_steps != 'one_step' and self.delivery_steps != 'ship_only'
                },
                'route_create_values': {
                    'product_selectable': True,
                    'product_categ_selectable': True,
                    'active': self.delivery_steps != 'ship_only' and self.reception_steps != 'one_step',
                    'company_id': self.company_id.id,
                    'sequence': 20,
                },
                'rules_values': {
                    'active': True,
                    'procure_method': 'make_to_order'
                }
            }
        }

    def _find_existing_rule_or_create(self, rules_list):
        """ This method will find existing rules or create new one. """
        for rule_vals in rules_list:
            existing_rule = self.env['stock.rule'].search([
                ('picking_type_id', '=', rule_vals['picking_type_id']),
                ('location_src_id', '=', rule_vals['location_src_id']),
                ('location_id', '=', rule_vals['location_id']),
                ('route_id', '=', rule_vals['route_id']),
                ('action', '=', rule_vals['action']),
                ('active', '=', False),
            ])
            if not existing_rule:
                self.env['stock.rule'].create(rule_vals)
            else:
                existing_rule.write({'active': True})

    def _get_locations_values(self, vals):
        """ Update the warehouse locations. """
        def_values = self.default_get(['reception_steps', 'delivery_steps'])
        reception_steps = vals.get('reception_steps', def_values['reception_steps'])
        delivery_steps = vals.get('delivery_steps', def_values['delivery_steps'])
        code = vals.get('code') or self.code
        code = code.replace(' ', '').upper()
        sub_locations = {
            'lot_stock_id': {
                'name': _('Stock'),
                'active': True,
                'usage': 'internal',
                'barcode': code + '-STOCK'
            },
            'wh_input_stock_loc_id': {
                'name': _('Input'),
                'active': reception_steps != 'one_step',
                'usage': 'internal',
                'barcode': code + '-INPUT'
            },
            'wh_qc_stock_loc_id': {
                'name': _('Quality Control'),
                'active': reception_steps == 'three_steps',
                'usage': 'internal',
                'barcode': code + '-QUALITY'
            },
            'wh_output_stock_loc_id': {
                'name': _('Output'),
                'active': delivery_steps != 'ship_only',
                'usage': 'internal',
                'barcode': code + '-OUTPUT'
            },
            'wh_pack_stock_loc_id': {
                'name': _('Packing Zone'),
                'active': delivery_steps == 'pick_pack_ship',
                'usage': 'internal',
                'barcode': code + '-PACKING'
            },
        }
        return sub_locations

    def _create_missing_locations(self, vals):
        """ It could happen that the user delete a mandatory location or a
        module with new locations was installed after some warehouses creation.
        In this case, this function will create missing locations in order to
        avoid mistakes during picking types and rules creation.
        """
        sub_locations = self._get_locations_values(vals)
        for warehouse in self:
            missing_location = {}
            for location, location_values in sub_locations.items():
                if not warehouse[location] and location not in vals:
                    location_values['location_id'] = vals.get('view_location_id', warehouse.view_location_id.id)
                    location_values['company_id'] = vals.get('company_id', warehouse.company_id.id)
                    missing_location[location] = self.env['stock.location'].create(location_values).id
            if missing_location:
                warehouse.write(missing_location)

    def create_resupply_routes(self, supplier_warehouses):
        Route = self.env['stock.location.route']
        Rule = self.env['stock.rule']

        input_location, output_location = self._get_input_output_locations(self.reception_steps, self.delivery_steps)
        internal_transit_location, external_transit_location = self._get_transit_locations()

        for supplier_wh in supplier_warehouses:
            transit_location = internal_transit_location if supplier_wh.company_id == self.company_id else external_transit_location
            if not transit_location:
                continue
            output_location = supplier_wh.lot_stock_id if supplier_wh.delivery_steps == 'ship_only' else supplier_wh.wh_output_stock_loc_id
            # Create extra MTO rule (only for 'ship only' because in the other cases MTO rules already exists)
            if supplier_wh.delivery_steps == 'ship_only':
                routing = [self.Routing(output_location, transit_location, supplier_wh.out_type_id, 'pull')]
                mto_vals = supplier_wh._get_global_route_rules_values().get('mto_pull_id')
                values = mto_vals['create_values']
                mto_rule_val = supplier_wh._get_rule_values(routing, values, name_suffix='MTO')
                Rule.create(mto_rule_val[0])

            inter_wh_route = Route.create(self._get_inter_warehouse_route_values(supplier_wh))

            pull_rules_list = supplier_wh._get_supply_pull_rules_values(
                [self.Routing(output_location, transit_location, supplier_wh.out_type_id, 'pull')],
                values={'route_id': inter_wh_route.id})
            pull_rules_list += self._get_supply_pull_rules_values(
                [self.Routing(transit_location, input_location, self.in_type_id, 'pull')],
                values={'route_id': inter_wh_route.id, 'propagate_warehouse_id': supplier_wh.id})
            for pull_rule_vals in pull_rules_list:
                Rule.create(pull_rule_vals)

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
        names = {'one_step': _('Receive in 1 step (stock)'), 'two_steps': _('Receive in 2 steps (input + stock)'),
                 'three_steps': _('Receive in 3 steps (input + quality + stock)'), 'crossdock': _('Cross-Dock'),
                 'ship_only': _('Deliver in 1 step (ship)'), 'pick_ship': _('Deliver in 2 steps (pick + ship)'),
                 'pick_pack_ship': _('Deliver in 3 steps (pick + pack + ship)')}
        return names[route_type]

    def get_rules_dict(self):
        """ Define the rules source/destination locations, picking_type and
        action needed for each warehouse route configuration.
        """
        customer_loc, supplier_loc = self._get_partner_locations()
        return {
            warehouse.id: {
                'one_step': [],
                'two_steps': [self.Routing(warehouse.wh_input_stock_loc_id, warehouse.lot_stock_id, warehouse.int_type_id, 'pull_push')],
                'three_steps': [
                    self.Routing(warehouse.wh_input_stock_loc_id, warehouse.wh_qc_stock_loc_id, warehouse.int_type_id, 'pull_push'),
                    self.Routing(warehouse.wh_qc_stock_loc_id, warehouse.lot_stock_id, warehouse.int_type_id, 'pull_push')],
                'crossdock': [
                    self.Routing(warehouse.wh_input_stock_loc_id, warehouse.wh_output_stock_loc_id, warehouse.int_type_id, 'pull'),
                    self.Routing(warehouse.wh_output_stock_loc_id, customer_loc, warehouse.out_type_id, 'pull')],
                'ship_only': [self.Routing(warehouse.lot_stock_id, customer_loc, warehouse.out_type_id, 'pull')],
                'pick_ship': [
                    self.Routing(warehouse.lot_stock_id, warehouse.wh_output_stock_loc_id, warehouse.pick_type_id, 'pull'),
                    self.Routing(warehouse.wh_output_stock_loc_id, customer_loc, warehouse.out_type_id, 'pull')],
                'pick_pack_ship': [
                    self.Routing(warehouse.lot_stock_id, warehouse.wh_pack_stock_loc_id, warehouse.pick_type_id, 'pull'),
                    self.Routing(warehouse.wh_pack_stock_loc_id, warehouse.wh_output_stock_loc_id, warehouse.pack_type_id, 'pull'),
                    self.Routing(warehouse.wh_output_stock_loc_id, customer_loc, warehouse.out_type_id, 'pull')],
                'company_id': warehouse.company_id.id,
            } for warehouse in self
        }

    def _get_inter_warehouse_route_values(self, supplier_warehouse):
        return {
            'name': _('%s: Supply Product from %s') % (self.name, supplier_warehouse.name),
            'warehouse_selectable': True,
            'product_selectable': True,
            'product_categ_selectable': True,
            'supplied_wh_id': self.id,
            'supplier_wh_id': supplier_warehouse.id,
            'company_id': self.company_id.id,
        }

    # Pull / Push tools
    # ------------------------------------------------------------

    def _get_rule_values(self, route_values, values=None, name_suffix=''):
        first_rule = True
        rules_list = []
        for routing in route_values:
            route_rule_values = {
                'name': self._format_rulename(routing.from_loc, routing.dest_loc, name_suffix),
                'location_src_id': routing.from_loc.id,
                'location_id': routing.dest_loc.id,
                'action': routing.action,
                'auto': 'manual',
                'picking_type_id': routing.picking_type.id,
                'procure_method': first_rule and 'make_to_stock' or 'make_to_order',
                'warehouse_id': self.id,
                'company_id': self.company_id.id,
                'propagate': routing.picking_type != self.pick_type_id,
            }
            route_rule_values.update(values or {})
            rules_list.append(route_rule_values)
            first_rule = False
        return rules_list

    def _get_supply_pull_rules_values(self, route_values, values=None):
        pull_values = {}
        pull_values.update(values)
        pull_values.update({'active': True})
        rules_list = self._get_rule_values(route_values, values=pull_values)
        for pull_rules in rules_list:
            pull_rules['procure_method'] = self.lot_stock_id.id != pull_rules['location_src_id'] and 'make_to_order' or 'make_to_stock'  # first part of the resuply route is MTS
        return rules_list

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
        Rule = self.env["stock.rule"]
        routes = self.env['stock.location.route'].search([('supplier_wh_id', '=', self.id)])
        rules = Rule.search(['&', '&', ('route_id', 'in', routes.ids), ('action', '!=', 'push'), ('location_id.usage', '=', 'transit')])
        rules.write({
            'location_src_id': new_location.id,
            'procure_method': change_to_multiple and "make_to_order" or "make_to_stock"})
        if not change_to_multiple:
            # If single delivery we should create the necessary MTO rules for the resupply
            routings = [self.Routing(self.lot_stock_id, location, self.out_type_id, 'pull') for location in rules.mapped('location_id')]
            mto_rule_vals = self._get_rule_values(routings)
            for mto_rule_val in mto_rule_vals:
                Rule.create(mto_rule_val)
        else:
            # We need to delete all the MTO stock rules, otherwise they risk to be used in the system
            Rule.search([
                '&', ('route_id', '=', self._find_global_route('stock.route_warehouse0_mto', _('Make To Order')).id),
                ('location_id.usage', '=', 'transit'),
                ('action', '!=', 'push'),
                ('location_src_id', '=', self.lot_stock_id.id)]).write({'active': False})

    def _check_reception_resupply(self, new_location):
        """ Check routes being delivered by the warehouses (resupply routes) and
        change their rule coming from the transit location """
        routes = self.env['stock.location.route'].search([('supplied_wh_id', 'in', self.ids)])
        self.env['stock.rule'].search([
            '&',
                ('route_id', 'in', routes.ids),
                '&',
                    ('action', '!=', 'push'),
                    ('location_src_id.usage', '=', 'transit')
        ]).write({'location_id': new_location.id})

    def _update_name_and_code(self, new_name=False, new_code=False):
        if new_code:
            self.mapped('lot_stock_id').mapped('location_id').write({'name': new_code})
        if new_name:
            # TDE FIXME: replacing the route name ? not better to re-generate the route naming ?
            for warehouse in self:
                routes = warehouse.route_ids
                for route in routes:
                    route.write({'name': route.name.replace(warehouse.name, new_name, 1)})
                    for pull in route.rule_ids:
                        pull.write({'name': pull.name.replace(warehouse.name, new_name, 1)})
                if warehouse.mto_pull_id:
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
        rules = self.env['stock.rule'].search_count([
            '&',
            ('route_id', 'not in', [x.id for x in self.route_ids]),
            '|', ('location_src_id', '=', location.id),
            ('location_id', '=', location.id)])
        if rules:
            return True
        return False

    # Misc
    # ------------------------------------------------------------

    def _get_picking_type_update_values(self):
        """ Return values in order to update the existing picking type when the
        warehouse's delivery_steps or reception_steps are modify.
        """
        input_loc, output_loc = self._get_input_output_locations(self.reception_steps, self.delivery_steps)
        return {
            'in_type_id': {'default_location_dest_id': input_loc.id},
            'out_type_id': {'default_location_src_id': output_loc.id},
            'pick_type_id': {
                'active': self.delivery_steps != 'ship_only',
                'default_location_dest_id': output_loc.id if self.delivery_steps == 'pick_ship' else self.wh_pack_stock_loc_id.id},
            'pack_type_id': {'active': self.delivery_steps == 'pick_pack_ship'},
            'int_type_id': {},
        }

    def _get_picking_type_create_values(self, max_sequence):
        """ When a warehouse is created this method return the values needed in
        order to create the new picking types for this warehouse. Every picking
        type are created at the same time than the warehouse howver they are
        activated or archived depending the delivery_steps or reception_steps.
        """
        input_loc, output_loc = self._get_input_output_locations(self.reception_steps, self.delivery_steps)
        return {
            'in_type_id': {
                'name': _('Receipts'),
                'code': 'incoming',
                'use_create_lots': True,
                'use_existing_lots': False,
                'default_location_src_id': False,
                'sequence': max_sequence + 1,
                'barcode': self.code.replace(" ", "").upper() + "-RECEIPTS",
            }, 'out_type_id': {
                'name': _('Delivery Orders'),
                'code': 'outgoing',
                'use_create_lots': False,
                'use_existing_lots': True,
                'default_location_dest_id': False,
                'sequence': max_sequence + 5,
                'barcode': self.code.replace(" ", "").upper() + "-DELIVERY",
            }, 'pack_type_id': {
                'name': _('Pack'),
                'code': 'internal',
                'use_create_lots': False,
                'use_existing_lots': True,
                'default_location_src_id': self.wh_pack_stock_loc_id.id,
                'default_location_dest_id': output_loc.id,
                'sequence': max_sequence + 4,
                'barcode': self.code.replace(" ", "").upper() + "-PACK",
            }, 'pick_type_id': {
                'name': _('Pick'),
                'code': 'internal',
                'use_create_lots': False,
                'use_existing_lots': True,
                'default_location_src_id': self.lot_stock_id.id,
                'sequence': max_sequence + 3,
                'barcode': self.code.replace(" ", "").upper() + "-PICK",
            }, 'int_type_id': {
                'name': _('Internal Transfers'),
                'code': 'internal',
                'use_create_lots': False,
                'use_existing_lots': True,
                'default_location_src_id': self.lot_stock_id.id,
                'default_location_dest_id': self.lot_stock_id.id,
                'active': self.reception_steps != 'one_step' or self.delivery_steps != 'ship_only' or self.user_has_groups('stock.group_stock_multi_locations'),
                'sequence': max_sequence + 2,
                'barcode': self.code.replace(" ", "").upper() + "-INTERNAL",
            },
        }, max_sequence + 6

    def _get_sequence_values(self):
        """ Each picking type is created with a sequence. This method returns
        the sequence values associated to each picking type.
        """
        return {
            'in_type_id': {
                'name': self.name + ' ' + _('Sequence in'),
                'prefix': self.code + '/IN/', 'padding': 5,
                'company_id': self.company_id.id,
            },
            'out_type_id': {
                'name': self.name + ' ' + _('Sequence out'),
                'prefix': self.code + '/OUT/', 'padding': 5,
                'company_id': self.company_id.id,
            },
            'pack_type_id': {
                'name': self.name + ' ' + _('Sequence packing'),
                'prefix': self.code + '/PACK/', 'padding': 5,
                'company_id': self.company_id.id,
            },
            'pick_type_id': {
                'name': self.name + ' ' + _('Sequence picking'),
                'prefix': self.code + '/PICK/', 'padding': 5,
                'company_id': self.company_id.id,
            },
            'int_type_id': {
                'name': self.name + ' ' + _('Sequence internal'),
                'prefix': self.code + '/INT/', 'padding': 5,
                'company_id': self.company_id.id,
            },
        }

    def _format_rulename(self, from_loc, dest_loc, suffix):
        rulename = '%s: %s' % (self.code, from_loc.name)
        if dest_loc:
            rulename += ' → %s' % (dest_loc.name)
        if suffix:
            rulename += ' (' + suffix + ')'
        return rulename

    def _format_routename(self, name=None, route_type=None):
        if route_type:
            name = self._get_route_name(route_type)
        return '%s: %s' % (self.name, name)

    @api.returns('self')
    def _get_all_routes(self):
        # TDE FIXME: check overrides
        routes = self.mapped('route_ids') | self.mapped('mto_pull_id').mapped('route_id')
        routes |= self.env["stock.location.route"].search([('supplied_wh_id', 'in', self.ids)])
        return routes
    get_all_routes_for_wh = _get_all_routes

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
        'uom.uom', 'Product Unit of Measure', related='product_id.uom_id',
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
    group_id = fields.Many2one(
        'procurement.group', 'Procurement Group', copy=False,
        help="Moves created through this orderpoint will be put in this procurement group. If none is given, the moves generated by stock rules will be grouped into one big picking.")
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

    def _quantity_in_progress(self):
        """Return Quantities that are not yet in virtual stock but should be deduced from orderpoint rule
        (example: purchases created from orderpoints)"""
        return dict(self.mapped(lambda x: (x.id, 0.0)))

    @api.constrains('product_id')
    def _check_product_uom(self):
        ''' Check if the UoM has the same category as the product standard UoM '''
        if any(orderpoint.product_id.uom_id.category_id != orderpoint.product_uom.category_id for orderpoint in self):
            raise ValidationError(_('You have to select a product unit of measure that is in the same category than the default unit of measure of the product'))

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

    def _get_date_planned(self, product_qty, start_date):
        days = self.lead_days or 0.0
        if self.lead_type == 'supplier':
            # These days will be substracted when creating the PO
            days += self.product_id._select_seller(
                quantity=product_qty,
                date=fields.Date.context_today(self,start_date),
                uom_id=self.product_uom).delay or 0.0
        date_planned = start_date + relativedelta.relativedelta(days=days)
        return date_planned.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

    def _prepare_procurement_values(self, product_qty, date=False, group=False):
        """ Prepare specific key for moves or other components that will be created from a stock rule
        comming from an orderpoint. This method could be override in order to add other custom key that could
        be used in move/po creation.
        """
        return {
            'date_planned': date or self._get_date_planned(product_qty, datetime.today()),
            'warehouse_id': self.warehouse_id,
            'orderpoint_id': self,
            'company_id': self.company_id,
            'group_id': group or self.group_id,
        }
