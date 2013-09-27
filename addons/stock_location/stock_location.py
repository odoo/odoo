# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import fields, osv
from datetime import *
from dateutil.relativedelta import relativedelta
from openerp.tools.translate import _

class stock_location_route(osv.osv):
    _inherit = 'stock.location.route'
    _description = "Inventory Routes"

    _columns = {
        'push_ids': fields.one2many('stock.location.path', 'route_id', 'Push Rules'),
        'product_selectable': fields.boolean('Selectable on Product'),
        'product_categ_selectable': fields.boolean('Selectable on Product Category'),
        'warehouse_selectable': fields.boolean('Selectable on Warehouse'),
        'active': fields.boolean('Active', help="If the active field is set to False, it will allow you to hide the route without removing it.")
    }
    _defaults = {
        'product_selectable': True,
        'active': True,
    }

class stock_warehouse(osv.osv):
    _inherit = 'stock.warehouse'
    _columns = {
        'route_ids': fields.many2many('stock.location.route', 'stock_route_warehouse', 'warehouse_id', 'route_id', 'Routes', domain="[('warehouse_selectable', '=', True)]", help='Defaults routes through the warehouse'),
        'reception_steps': fields.selection([
            ('one_step', 'Receive goods directly in stock (1 step)'),
            ('two_steps', 'Unload in input location then go to stock (2 steps)'),
            ('three_steps', 'Unload in input location, go through a quality control before being admitted in stock (3 steps)')], 'Incoming Shipments', required=True),
        'delivery_steps': fields.selection([
            ('ship_only', 'Ship directly from stock (Ship only)'),
            ('pick_ship', 'Bring goods to output location before shipping (Pick + Ship)'),
            ('pick_pack_ship', 'Make packages into a dedicated location, then bring them to the output location for shipping (Pick + Pack + Ship)')], 'Outgoing Shippings', required=True),
        
        'wh_input_stock_loc_id': fields.many2one('stock.location', 'Input Location'),
        'wh_qc_stock_loc_id': fields.many2one('stock.location', 'Quality Control Location'),
        'wh_output_stock_loc_id': fields.many2one('stock.location', 'Output Location'),
        'wh_pack_stock_loc_id': fields.many2one('stock.location', 'Packing Location'),
        'ship_route_mto': fields.many2one('stock.location.route', 'ship MTO route'),
        'pick_ship_route_mto': fields.many2one('stock.location.route', 'pick-ship MTO route'),
        'pick_pack_ship_route_mto': fields.many2one('stock.location.route', 'pick-pack-ship MTO route'),
        
    }
    _defaults = {
        'reception_steps': 'one_step',
        'delivery_steps': 'ship_only',
    }

    def switch_location(self, cr, uid, ids, warehouse, new_reception_step=False, new_delivery_step=False, context=None):
        location_obj = self.pool.get('stock.location')
        wh_view_location_id = warehouse.lot_stock_id.location_id.id
        wh_stock_loc = warehouse.lot_stock_id
        wh_input_stock_loc = wh_output_stock_loc = wh_pack_stock_loc = wh_qc_stock_loc = wh_stock_loc

        new_reception_step = new_reception_step or warehouse.reception_steps
        new_delivery_step = new_delivery_step or warehouse.delivery_steps
        if warehouse.reception_steps != new_reception_step:
            location_obj.write(cr, uid, [warehouse.wh_input_stock_loc_id.id, warehouse.wh_qc_stock_loc_id.id], {'active': False}, context=context)
            if new_reception_step != 'one_step':
                location_obj.write(cr, uid, warehouse.wh_input_stock_loc_id.id, {'active': True}, context=context) 
            if new_reception_step == 'three_steps':
                location_obj.write(cr, uid, warehouse.wh_qc_stock_loc_id.id, {'active': True}, context=context)
                
        if warehouse.delivery_steps != new_delivery_step:
            location_obj.write(cr, uid, [warehouse.wh_output_stock_loc_id.id, warehouse.wh_pack_stock_loc_id.id], {'active': False}, context=context)
            if new_delivery_step != 'ship_only':
                location_obj.write(cr, uid, warehouse.wh_output_stock_loc_id.id, {'active': True}, context=context) 
            if new_delivery_step == 'pick_pack_ship':
                location_obj.write(cr, uid, warehouse.wh_pack_stock_loc_id.id, {'active': True}, context=context)  
                
        return True

    def create_route(self, cr, uid, ids, warehouse, context=None):
        default_route_ids = []
        data_obj = self.pool.get('ir.model.data')
        route_obj = self.pool.get('stock.location.route')
        pull_obj = self.pool.get('procurement.rule')
        push_obj = self.pool.get('stock.location.path')
        keys = ('two_steps', 'three_steps')
        routes_dict = self.get_routes_dict(cr, uid, ids, warehouse, warehouse.reception_steps, warehouse.delivery_steps, write=False, context=context)
        for reception in keys:
            active = False
            route_name, values = routes_dict[reception]
            if reception == warehouse.reception_steps:
                active = True
            new_route_id = route_obj.create(cr, uid, vals={
                'name': self._format_routename(cr, uid, warehouse, route_name, context=context),
                'product_categ_selectable': True,
                'product_selectable': False,
                'active': active
            }, context=context)
            default_route_ids.append((4, new_route_id))
            first_rule = True
            for from_loc, dest_loc, pick_type_id in values:
                push_data = {
                    'name': self._format_rulename(cr, uid, warehouse, from_loc, dest_loc, context=context),
                    'location_from_id': from_loc.id,
                    'location_dest_id': dest_loc.id,
                    'route_id': new_route_id,
                    'auto': 'manual',
                    'picking_type_id': pick_type_id,
                    'active': active,
                }
                push_obj.create(cr, uid, vals=push_data, context=context)
                pull_obj.create(cr, uid, {
                    'name': self._format_rulename(cr, uid, warehouse, from_loc, dest_loc, context=context),
                    'location_src_id': from_loc.id,
                    'location_id': dest_loc.id,
                    'route_id': new_route_id,
                    'action': 'move',
                    'picking_type_id': pick_type_id,
                    'procure_method': first_rule is True and 'make_to_stock' or 'make_to_order',
                    'active': active,
                }, context=context)
                first_rule = False

        
        keys = {'ship_only': 'ship_route_mto', 'pick_ship': 'pick_ship_route_mto', 'pick_pack_ship': 'pick_pack_ship_route_mto'}
        for delivery, field in keys.items():
            active = False
            #create pull rules for delivery, which include all routes in MTS on the warehouse and a specific route MTO to be set on the product
            route_name, values = routes_dict[delivery]
            if delivery == warehouse.delivery_steps:
                active = True
            route_id = route_obj.create(cr, uid, vals={
                'name': self._format_routename(cr, uid, warehouse, route_name, context=context),
                'warehouse_selectable': True,
                'product_selectable': False,
                'active': active,
            }, context=context)
            default_route_ids.append((4, route_id))
                
            mto_route_id = route_obj.create(cr, uid, vals={
                'name': self._format_routename(cr, uid, warehouse, route_name, context=context) + _(' (MTO)'),
                'warehouse_selectable': False,
                'product_selectable': True,
                'active': active,
            })
            self.write(cr, uid, warehouse.id, {field: mto_route_id}, context=context)
            first_rule = True
            for from_loc, dest_loc, pick_type_id in values:
                pull_obj.create(cr, uid, {
                    'name': self._format_rulename(cr, uid, warehouse, from_loc, dest_loc, context=context),
                    'location_src_id': from_loc.id,
                    'location_id': dest_loc.id,
                    'route_id': route_id,
                    'action': 'move',
                    'picking_type_id': pick_type_id,
                    'procure_method': first_rule is True and 'make_to_stock' or 'make_to_order',
                    'active': active,
                }, context=context)
                if first_rule:
                    pull_obj.create(cr, uid, {
                        'name': self._format_rulename(cr, uid, warehouse, from_loc, dest_loc, context=context),
                        'location_src_id': from_loc.id,
                        'location_id': dest_loc.id,
                        'route_id': mto_route_id,
                        'action': 'move',
                        'picking_type_id': pick_type_id,
                        'procure_method': 'make_to_order',
                        'sequence': 10,
                        'active': active,
                    }, context=context)
                first_rule = False

        #create a route for cross dock operations, that can be set on products and product categories
        route_name, values = routes_dict['crossdock']
        crossdock_route_id = route_obj.create(cr, uid, vals={
            'name': self._format_routename(cr, uid, warehouse, route_name, context=context),
            'warehouse_selectable': False,
            'product_selectable': True,
            'product_categ_selectable': True,
        })
        default_route_ids.append((4, crossdock_route_id))
        first_rule = True
        for from_loc, dest_loc, pick_type_id in values:
            pull_obj.create(cr, uid, {
                'name': self._format_rulename(cr, uid, warehouse, from_loc, dest_loc, context=context),
                'location_src_id': from_loc.id,
                'location_id': dest_loc.id,
                'route_id': crossdock_route_id,
                'action': 'move',
                'picking_type_id': pick_type_id,
                'procure_method': first_rule is True and 'make_to_stock' or 'make_to_order',
                'sequence': 10,
            }, context=context)
            first_rule = False

        #set defaut delivery route on warehouse according to option choosen
        self.write(cr, uid, warehouse.id, {'route_ids': default_route_ids}, context=context)

        return default_route_ids

    def change_route(self, cr, uid, ids, warehouse, new_reception_step=False, new_delivery_step=False, context=None):
        pull_obj = self.pool.get('procurement.rule')
        new_reception_step = new_reception_step or warehouse.reception_steps
        new_delivery_step = new_delivery_step or warehouse.delivery_steps
        reception_name = False
        routes_dict = self.get_routes_dict(cr, uid, ids, warehouse, new_reception_step, new_delivery_step, write=True, context=context)
        delivery_name, values = routes_dict[new_delivery_step]
        delivery_name = self._format_routename(cr, uid, warehouse, delivery_name, context=context)
        crossdock_name, values = routes_dict['crossdock']
        crossdock_name = self._format_routename(cr, uid, warehouse, crossdock_name, context=context)

        if new_reception_step != 'one_step':
            reception_name, values = routes_dict[new_reception_step]
            reception_name = self._format_routename(cr, uid, warehouse, reception_name, context=context)
        
        set_active_route_ids = []
        set_inactive_route_ids = []
        for route in warehouse.route_ids:
            #put active route that are associated to reception and delivery method choosen if it's not already the case
            if route.name == reception_name or route.name == delivery_name:
                if not route.active:
                    set_active_route_ids.append(route.id)
            #put previous active route that are no longer needed to active=False
            elif route.active and route.name != crossdock_name:
                set_inactive_route_ids.append(route.id)
            #change pull rules input/output destination on crossdock route
            elif route.name == crossdock_name:
                route_name, values = routes_dict['crossdock']
                first_rule = True
                i=0
                if len(route.pull_ids) == len(values):
                    for from_loc, dest_loc, pick_type_id in values:
                        pull_obj.write(cr, uid, route.pull_ids[i].id, vals={
                            'name': self._format_rulename(cr, uid, warehouse, from_loc, dest_loc, context=context),
                            'location_src_id': from_loc.id,
                            'location_id': dest_loc.id,
                            'route_id': route.id,
                            'action': 'move',
                            'picking_type_id': pick_type_id,
                            'procure_method': first_rule is True and 'make_to_stock' or 'make_to_order',
                            'sequence': 10,
                        }, context=context)
                        first_rule = False
                        i+=1
                continue
        #deactivate previous mto route
        if warehouse.ship_route_mto.active:
            set_inactive_route_ids.append(warehouse.ship_route_mto.id)
        if warehouse.pick_ship_route_mto.active:
            set_inactive_route_ids.append(warehouse.pick_ship_route_mto.id)
        if warehouse.pick_pack_ship_route_mto.active:
            set_inactive_route_ids.append(warehouse.pick_pack_ship_route_mto.id)
        #activate new mto route
        if new_delivery_step == 'ship_only':
            set_active_route_ids.append(warehouse.ship_route_mto.id)
        elif new_delivery_step == 'pick_ship':
            set_active_route_ids.append(warehouse.pick_ship_route_mto.id)
        elif new_delivery_step == 'pick_pack_ship':
            set_active_route_ids.append(warehouse.pick_pack_ship_route_mto.id)
        self.set_route_active_status(cr, uid, ids, set_inactive_route_ids, False, context=context)
        self.set_route_active_status(cr, uid, ids, set_active_route_ids, True, context=context)
        return True

    def set_route_active_status(self, cr, uid, ids, route_ids, status=True, context=None):
        route_obj = self.pool.get('stock.location.route')
        pull_obj = self.pool.get('procurement.rule')
        push_obj = self.pool.get('stock.location.path')
        if not route_ids:
            return True
        route_obj.write(cr, uid, route_ids, {'active': status}, context=context)
        pull_rules_ids = []
        push_rules_ids = []
        for route in route_obj.browse(cr, uid, route_ids, context=context):
            for pull_rule in route.pull_ids:
                pull_rules_ids.append(pull_rule.id)
            for push_rule in route.push_ids:
                push_rules_ids.append(push_rule.id)
        if pull_rules_ids:
            pull_obj.write(cr, uid, pull_rules_ids, {'active': status}, context=context)
        if push_rules_ids:
            push_obj.write(cr, uid, push_rules_ids, {'active': status}, context=context)
        return True

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        if vals is None:
            vals = {}
        data_obj = self.pool.get('ir.model.data')
        seq_obj = self.pool.get('ir.sequence')
        picking_type_obj = self.pool.get('stock.picking.type')
        location_obj = self.pool.get('stock.location')
        route_obj = self.pool.get('stock.location.route')

        #create view location for warehouse
        wh_loc_id = location_obj.create(cr, uid, {
                'name': _(vals.get('name')),
                'usage': 'view',
                'location_id': data_obj.get_object_reference(cr, uid, 'stock', 'stock_location_locations')[1]
            }, context=context)
        wh_stock_loc_id = location_obj.create(cr, uid, {
                'name': _('Stock'),
                'usage': 'internal',
                'location_id': wh_loc_id
            }, context=context)
        vals['lot_stock_id'] = wh_stock_loc_id
        context_with_inactive = context.copy()
        context_with_inactive['active_test']=False
        #create all location
        reception_steps = vals.get('reception_steps', False)
        delivery_steps = vals.get('delivery_steps', False)
        wh_input_stock_loc_id = location_obj.create(cr, uid, {
                'name': _('Input'),
                'usage': 'internal',
                'location_id': wh_loc_id,
                'active': reception_steps != 'one_step' and True or False,
            }, context=context_with_inactive)
        vals['wh_input_stock_loc_id'] = wh_input_stock_loc_id
        wh_qc_stock_loc_id = location_obj.create(cr, uid, {
                'name': _('Quality Control'),
                'usage': 'internal',
                'location_id': wh_loc_id,
                'active': reception_steps == 'three_steps' and True or False,
            }, context=context_with_inactive)
        vals['wh_qc_stock_loc_id'] = wh_qc_stock_loc_id
        wh_output_stock_loc_id = location_obj.create(cr, uid, {
                'name': _('Output'),
                'usage': 'internal',
                'location_id': wh_loc_id,
                'active': delivery_steps != 'ship_only' and True or False,
            }, context=context_with_inactive)
        vals['wh_output_stock_loc_id'] = wh_output_stock_loc_id
        wh_pack_stock_loc_id = location_obj.create(cr, uid, {
                'name': _('Packing Zone'),
                'usage': 'internal',
                'location_id': wh_loc_id,
                'active': delivery_steps == 'pick_pack_ship' and True or False,
            }, context=context_with_inactive)
        vals['wh_pack_stock_loc_id'] = wh_pack_stock_loc_id 

        #create WH
        new_id = super(stock_warehouse, self).create(cr, uid, vals=vals, context=context)

        #create sequences and picking type
        warehouse = self.browse(cr, uid, new_id, context=context)
        wh_stock_loc = warehouse.lot_stock_id
        wh_input_stock_loc = location_obj.browse(cr, uid, wh_input_stock_loc_id, context=context)
        wh_qc_stock_loc = location_obj.browse(cr, uid, wh_qc_stock_loc_id, context=context)
        wh_output_stock_loc = location_obj.browse(cr, uid, wh_output_stock_loc_id, context=context)
        wh_pack_stock_loc = location_obj.browse(cr, uid, wh_pack_stock_loc_id, context=context)
        
        #fetch customer and supplier locations, for references
        try:
            customer_loc = data_obj.get_object_reference(cr, uid, 'stock', 'stock_location_customers')[1]
            supplier_loc = data_obj.get_object_reference(cr, uid, 'stock', 'stock_location_suppliers')[1]
        except:
            customer_loc = location_obj.search(cr, uid, [('usage', '=', 'customer')], context=context)
            customer_loc = customer_loc and customer_loc[0] or False
            supplier_loc = location_obj.search(cr, uid, [('usage', '=', 'supplier')], context=context)
            supplier_loc = supplier_loc and supplier_loc[0] or False
        if not (customer_loc and supplier_loc):
            raise osv.except_osv(_('Error!'), _('Can\'t find any customer or supplier location.'))
        customer_loc = location_obj.browse(cr, uid, customer_loc, context=context)
        supplier_loc = location_obj.browse(cr, uid, supplier_loc, context=context)

        #create in, out, internal picking types for warehouse
        #First create new sequence
        in_seq_id = seq_obj.create(cr, uid, values={'name': warehouse.name + _(' Picking in'), 'prefix': warehouse.code + '\IN\\', 'padding': 5}, context=context)
        out_seq_id = seq_obj.create(cr, uid, values={'name': warehouse.name + _(' Picking out'), 'prefix': warehouse.code + '\OUT\\', 'padding': 5}, context=context)
        internal_seq_id = seq_obj.create(cr, uid, values={'name': warehouse.name + _(' Picking internal'), 'prefix': warehouse.code + '\INT\\', 'padding': 5}, context=context)
        #then create picking_types
        input_loc = wh_input_stock_loc
        if warehouse.reception_steps == 'one_step':
            input_loc = wh_stock_loc
        output_loc = wh_output_stock_loc
        if warehouse.delivery_steps == 'ship_only':
            output_loc = wh_stock_loc
        in_picking_type_id = picking_type_obj.create(cr, uid, vals={
            'name': _('Receptions'),
            'warehouse_id': new_id,
            'code_id': 'incoming',
            'auto_force_assign': True,
            'sequence_id': in_seq_id,
            'default_location_src_id': supplier_loc.id,
            'default_location_dest_id': input_loc.id}, context=context)
        out_picking_type_id = picking_type_obj.create(cr, uid, vals={
            'name': _('Delivery Orders'),
            'warehouse_id': new_id,
            'code_id': 'outgoing',
            'sequence_id': out_seq_id,
            'delivery': True,
            'default_location_src_id': output_loc.id,
            'default_location_dest_id': customer_loc.id}, context=context)
        internal_picking_type_id = picking_type_obj.create(cr, uid, vals={
            'name': _('Internal Transfers'),
            'warehouse_id': new_id,
            'code_id': 'internal',
            'sequence_id': internal_seq_id,
            'default_location_src_id': wh_stock_loc.id,
            'default_location_dest_id': wh_stock_loc.id,
            'pack': True,}, context=context)

        #create routes and push/pull rules
        default_route_id = self.create_route(cr, uid, new_id, warehouse, context=context)

        return new_id

    def _format_rulename(self, cr, uid, obj, from_loc, dest_loc, context=None):
        return obj.name + ': ' + from_loc.name + ' -> ' + dest_loc.name

    def _format_routename(self, cr, uid, obj, name, context=None):
        return obj.name + ': ' + name

    def get_routes_dict(self, cr, uid, ids, warehouse, reception_steps=False, delivery_steps=False, write=False, context=None):
        picking_type_obj = self.pool.get('stock.picking.type')
        data_obj = self.pool.get('ir.model.data')
        location_obj = self.pool.get('stock.location')
        #fetch various location
        wh_input_stock_loc = warehouse.wh_input_stock_loc_id
        wh_qc_stock_loc = warehouse.wh_qc_stock_loc_id
        wh_output_stock_loc = warehouse.wh_output_stock_loc_id
        wh_pack_stock_loc = warehouse.wh_pack_stock_loc_id
        wh_stock_loc = warehouse.lot_stock_id
        #fetch customer and supplier locations, for references
        try:
            customer_loc = data_obj.get_object_reference(cr, uid, 'stock', 'stock_location_customers')[1]
            supplier_loc = data_obj.get_object_reference(cr, uid, 'stock', 'stock_location_suppliers')[1]
        except:
            customer_loc = location_obj.search(cr, uid, [('usage', '=', 'customer')], context=context)
            customer_loc = customer_loc and customer_loc[0] or False
            supplier_loc = location_obj.search(cr, uid, [('usage', '=', 'supplier')], context=context)
            supplier_loc = supplier_loc and supplier_loc[0] or False
        if not (customer_loc and supplier_loc):
            raise osv.except_osv(_('Error!'), _('Can\'t find any customer or supplier location.'))
        customer_loc = location_obj.browse(cr, uid, customer_loc, context=context)
        supplier_loc = location_obj.browse(cr, uid, supplier_loc, context=context)
        #update route on picking type
        input_loc = wh_input_stock_loc
        if reception_steps == 'one_step':
            input_loc = wh_stock_loc
        output_loc = wh_output_stock_loc
        if delivery_steps == 'ship_only':
            output_loc = wh_stock_loc
        in_picking_type_id = picking_type_obj.search(cr, uid, [('warehouse_id', '=', warehouse.id), ('code_id', '=', 'incoming')], context=context)[0]
        out_picking_type_id = picking_type_obj.search(cr, uid, [('warehouse_id', '=', warehouse.id), ('code_id', '=', 'outgoing')], context=context)[0]
        internal_picking_type_id = picking_type_obj.search(cr, uid, [('warehouse_id', '=', warehouse.id), ('code_id', '=', 'internal')], context=context)[0]
        #in case we need to update picking location
        if write:
            picking_type_obj.write(cr, uid, in_picking_type_id, {'default_location_dest_id': input_loc.id}, context=context)
            picking_type_obj.write(cr, uid, out_picking_type_id, {'default_location_src_id': output_loc.id}, context=context)
            
        return {
            'two_steps': (_('Reception in 2 steps'), [(wh_input_stock_loc, wh_stock_loc, internal_picking_type_id)]),
            'three_steps': (_('Reception in 3 steps'), [(wh_input_stock_loc, wh_qc_stock_loc, internal_picking_type_id), (wh_qc_stock_loc, wh_stock_loc, internal_picking_type_id)]),
            'crossdock': (_('Cross-Dock'), [(input_loc, output_loc, internal_picking_type_id), (output_loc, customer_loc, out_picking_type_id)]),
            'ship_only': (_('Ship Only'), [(wh_stock_loc, customer_loc, out_picking_type_id)]),
            'pick_ship': (_('Pick + Ship'), [(wh_stock_loc, wh_output_stock_loc, internal_picking_type_id), (wh_output_stock_loc, customer_loc, out_picking_type_id)]),
            'pick_pack_ship': (_('Pick + Pack + Ship'), [(wh_stock_loc, wh_pack_stock_loc, internal_picking_type_id), (wh_pack_stock_loc, wh_output_stock_loc, internal_picking_type_id), (wh_output_stock_loc, customer_loc, out_picking_type_id)]),
        }

    def write(self, cr, uid, ids, vals, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        seq_obj = self.pool.get('ir.sequence')
        context_with_inactive = context.copy()
        context_with_inactive['active_test']=False
        for warehouse in self.browse(cr, uid, ids, context=context_with_inactive):
            name = warehouse.name
            rename = False
            if vals.get('code') or vals.get('name'):
                #use previous name to find informations
                #rename sequence
                if vals.get('name'):
                    rename = True
                in_seq = seq_obj.search(cr, uid, [('name', '=', name + _(' Picking in'))], context=context)
                out_seq = seq_obj.search(cr, uid, [('name', '=', name + _(' Picking out'))], context=context)
                internal_seq  = seq_obj.search(cr, uid, [('name', '=', name + _(' Picking internal'))], context=context)
                seq_obj.write(cr, uid, in_seq, {'name': vals.get('name', name), 'prefix': vals.get('code', warehouse.code) + '\IN\\'}, context=context)
                seq_obj.write(cr, uid, out_seq, {'name': vals.get('name', name), 'prefix': vals.get('code', warehouse.code) + '\OUT\\'}, context=context)
                seq_obj.write(cr, uid, internal_seq, {'name': vals.get('name', name), 'prefix': vals.get('code', warehouse.code) + '\INT\\'}, context=context)
            #first of all, check if we need to delete and recreate route
            if vals.get('reception_steps') or vals.get('delivery_steps'):
                #activate and deactivate location according to reception and delivery option
                self.switch_location(cr, uid, warehouse.id, warehouse, vals.get('reception_steps', False), vals.get('delivery_steps', False), context=context)
                # switch between route
                self.change_route(cr, uid, ids, warehouse, vals.get('reception_steps', False), vals.get('delivery_steps', False), context=context_with_inactive)

            #TODO rename routes, location, pull/push rules name if warehouse name has changed
            if rename:
                #rename location
                location_id = warehouse.lot_stock_id.location_id.id

        return super(stock_warehouse, self).write(cr, uid, ids, vals=vals, context=context)

    def unlink(self, cr, uid, ids, context=None):
        #TODO try to delete location and route and if not possible, put them in inactive
        return super(stock_warehouse, self).unlink(cr, uid, ids, context=context)

class stock_location_path(osv.osv):
    _name = "stock.location.path"
    _description = "Pushed Flows"
    _order = "name"
    _columns = {
        'name': fields.char('Operation Name', size=64, required=True),
        'company_id': fields.many2one('res.company', 'Company'),
        'route_id': fields.many2one('stock.location.route', 'Route'),
        'location_from_id': fields.many2one('stock.location', 'Source Location', ondelete='cascade', select=1, required=True),
        'location_dest_id': fields.many2one('stock.location', 'Destination Location', ondelete='cascade', select=1, required=True),
        'delay': fields.integer('Delay (days)', help="Number of days to do this transition"),
        'invoice_state': fields.selection([
            ("invoiced", "Invoiced"),
            ("2binvoiced", "To Be Invoiced"),
            ("none", "Not Applicable")], "Invoice Status",
            required=True,), 
        'picking_type_id': fields.many2one('stock.picking.type', 'Type of the new Operation', required=True, help="This is the picking type associated with the different pickings"), 
        'auto': fields.selection(
            [('auto','Automatic Move'), ('manual','Manual Operation'),('transparent','Automatic No Step Added')],
            'Automatic Move',
            required=True, select=1,
            help="This is used to define paths the product has to follow within the location tree.\n" \
                "The 'Automatic Move' value will create a stock move after the current one that will be "\
                "validated automatically. With 'Manual Operation', the stock move has to be validated "\
                "by a worker. With 'Automatic No Step Added', the location is replaced in the original move."
            ),
        'propagate': fields.boolean('Propagate cancel and split', help='If checked, when the previous move is cancelled or split, the move generated by this move will too'),
        'active': fields.boolean('Active', help="If the active field is set to False, it will allow you to hide the rule without removing it."),
    }
    _defaults = {
        'auto': 'auto',
        'delay': 1,
        'invoice_state': 'none',
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'procurement.order', context=c),
        'propagate': True,
        'active': True,
    }
    def _apply(self, cr, uid, rule, move, context=None):
        move_obj = self.pool.get('stock.move')
        newdate = (datetime.strptime(move.date, '%Y-%m-%d %H:%M:%S') + relativedelta(days=rule.delay or 0)).strftime('%Y-%m-%d')
        if rule.auto=='transparent':
            move_obj.write(cr, uid, [move.id], {
                'date': newdate,
                'location_dest_id': rule.location_dest_id.id
            })
            if rule.location_dest_id.id<>move.location_dest_id.id:
                move_obj._push_apply(self, cr, uid, move.id, context)
            return move.id
        else:
            move_id = move_obj.copy(cr, uid, move.id, {
                'location_id': move.location_dest_id.id,
                'location_dest_id': rule.location_dest_id.id,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'company_id': rule.company_id and rule.company_id.id or False,
                'date_expected': newdate,
                'picking_id': False,
                'picking_type_id': rule.picking_type_id and rule.picking_type_id.id or False,
                'rule_id': rule.id,
                'propagate': rule.propagate, 
            })
            move_obj.write(cr, uid, [move.id], {
                'move_dest_id': move_id,
            })
            move_obj.action_confirm(cr, uid, [move_id], context=None)
            return move_id


