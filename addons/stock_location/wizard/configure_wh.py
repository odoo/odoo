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

class stock_configure_wh(osv.osv_memory):
    _name = "stock.configure.wh"
    _description = "Configure New WH"

    _columns = {
        'name': fields.char('Warehouse Name', required=True),
        'address_id': fields.many2one('res.partner', 'Warehouse Address'),
        'internal_stock_loc_id': fields.many2one('stock.location', 'Internal Stock Location', required=True),
        'input_stock_loc_id': fields.many2one('stock.location', 'Input Location', required=True),
        'output_stock_loc_id': fields.many2one('stock.location', 'Output Location', required=True),
        'crossdock': fields.boolean('Crossdock', help='Whether this warehouse uses generally crossdock operations or not'),
        'packing': fields.boolean('Packing', help='Whether we make packing in that warehouse while making outgoing shipments or not'),
        'packing_loc_id': fields.many2one('stock.location', 'Packing Zone Location')
    }

    def onchange_crossdock(self, cr, uid, ids, crossdock=False, context=None):
        if crossdock:
            return {'value': {'packing': False, 'packing_loc_id': False}}
        return True


    def onchange_packing(self, cr, uid, ids, packing=False, stock_loc=False, context=None):
        if packing:
            return {'value': {'packing_loc_id': stock_loc}}
        return True


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

        route_obj = self.pool.get('stock.location.route')
        pull_obj = self.pool.get('procurement.rule')
        inventory_obj = self.pool.get('stock.inventory')
        if ids and len(ids):
            ids = ids[0]
        obj = self.browse(cr, uid, ids, context=context)
        
        data_obj = self.pool.get('ir.model.data')

        wh_stock_loc = obj.internal_stock_loc_id.id
        wh_input_stock_loc = obj.input_stock_loc_id.id
        wh_output_stock_loc = obj.output_stock_loc_id.id

        customer_loc = data_obj.get_object_reference(cr, uid, 'stock', 'stock_location_customers')[1]
        supplier_loc = data_obj.get_object_reference(cr, uid, 'stock', 'stock_location_suppliers')[1]

        #create route
        new_route_id = False

        route_data = {
            'name': obj.name+': Ship', 
            'warehouse_selectable': True,
            'product_selectable': False, 
        }
        if obj.crossdock:
            route_data['name'] = obj.name+': Crossdock'
        elif wh_stock_loc != wh_output_stock_loc:
            if obj.packing:
                route_data['name'] = obj.name+': Pick + Pack + Ship'
            else:
                route_data['name'] = obj.name+': Pick + Ship'
        new_route_id = route_obj.create(cr, uid, vals=route_data, context=context)

        #create wh
        wh_data = {
            'name': obj.name,
            'address_id': obj.address_id and obj.address_id.id or False,
            'lot_stock_id': wh_stock_loc,
            'route_id': new_route_id,
        }
        wh_obj = self.pool.get('stock.warehouse')
        new_wh_id = wh_obj.create(cr, uid, vals=wh_data, context=context)

        #create in, out, internal picking types for wh
        #First create new sequence
        seq_obj = self.pool.get('ir.sequence')
        in_seq_id = seq_obj.create(cr, uid, values={'name': 'Picking in', 'prefix': 'IN', 'padding': 5}, context=context)
        out_seq_id = seq_obj.create(cr, uid, values={'name': 'Picking out', 'prefix': 'OUT', 'padding': 5}, context=context)
        internal_seq_id = seq_obj.create(cr, uid, values={'name': 'Picking internal', 'prefix': 'INT', 'padding': 5}, context=context)
        #then create picking_type
        picking_obj = self.pool.get('stock.picking.type')
        in_picking_id = picking_obj.create(cr, uid, vals={'name': 'Receptions', 'warehouse_id': new_wh_id, 'code_id': 'incoming', 'sequence_id': in_seq_id, 'default_location_src_id': supplier_loc, 'default_location_dest_id': wh_stock_loc}, context=context)
        out_picking_id = picking_obj.create(cr, uid, vals={'name': 'Delivery Orders', 'warehouse_id': new_wh_id, 'code_id': 'outgoing', 'sequence_id': out_seq_id, 'default_location_src_id': wh_stock_loc, 'default_location_dest_id': customer_loc}, context=context)
        internal_picking_id = picking_obj.create(cr, uid, vals={'name': 'Internal Transfers', 'warehouse_id': new_wh_id, 'code_id': 'internal', 'sequence_id': internal_seq_id, 'default_location_src_id': wh_stock_loc, 'default_location_dest_id': wh_stock_loc, 'pack': obj.packing}, context=context)

        #add pull rules to default route
        #ship pull rules
        pull_data = {
            'name': obj.name+': Stock -> Customer', 
            'location_src_id': wh_stock_loc, 
            'location_id': customer_loc, 
            'propagate': True, 
            'route_id': new_route_id, 
            'action': 'move', 
            'picking_type_id': internal_picking_id, 
            'procure_method': 'make_to_stock'
        }
        if obj.crossdock:
            cross_data = pull_data.copy()
            cross_data.update({
                'name': obj.name+': Output -> Customer',
                'location_src_id': wh_output_stock_loc,
                'picking_type_id': out_picking_id,
                'procure_method': 'make_to_order',
                })
            pull_obj.create(cr, uid, vals=cross_data, context=context)

            cross_data.update({
                'name': obj.name+': Supplier -> Output',
                'location_src_id': supplier_loc,
                'location_id': wh_output_stock_loc,
                'action': 'buy',
                'picking_type_id': in_picking_id,
                })
            pull_obj.create(cr, uid, vals=cross_data, context=context)
        #ship rules
        elif wh_stock_loc == wh_output_stock_loc:
            pull_obj.create(cr, uid, vals=pull_data, context=context)
        #pick-pack-ship rules
        elif obj.packing:
            #if packing zone is the same as output or stock, only create one pull rule, otherwise, create two
            if obj.packing_loc_id.id == wh_stock_loc:
                pull_data.update({
                    'name': obj.name + ' Stock -> Output',
                    'location_id': wh_output_stock_loc,
                    })
                pull_obj.create(cr, uid, vals=pull_data, context=context)
            else:

                pull_data.update({
                    'name': obj.name+' Stock -> Pack',
                    'location_id': obj.packing_loc_id.id,
                    })
                pull_obj.create(cr, uid, vals=pull_data, context=context)

                pull_data.update({
                    'name': obj.name+' Pack -> Output',
                    'location_src_id': obj.packing_loc_id.id,
                    'location_id': wh_output_stock_loc,
                    'picking_type_id': internal_picking_id,
                    'procure_method': 'make_to_order',
                    })
                pull_obj.create(cr, uid, vals=pull_data, context=context)

            pull_data.update({
                'name': obj.name+' Output -> Customer',
                'location_src_id': wh_output_stock_loc,
                'location_id': customer_loc,
                'picking_type_id': out_picking_id,
                'procure_method': 'make_to_order',
                })
            pull_obj.create(cr, uid, vals=pull_data, context=context)
        #pick-ship rules
        else:
            pull_data.update({
                'name': obj.name + ' Stock -> Output',
                'location_id': wh_output_stock_loc,
                })
            pull_obj.create(cr, uid, vals=pull_data, context=context)

            pull_data.update({
                'name': obj.name+' Output -> Customer',
                'location_src_id': wh_output_stock_loc,
                'location_id': customer_loc,
                'picking_type_id': out_picking_id,
                'procure_method': 'make_to_order',
                })
            pull_obj.create(cr, uid, vals=pull_data, context=context)

        return {'type': 'ir.actions.act_window_close'}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
