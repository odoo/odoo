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
from openerp.tools.translate import _

class stock_configure_wh(osv.osv_memory):
    _name = "stock.configure.wh"
    _description = "Configure New WH"

    _columns = {
        'code': fields.char('Warehouse Unique Identifier', size=5, required=True),
        'reception_steps': fields.selection([
            ('one_step', 'Receive goods directly in stock (1 step)'),
            ('two_steps', 'Unload in input location then go to stock (2 steps)'),
            ('three_steps', 'Unload in input location, go through a quality control before being admitted in stock (3 steps)')], 'Incoming Shipments', required=True),
        'delivery_steps': fields.selection([
            ('ship_only', 'Ship directly from stock (Ship only)'),
            ('pick_ship', 'Bring goods to output location before shipping (Pick + Ship)'),
            ('pick_pack_ship', 'Make packages into a dedicated location, then bring them to the output location for shipping (Pick + Pack + Ship)')], 'Outgoing Shippings', required=True),
        'packing': fields.boolean('Use Packing Operations', help='Whether we make packing in that warehouse while making internal transfers or not'),
    }

    _defaults = {
        'reception_steps': 'one_step',
        'delivery_steps': 'ship_only',
    }

    def onchange_delivery_steps(self, cr, uid, ids, delivery_steps, context=None):
        if delivery_steps == 'pick_pack_ship':
            return {'value': {'packing': True}}
        return {}

    def _format_rulename(self, cr, uid, obj, from_loc, dest_loc, context=None):
        return obj.name + ': ' + from_loc.name + ' -> ' + dest_loc.name

    def _format_routename(self, cr, uid, obj, name, context=None):
        return obj.name + ': ' + name

    def configure_wh(self, cr, uid, ids, context=None):
        """ To Import stock inventory according to products available in the selected locations.
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: the ID or list of IDs if we want more than one
        @param context: A standard dictionary
        @return:
        """
        if context is None:
            context = {}
        if ids and isinstance(ids, list):
            ids = ids[0]

        #TODO avoid running twice the config wizard for a given warehouse => don't create twice the same rule/route/location....
        data_obj = self.pool.get('ir.model.data')
        seq_obj = self.pool.get('ir.sequence')
        picking_type_obj = self.pool.get('stock.picking.type')
        location_obj = self.pool.get('stock.location')
        route_obj = self.pool.get('stock.location.route')
        pull_obj = self.pool.get('procurement.rule')
        push_obj = self.pool.get('stock.location.path')
        wh_obj = self.pool.get('stock.warehouse')
        obj = self.browse(cr, uid, ids, context=context)

        warehouse_id = context.get('active_id', context.get('active_ids') and context.get('active_ids')[0] or False)
        if not warehouse_id:
            raise osv.except_osv(_('Error!'), _('Can\'t find the warehouse to configure. The wizard cannot be used'))

        warehouse = wh_obj.browse(cr, uid, warehouse_id, context=context)
        wh_view_location_id = warehouse.lot_stock_id.location_id.id
        wh_stock_loc = warehouse.lot_stock_id
        wh_input_stock_loc = wh_output_stock_loc = wh_pack_stock_loc = wh_qc_stock_loc = wh_stock_loc
        if obj.reception_steps != 'one_step':
            wh_input_stock_loc_id = location_obj.create(cr, uid, {
                'name': _('Input'),
                'usage': 'internal',
                'location_id': wh_view_location_id
            }, context=context)
            wh_input_stock_loc = location_obj.browse(cr, uid, wh_input_stock_loc_id, context=context)
        if obj.reception_steps == 'three_steps':
            wh_qc_stock_loc_id = location_obj.create(cr, uid, {
                'name': _('Quality Control'),
                'usage': 'internal',
                'location_id': wh_view_location_id
            }, context=context)
            wh_qc_stock_loc = location_obj.browse(cr, uid, wh_qc_stock_loc_id, context=context)
        if obj.delivery_steps != 'ship_only':
            wh_output_stock_loc_id = location_obj.create(cr, uid, {
                'name': _('Output'),
                'usage': 'internal',
                'location_id': wh_view_location_id
            }, context=context)
            wh_output_stock_loc = location_obj.browse(cr, uid, wh_output_stock_loc_id, context=context)
        if obj.delivery_steps == 'pick_pack_ship':
            wh_pack_stock_loc_id = location_obj.create(cr, uid, {
                'name': _('Packing Zone'),
                'usage': 'internal',
                'location_id': wh_view_location_id
            }, context=context)
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
            raise osv.except_osv(_('Error!'), _('Can\'t find any customer or supplier location. The wizard cannot be used'))
        customer_loc = location_obj.browse(cr, uid, customer_loc, context=context)
        supplier_loc = location_obj.browse(cr, uid, supplier_loc, context=context)

        #create default route for warehouse
        default_route_id = route_obj.create(cr, uid, vals={
            'name': 'to be changed later',
            'warehouse_selectable': True,
            'product_selectable': False,
        }, context=context)

        #create warehouse
        wh_data = {
            'route_id': default_route_id,
            #TODO what about 'code' ....
        }
        wh_obj.write(cr, uid, warehouse_id, vals=wh_data, context=context)

        #create in, out, internal picking types for warehouse
        #First create new sequence
        in_seq_id = seq_obj.create(cr, uid, values={'name': warehouse.name + _(' Picking in'), 'prefix': obj.code + '\IN\\', 'padding': 5}, context=context)
        out_seq_id = seq_obj.create(cr, uid, values={'name': warehouse.name + _(' Picking out'), 'prefix': obj.code + '\OUT\\', 'padding': 5}, context=context)
        internal_seq_id = seq_obj.create(cr, uid, values={'name': warehouse.name + _(' Picking internal'), 'prefix': obj.code + '\INT\\', 'padding': 5}, context=context)
        #then create picking_types
        in_picking_type_id = picking_type_obj.create(cr, uid, vals={
            'name': _('Receptions'),
            'warehouse_id': warehouse_id,
            'code_id': 'incoming',
            'auto_force_assign': True,
            'sequence_id': in_seq_id,
            'default_location_src_id': supplier_loc.id,
            'default_location_dest_id': wh_input_stock_loc.id}, context=context)
        out_picking_type_id = picking_type_obj.create(cr, uid, vals={
            'name': _('Delivery Orders'),
            'warehouse_id': warehouse_id,
            'code_id': 'outgoing',
            'sequence_id': out_seq_id,
            'delivery': True,
            'default_location_src_id': wh_output_stock_loc.id,
            'default_location_dest_id': customer_loc.id}, context=context)
        internal_picking_type_id = picking_type_obj.create(cr, uid, vals={
            'name': _('Internal Transfers'),
            'warehouse_id': warehouse_id,
            'code_id': 'internal',
            'sequence_id': internal_seq_id,
            'default_location_src_id': wh_stock_loc.id,
            'default_location_dest_id': wh_stock_loc.id,
            'pack': obj.delivery_steps == 'pick_pack_ship' or obj.packing}, context=context)

        #defining the route references for further creation
        routes_dict = {
            'two_steps': (_('Reception in 2 steps'), [(wh_input_stock_loc, wh_stock_loc, internal_picking_type_id)]),
            'three_steps': (_('Reception in 3 steps'), [(wh_input_stock_loc, wh_qc_stock_loc, internal_picking_type_id), (wh_qc_stock_loc, wh_stock_loc, internal_picking_type_id)]),
            'crossdock': (_('Cross-Dock'), [(wh_input_stock_loc, wh_output_stock_loc, internal_picking_type_id), (wh_output_stock_loc, customer_loc, out_picking_type_id)]),
            'ship_only': (_('Ship Only'), [(wh_stock_loc, customer_loc, out_picking_type_id)]),
            'pick_ship': (_('Pick + Ship'), [(wh_stock_loc, wh_output_stock_loc, internal_picking_type_id), (wh_output_stock_loc, customer_loc, out_picking_type_id)]),
            'pick_pack_ship': (_('Pick + Pack + Ship'), [(wh_stock_loc, wh_pack_stock_loc, internal_picking_type_id), (wh_pack_stock_loc, wh_output_stock_loc, internal_picking_type_id), (wh_output_stock_loc, customer_loc, out_picking_type_id)]),
        }

        #create push rules for reception and assign them to 'All products' category
        if obj.reception_steps != 'one_step':
            try:
                all_products_categ = data_obj.get_object_reference(cr, uid, 'product', 'product_category_all')[1]
            except:
                all_products_categ = self.pool.get('product.category').search(cr, uid, [('parent_id', '=', False)], context=context)
                all_products_categ = all_products_categ and all_products_categ[0] or False
            if not all_products_categ:
                raise osv.except_osv(_('Error!'), _('Can\'t find the product category for the reception in several steps. The wizard cannot be used.'))

            route_name, values = routes_dict[obj.reception_steps]
            new_route_id = route_obj.create(cr, uid, vals={
                'name': self._format_routename(cr, uid, warehouse, route_name, context=context),
                'product_categ_selectable': True,
                'product_selectable': False,
            }, context=context)
            for from_loc, dest_loc, pick_type_id in values:
                push_data = {
                    'name': self._format_rulename(cr, uid, warehouse, from_loc, dest_loc, context=context),
                    'location_from_id': from_loc.id,
                    'location_dest_id': dest_loc.id,
                    'route_id': new_route_id,
                    'auto': 'manual',
                    'picking_type_id': pick_type_id,
                }
                push_obj.create(cr, uid, vals=push_data, context=context)

            self.pool.get('product.category').write(cr, uid, all_products_categ, {'route_ids': [(4, new_route_id)]}, context=context)

        #create pull rules for delivery, which include all routes in MTS on the warehouse and a specific route MTO to be set on the product
        route_name, values = routes_dict[obj.delivery_steps]
        route_obj.write(cr, uid, default_route_id, {'name': self._format_routename(cr, uid, warehouse, route_name, context=context)}, context=context)
        mto_route_id = route_obj.create(cr, uid, vals={
            'name': self._format_routename(cr, uid, warehouse, route_name, context=context) + _(' (MTO)'),
            'warehouse_selectable': False,
            'product_selectable': True,
        })
        first_rule = True
        for from_loc, dest_loc, pick_type_id in values:
            pull_obj.create(cr, uid, {
                'name': self._format_rulename(cr, uid, warehouse, from_loc, dest_loc, context=context),
                'location_src_id': from_loc.id,
                'location_id': dest_loc.id,
                'route_id': default_route_id,
                'action': 'move',
                'picking_type_id': pick_type_id,
                'procure_method': first_rule is True and 'make_to_stock' or 'make_to_order',
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

        return {'type': 'ir.actions.act_window_close'}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