class procurement_rule(osv.osv):
    _inherit = 'procurement.rule'

    _columns = {
        'delay': fields.integer('Number of Days'),
        'partner_address_id': fields.many2one('res.partner', 'Partner Address'),
        'propagate': fields.boolean('Propagate cancel and split', help='If checked, when the previous move of the move (which was generated by a next procurement) is cancelled or split, the move generated by this move will too'),
    }
    _defaults = {
        'propagate': True, 
        'delay': 0, 
    }


class procurement_order(osv.osv):
    _inherit = 'procurement.order'
    _columns = {
        'route_ids': fields.many2many('stock.location.route', 'stock_location_route_procurement', 'procurement_id', 'route_id', 'Followed Route', help="Preferred route to be followed by the procurement order"),
        }
    
    def _run_move_create(self, cr, uid, procurement, context=None):
        d = super(procurement_order, self)._run_move_create(cr, uid, procurement, context=context)
        d.update({
            'route_ids': [(4,x.id) for x in procurement.route_ids],  
        })
        if procurement.rule_id:
            newdate = (datetime.strptime(procurement.date_planned, '%Y-%m-%d %H:%M:%S') - relativedelta(days=procurement.rule_id.delay or 0)).strftime('%Y-%m-%d %H:%M:%S')
            d.update({
                'date': newdate,
                'propagate': procurement.rule_id.propagate, 
            })
        return d

    def _find_suitable_rule(self, cr, uid, procurement, context=None):
        rule_id = super(procurement_order, self)._find_suitable_rule(cr, uid, procurement, context=context)
        if not rule_id:
            rule_id = self._search_suitable_rule(cr, uid, procurement, [('location_id', '=', procurement.location_id.id)], context=context) #action=move
            rule_id = rule_id and rule_id[0] or False
        return rule_id

    def _search_suitable_rule(self, cr, uid, procurement, domain, context=None):
        '''we try to first find a rule among the ones defined on the procurement order group and if none is found, we try on the routes defined for the product, and finally we fallback on the default behavior'''
        categ_obj = self.pool.get("product.category")
        categ_id = procurement.product_id.categ_id.id
        route_ids1 = [x.id for x in procurement.product_id.route_ids + procurement.product_id.categ_id.total_route_ids]
        route_ids2 = [x.id for x in procurement.route_ids]
        res = self.pool.get('procurement.rule').search(cr, uid, domain + [('route_id', 'in', route_ids1)], order = 'route_sequence, sequence', context=context)
        if not res:
            res = self.pool.get('procurement.rule').search(cr, uid, domain + [('route_id', 'in', route_ids2)], order = 'route_sequence, sequence', context=context)
            if not res:
                res = self.pool.get('procurement.rule').search(cr, uid, domain + [('route_id', '=', False)], order='sequence', context=context)
        return res


