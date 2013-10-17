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
import openerp.addons.decimal_precision as dp

class product_product(osv.osv):
    _inherit = "product.product"
        
    def _stock_move_count(self, cr, uid, ids, field_name, arg, context=None):
        res = dict([(id, {'reception_count': 0, 'delivery_count': 0}) for id in ids])
        move_pool=self.pool.get('stock.move')
        moves = move_pool.read_group(cr, uid, [
            ('product_id', 'in', ids),
            ('location_id.usage', '!=', 'internal'),
            ('location_dest_id.usage', '=', 'internal'),
            ('state','in',('confirmed','assigned','pending'))
        ], ['product_id'], ['product_id'])
        for move in moves:
            product_id = move['product_id'][0]
            res[product_id]['reception_count'] = move['product_id_count']
        moves = move_pool.read_group(cr, uid, [
            ('product_id', 'in', ids),
            ('location_id.usage', '=', 'internal'),
            ('location_dest_id.usage', '!=', 'internal'),
            ('state','in',('confirmed','assigned','pending'))
        ], ['product_id'], ['product_id'])
        for move in moves:
            product_id = move['product_id'][0]
            res[product_id]['delivery_count'] = move['product_id_count']
        return res

    def view_header_get(self, cr, user, view_id, view_type, context=None):
        if context is None:
            context = {}
        res = super(product_product, self).view_header_get(cr, user, view_id, view_type, context)
        if res: return res
        if (context.get('active_id', False)) and (context.get('active_model') == 'stock.location'):
            return _('Products: ')+self.pool.get('stock.location').browse(cr, user, context['active_id'], context).name
        return res

    #
    # TODO: Needs to be rechecked 
    #
    def _get_domain_locations(self, cr, uid, ids, context=None):
        '''
        Parses the context and returns a list of location_ids based on it.
        It will return all stock locations when no parameters are given
        Possible parameters are shop, warehouse, location, force_company, compute_child
        '''
        context = context or {}

        location_obj = self.pool.get('stock.location')
        warehouse_obj = self.pool.get('stock.warehouse')

        location_ids = []
        if context.get('location', False):
            if type(context['location']) == type(1):
                location_ids = [context['location']]
            elif type(context['location']) in (type(''), type(u'')):
                domain = [('name','ilike',context['location'])]
                if context.get('force_company', False):
                    domain += [('company_id', '=', context['force_company'])]
                location_ids = location_obj.search(cr, uid, domain, context=context)
            else:
                location_ids = context['location']
        else:
            if context.get('warehouse', False):
                wh = warehouse_obj.browse(cr, uid, [context['warehouse']], context=context)
            else:
                wids = warehouse_obj.search(cr, uid, [], context=context)
                wh = warehouse_obj.browse(cr, uid, wids, context=context)

            for w in warehouse_obj.browse(cr, uid, wids, context=context):
                location_ids.append(w.lot_stock_id.id)

        operator = context.get('compute_child',True) and 'child_of' or 'in'
        domain = context.get('force_company', False) and ['&', ('company_id', '=', context['force_company'])] or []
        domain += [('product_id', 'in', ids)]
        return (
            domain + [('location_id', operator, location_ids)],
            domain + ['&', ('location_dest_id', operator, location_ids), '!', ('location_id', operator, location_ids)],
            domain + ['&', ('location_id', operator, location_ids), '!', ('location_dest_id', operator, location_ids)]
        )

    def _get_domain_dates(self, cr, uid, ids, context):
        from_date = context.get('from_date',False)
        to_date = context.get('to_date',False)
        domain = []
        if from_date:
            domain.append(('date','>=',from_date))
        if to_date:
            domain.append(('date','<=',to_date))
        return domain

    def _product_available(self, cr, uid, ids, field_names=None, arg=False, context=None):
        context = context or {}
        field_names = field_names or []

        domain_products = [('product_id', 'in', ids)]
        domain_quant, domain_move_in, domain_move_out = self._get_domain_locations(cr, uid, ids, context=context)
        domain_move_in += self._get_domain_dates(cr, uid, ids, context=context) + [('state','not in',('done','cancel'))] + domain_products
        domain_move_out += self._get_domain_dates(cr, uid, ids, context=context) + [('state','not in',('done','cancel'))] + domain_products
        domain_quant += domain_products
        if context.get('lot_id') or context.get('owner_id') or context.get('package_id'):
            if context.get('lot_id'):
                domain_quant.append(('lot_id','=',context['lot_id']))
            if context.get('owner_id'):
                domain_quant.append(('owner_id','=',context['owner_id']))
            if context.get('package_id'):
                domain_quant.append(('package_id','=',context['package_id']))
            moves_in  = []
            moves_out = []
        else:
#             if field_names in ['incoming_qty', 'outgoing_qty', 'virtual_available']:
            moves_in  = self.pool.get('stock.move').read_group(cr, uid, domain_move_in, ['product_id', 'product_qty'], ['product_id'], context=context)
            moves_out = self.pool.get('stock.move').read_group(cr, uid, domain_move_out, ['product_id', 'product_qty'], ['product_id'], context=context)
            
        quants = self.pool.get('stock.quant').read_group(cr, uid, domain_quant, ['product_id', 'qty'], ['product_id'], context=context)
        quants = dict(map(lambda x: (x['product_id'][0], x['qty']), quants))
            
        moves_in = dict(map(lambda x: (x['product_id'][0], x['product_qty']), moves_in))
        moves_out = dict(map(lambda x: (x['product_id'][0], x['product_qty']), moves_out))

        res = {}
        for id in ids:
            res[id] = {
                'qty_available': quants.get(id, 0.0),
                'incoming_qty': moves_in.get(id, 0.0),
                'outgoing_qty': moves_out.get(id, 0.0),
                'virtual_available': quants.get(id, 0.0) + moves_in.get(id, 0.0) - moves_out.get(id, 0.0),
            }            
            
        return res

    _columns = {
        'reception_count': fields.function(_stock_move_count, string="Reception", type='integer', multi='pickings'),
        'delivery_count': fields.function(_stock_move_count, string="Delivery", type='integer', multi='pickings'),
        'qty_available': fields.function(_product_available, multi='qty_available',
            type='float',  digits_compute=dp.get_precision('Product Unit of Measure'),
            string='Quantity On Hand',
            help="Current quantity of products.\n"
                 "In a context with a single Stock Location, this includes "
                 "goods stored at this Location, or any of its children.\n"
                 "In a context with a single Warehouse, this includes "
                 "goods stored in the Stock Location of this Warehouse, or any "
                 "of its children.\n"
                 "stored in the Stock Location of the Warehouse of this Shop, "
                 "or any of its children.\n"
                 "Otherwise, this includes goods stored in any Stock Location "
                 "with 'internal' type."),
        'virtual_available': fields.function(_product_available, multi='qty_available',
            type='float',  digits_compute=dp.get_precision('Product Unit of Measure'),
            string='Forecasted Quantity',
            help="Forecast quantity (computed as Quantity On Hand "
                 "- Outgoing + Incoming)\n"
                 "In a context with a single Stock Location, this includes "
                 "goods stored in this location, or any of its children.\n"
                 "In a context with a single Warehouse, this includes "
                 "goods stored in the Stock Location of this Warehouse, or any "
                 "of its children.\n"
                 "stored in the Stock Location of the Warehouse of this Shop, "
                 "or any of its children.\n"
                 "Otherwise, this includes goods stored in any Stock Location "
                 "with 'internal' type."),
        'incoming_qty': fields.function(_product_available, multi='qty_available',
            type='float',  digits_compute=dp.get_precision('Product Unit of Measure'),
            string='Incoming',
            help="Quantity of products that are planned to arrive.\n"
                 "In a context with a single Stock Location, this includes "
                 "goods arriving to this Location, or any of its children.\n"
                 "In a context with a single Warehouse, this includes "
                 "goods arriving to the Stock Location of this Warehouse, or "
                 "any of its children.\n"
                 "In a context with a single Shop, this includes goods "
                 "arriving to the Stock Location of the Warehouse of this "
                 "Shop, or any of its children.\n"
                 "Otherwise, this includes goods arriving to any Stock "
                 "Location with 'internal' type."),
        'outgoing_qty': fields.function(_product_available, multi='qty_available',
            type='float',  digits_compute=dp.get_precision('Product Unit of Measure'),
            string='Outgoing',
            help="Quantity of products that are planned to leave.\n"
                 "In a context with a single Stock Location, this includes "
                 "goods leaving this Location, or any of its children.\n"
                 "In a context with a single Warehouse, this includes "
                 "goods leaving the Stock Location of this Warehouse, or "
                 "any of its children.\n"
                 "In a context with a single Shop, this includes goods "
                 "leaving the Stock Location of the Warehouse of this "
                 "Shop, or any of its children.\n"
                 "Otherwise, this includes goods leaving any Stock "
                 "Location with 'internal' type."),
        'track_production': fields.boolean('Track Manufacturing Lots', help="Forces to specify a Serial Number for all moves containing this product and generated by a Manufacturing Order"),
        'track_incoming': fields.boolean('Track Incoming Lots', help="Forces to specify a Serial Number for all moves containing this product and coming from a Supplier Location"),
        'track_outgoing': fields.boolean('Track Outgoing Lots', help="Forces to specify a Serial Number for all moves containing this product and going to a Customer Location"),
        'location_id': fields.dummy(string='Location', relation='stock.location', type='many2one'),
        'warehouse_id': fields.dummy(string='Warehouse', relation='stock.warehouse', type='many2one'),
        'orderpoint_ids': fields.one2many('stock.warehouse.orderpoint', 'product_id', 'Minimum Stock Rules'),
        'route_ids': fields.many2many('stock.location.route', 'stock_route_product', 'product_id', 'route_id', 'Routes', domain="[('product_selectable', '=', True)]",
                                    help="Depending on the modules installed, this will allow you to define the route of the product: whether it will be bought, manufactured, MTO/MTS,..."),
    }

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(product_product,self).fields_view_get(cr, uid, view_id, view_type, context, toolbar=toolbar, submenu=submenu)
        if context is None:
            context = {}
        if ('location' in context) and context['location']:
            location_info = self.pool.get('stock.location').browse(cr, uid, context['location'])
            fields=res.get('fields',{})
            if fields:
                if location_info.usage == 'supplier':
                    if fields.get('virtual_available'):
                        res['fields']['virtual_available']['string'] = _('Future Receptions')
                    if fields.get('qty_available'):
                        res['fields']['qty_available']['string'] = _('Received Qty')

                if location_info.usage == 'internal':
                    if fields.get('virtual_available'):
                        res['fields']['virtual_available']['string'] = _('Future Stock')

                if location_info.usage == 'customer':
                    if fields.get('virtual_available'):
                        res['fields']['virtual_available']['string'] = _('Future Deliveries')
                    if fields.get('qty_available'):
                        res['fields']['qty_available']['string'] = _('Delivered Qty')

                if location_info.usage == 'inventory':
                    if fields.get('virtual_available'):
                        res['fields']['virtual_available']['string'] = _('Future P&L')
                    if fields.get('qty_available'):
                        res['fields']['qty_available']['string'] = _('P&L Qty')

                if location_info.usage == 'procurement':
                    if fields.get('virtual_available'):
                        res['fields']['virtual_available']['string'] = _('Future Qty')
                    if fields.get('qty_available'):
                        res['fields']['qty_available']['string'] = _('Unplanned Qty')

                if location_info.usage == 'production':
                    if fields.get('virtual_available'):
                        res['fields']['virtual_available']['string'] = _('Future Productions')
                    if fields.get('qty_available'):
                        res['fields']['qty_available']['string'] = _('Produced Qty')
        return res

    def action_view_routes(self, cr, uid, ids, context=None):
        route_obj = self.pool.get("stock.location.route")
        act_obj = self.pool.get('ir.actions.act_window')
        mod_obj = self.pool.get('ir.model.data')
        product_route_ids = set()
        for product in self.browse(cr, uid, ids, context=context):
            product_route_ids |= set([r.id for r in product.route_ids])
            product_route_ids |= set([r.id for r in product.categ_id.total_route_ids])
        route_ids = route_obj.search(cr, uid, ['|', ('id', 'in', list(product_route_ids)), ('warehouse_selectable', '=', True)], context=context)
        result = mod_obj.get_object_reference(cr, uid, 'stock_location', 'action_routes_form')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        result['domain'] = "[('id','in',[" + ','.join(map(str, route_ids)) + "])]"
        return result