class product_putaway_strategy(osv.osv):
    _name = 'product.putaway'
    _description = 'Put Away Strategy'
    _columns = {
        'product_categ_id':fields.many2one('product.category', 'Product Category', required=True),
        'location_id': fields.many2one('stock.location','Parent Location', help="Parent Destination Location from which a child bin location needs to be chosen", required=True), #domain=[('type', '=', 'parent')], 
        'method': fields.selection([('fixed', 'Fixed Location')], "Method", required = True),
        'location_spec_id': fields.many2one('stock.location','Specific Location', help="When the location is specific, it will be put over there"), #domain=[('type', '=', 'parent')],
    }

# TODO: move this on stock module

class product_removal_strategy(osv.osv):
    _name = 'product.removal'
    _description = 'Removal Strategy'
    _order = 'sequence'
    _columns = {
        'product_categ_id': fields.many2one('product.category', 'Category', required=True), 
        'sequence': fields.integer('Sequence'),
        'method': fields.selection([('fifo', 'FIFO'), ('lifo', 'LIFO')], "Method", required = True),
        'location_id': fields.many2one('stock.location', 'Locations', required=True),
    }

class product_product(osv.osv):
    _inherit = 'product.product'
    _columns = {
        'route_ids': fields.many2many('stock.location.route', 'stock_route_product', 'product_id', 'route_id', 'Routes', domain="[('product_selectable', '=', True)]"), #Adds domain
    }

class product_category(osv.osv):
    _inherit = 'product.category'
    
    
    def calculate_total_routes(self, cr, uid, ids, name, args, context=None):
        res = {}
        route_obj = self.pool.get("stock.location.route")
        for categ in self.browse(cr, uid, ids, context=context):
            categ2 = categ
            routes = [x.id for x in categ.route_ids]
            while categ2.parent_id:
                categ2 = categ2.parent_id
                routes += [x.id for x in categ2.route_ids]
            res[categ.id] = routes
        return res
        
    _columns = {
        'route_ids': fields.many2many('stock.location.route', 'stock_location_route_categ', 'categ_id', 'route_id', 'Routes', domain="[('product_categ_selectable', '=', True)]"),
        'removal_strategy_ids': fields.one2many('product.removal', 'product_categ_id', 'Removal Strategies'),
        'putaway_strategy_ids': fields.one2many('product.putaway', 'product_categ_id', 'Put Away Strategies'),
        'total_route_ids': fields.function(calculate_total_routes, relation='stock.location.route', type='many2many', string='Total routes', readonly=True),
    }

    

class stock_move_putaway(osv.osv):
    _name = 'stock.move.putaway'
    _description = 'Proposed Destination'
    _columns = {
        'move_id': fields.many2one('stock.move', required=True),
        'location_id': fields.many2one('stock.location', 'Location', required=True),
        'lot_id': fields.many2one('stock.production.lot', 'Lot'),
        'quantity': fields.float('Quantity', required=True),
    }