class product_template(osv.osv):
    _name = 'product.template'
    _inherit = 'product.template'
    _columns = {
        'type': fields.selection([('product', 'Stockable Product'), ('consu', 'Consumable'), ('service', 'Service')], 'Product Type', required=True, help="Consumable: Will not imply stock management for this product. \nStockable product: Will imply stock management for this product."),
        'property_stock_procurement': fields.property(
            type='many2one',
            relation='stock.location',
            string="Procurement Location",
            domain=[('usage','like','procurement')],
            help="This stock location will be used, instead of the default one, as the source location for stock moves generated by procurements."),
        'property_stock_production': fields.property(
            type='many2one',
            relation='stock.location',
            string="Production Location",
            domain=[('usage','like','production')],
            help="This stock location will be used, instead of the default one, as the source location for stock moves generated by manufacturing orders."),
        'property_stock_inventory': fields.property(
            type='many2one',
            relation='stock.location',
            string="Inventory Location",
            domain=[('usage','like','inventory')],
            help="This stock location will be used, instead of the default one, as the source location for stock moves generated when you do an inventory."),
        'sale_delay': fields.float('Customer Lead Time', help="The average delay in days between the confirmation of the customer order and the delivery of the finished products. It's the time you promise to your customers."),
        'loc_rack': fields.char('Rack', size=16),
        'loc_row': fields.char('Row', size=16),
        'loc_case': fields.char('Case', size=16),
    }

    _defaults = {
        'sale_delay': 7,
    }
    
  
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


class product_putaway_strategy(osv.osv):
    _name = 'product.putaway'
    _description = 'Put Away Strategy'
    _columns = {
        'product_categ_id':fields.many2one('product.category', 'Product Category', required=True),
        'location_id': fields.many2one('stock.location','Parent Location', help="Parent Destination Location from which a child bin location needs to be chosen", required=True), #domain=[('type', '=', 'parent')], 
        'method': fields.selection([('fixed', 'Fixed Location')], "Method", required = True),
        'location_spec_id': fields.many2one('stock.location','Specific Location', help="When the location is specific, it will be put over there"), #domain=[('type', '=', 'parent')],
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


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