class stock_quant(osv.osv):
    _inherit = "stock.quant"
    def check_preferred_location(self, cr, uid, move, context=None):
        # moveputaway_obj = self.pool.get('stock.move.putaway')
        if move.putaway_ids and move.putaway_ids[0]:
            #Take only first suggestion for the moment
            return move.putaway_ids[0].location_id
        else:
            return super(stock_quant, self).check_preferred_location(cr, uid, move, context=context)


class stock_move(osv.osv):
    _inherit = 'stock.move'
    _columns = {
        'putaway_ids': fields.one2many('stock.move.putaway', 'move_id', 'Put Away Suggestions'), 
        'route_ids': fields.many2many('stock.location.route', 'stock_location_route_move', 'move_id', 'route_id', 'Destination route', help="Preferred route to be followed by the procurement order"),
    }

    def _push_apply(self, cr, uid, moves, context):
        categ_obj = self.pool.get("product.category")
        push_obj = self.pool.get("stock.location.path")
        for move in moves:
            if not move.move_dest_id:
                categ_id = move.product_id.categ_id.id
                routes = [x.id for x in move.product_id.route_ids + move.product_id.categ_id.total_route_ids]
                rules = push_obj.search(cr, uid, [('route_id', 'in', routes), ('location_from_id', '=', move.location_dest_id.id)], context=context)
                if rules: 
                    rule = push_obj.browse(cr, uid, rules[0], context=context)
                    push_obj._apply(cr, uid, rule, move, context=context)
        return True

    # Create the stock.move.putaway records
    def _putaway_apply(self,cr, uid, ids, context=None):
        moveputaway_obj = self.pool.get('stock.move.putaway')
        for move in self.browse(cr, uid, ids, context=context):
            putaway = self.pool.get('stock.location').get_putaway_strategy(cr, uid, move.location_dest_id, move.product_id, context=context)
            if putaway:
                # Should call different methods here in later versions
                # TODO: take care of lots
                if putaway.method == 'fixed' and putaway.location_spec_id:
                    moveputaway_obj.create(cr, uid, {'move_id': move.id,
                                                     'location_id': putaway.location_spec_id.id,
                                                     'quantity': move.product_uom_qty}, context=context)
        return True

    def action_assign(self, cr, uid, ids, context=None):
        result = super(stock_move, self).action_assign(cr, uid, ids, context=context)
        self._putaway_apply(cr, uid, ids, context=context)
        return result

    def action_confirm(self, cr, uid, ids, context=None):
        result = super(stock_move, self).action_confirm(cr, uid, ids, context)
        moves = self.browse(cr, uid, ids, context=context)
        self._push_apply(cr, uid, moves, context=context)
        return result

    def _prepare_procurement_from_move(self, cr, uid, move, context=None):
        """
            Next to creating the procurement order, it will propagate the routes
        """
        vals = super(stock_move, self)._prepare_procurement_from_move(cr, uid, move, context=context)
        vals['route_ids'] = [(4, x.id) for x in move.route_ids]
        return vals


class stock_location(osv.osv):
    _inherit = 'stock.location'
    _columns = {
        'removal_strategy_ids': fields.one2many('product.removal', 'location_id', 'Removal Strategies'),
        'putaway_strategy_ids': fields.one2many('product.putaway', 'location_id', 'Put Away Strategies'),
    }

    def get_putaway_strategy(self, cr, uid, location, product, context=None):
        pa = self.pool.get('product.putaway')
        categ = product.categ_id
        categs = [categ.id, False]
        while categ.parent_id:
            categ = categ.parent_id
            categs.append(categ.id)

        result = pa.search(cr,uid, [
            ('location_id', '=', location.id),
            ('product_categ_id', 'in', categs)
        ], context=context)
        if result:
            return pa.browse(cr, uid, result[0], context=context)
        #return super(stock_location, self).get_putaway_strategy(cr, uid, location, product, context=context)

    def get_removal_strategy(self, cr, uid, location, product, context=None):
        pr = self.pool.get('product.removal')
        categ = product.categ_id
        categs = [categ.id, False]
        while categ.parent_id:
            categ = categ.parent_id
            categs.append(categ.id)

        result = pr.search(cr,uid, [
            ('location_id', '=', location.id),
            ('product_categ_id', 'in', categs)
        ], context=context)
        if result:
            return pr.browse(cr, uid, result[0], context=context).method
        return super(stock_location, self).get_removal_strategy(cr, uid, location, product, context=context)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
