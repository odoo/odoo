# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil import relativedelta

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT


#----------------------------------------------------------
# Stock Location
#----------------------------------------------------------

class stock_location(osv.osv):
    _name = "stock.location"
    _description = "Inventory Locations"
    _parent_name = "location_id"
    _parent_store = True
    _parent_order = 'name'
    _order = 'parent_left'
    _rec_name = 'complete_name'

    def _complete_name(self, cr, uid, ids, name, args, context=None):
        """ Forms complete name of location from parent location to child location.
        @return: Dictionary of values
        """
        res = {}
        for m in self.browse(cr, uid, ids, context=context):
            res[m.id] = m.name
            parent = m.location_id
            while parent:
                res[m.id] = parent.name + '/' + res[m.id]
                parent = parent.location_id
        return res

    def _get_sublocations(self, cr, uid, ids, context=None):
        """ return all sublocations of the given stock locations (included) """
        if context is None:
            context = {}
        context_with_inactive = context.copy()
        context_with_inactive['active_test'] = False
        return self.search(cr, uid, [('id', 'child_of', ids)], context=context_with_inactive)

    def name_get(self, cr, uid, ids, context=None):
        res = []
        for location in self.browse(cr, uid, ids, context=context):
            sub_location = location
            name = location.name
            while sub_location.location_id and sub_location.usage != 'view':
                sub_location = sub_location.location_id
                name = sub_location.name + '/' + name
            res.append((location.id, name))
        return res

    _columns = {
        'name': fields.char('Location Name', required=True, translate=True),
        'active': fields.boolean('Active', help="By unchecking the active field, you may hide a location without deleting it."),
        'usage': fields.selection([
                        ('supplier', 'Vendor Location'),
                        ('view', 'View'),
                        ('internal', 'Internal Location'),
                        ('customer', 'Customer Location'),
                        ('inventory', 'Inventory Loss'),
                        ('procurement', 'Procurement'),
                        ('production', 'Production'),
                        ('transit', 'Transit Location')],
                'Location Type', required=True,
                help="""* Vendor Location: Virtual location representing the source location for products coming from your vendors
                       \n* View: Virtual location used to create a hierarchical structures for your warehouse, aggregating its child locations ; can't directly contain products
                       \n* Internal Location: Physical locations inside your own warehouses,
                       \n* Customer Location: Virtual location representing the destination location for products sent to your customers
                       \n* Inventory Loss: Virtual location serving as counterpart for inventory operations used to correct stock levels (Physical inventories)
                       \n* Procurement: Virtual location serving as temporary counterpart for procurement operations when the source (vendor or production) is not known yet. This location should be empty when the procurement scheduler has finished running.
                       \n* Production: Virtual counterpart location for production operations: this location consumes the raw material and produces finished products
                       \n* Transit Location: Counterpart location that should be used in inter-companies or inter-warehouses operations
                      """, select=True),
        'complete_name': fields.function(_complete_name, type='char', string="Full Location Name",
                            store={'stock.location': (_get_sublocations, ['name', 'location_id', 'active'], 10)}),
        'location_id': fields.many2one('stock.location', 'Parent Location', select=True, ondelete='cascade',
            help="The parent location that includes this location. Example : The 'Dispatch Zone' is the 'Gate 1' parent location."),
        'child_ids': fields.one2many('stock.location', 'location_id', 'Contains'),

        'partner_id': fields.many2one('res.partner', 'Owner', help="Owner of the location if not internal"),

        'comment': fields.text('Additional Information'),
        'posx': fields.integer('Corridor (X)', help="Optional localization details, for information purpose only"),
        'posy': fields.integer('Shelves (Y)', help="Optional localization details, for information purpose only"),
        'posz': fields.integer('Height (Z)', help="Optional localization details, for information purpose only"),

        'parent_left': fields.integer('Left Parent', select=1),
        'parent_right': fields.integer('Right Parent', select=1),

        'company_id': fields.many2one('res.company', 'Company', select=1, help='Let this field empty if this location is shared between companies'),
        'scrap_location': fields.boolean('Is a Scrap Location?', help='Check this box to allow using this location to put scrapped/damaged goods.'),
        'return_location': fields.boolean('Is a Return Location?', help='Check this box to allow using this location as a return location.'),
        'removal_strategy_id': fields.many2one('product.removal', 'Removal Strategy', help="Defines the default method used for suggesting the exact location (shelf) where to take the products from, which lot etc. for this location. This method can be enforced at the product category level, and a fallback is made on the parent locations if none is set here."),
        'putaway_strategy_id': fields.many2one('product.putaway', 'Put Away Strategy', help="Defines the default method used for suggesting the exact location (shelf) where to store the products. This method can be enforced at the product category level, and a fallback is made on the parent locations if none is set here."),
        'barcode': fields.char('Barcode', copy=False, oldname='loc_barcode'),
    }
    _defaults = {
        'active': True,
        'usage': 'internal',
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'stock.location', context=c),
        'posx': 0,
        'posy': 0,
        'posz': 0,
        'scrap_location': False,
    }
    _sql_constraints = [('barcode_company_uniq', 'unique (barcode,company_id)', 'The barcode for a location must be unique per company !')]

    def default_get(self, cr, uid, fields, context=None):
        res = super(stock_location, self).default_get(cr, uid, fields, context=context)
        if 'barcode' in fields and 'barcode' not in res and res.get('complete_name'):
            res['barcode'] = res['complete_name']
        return res

    def get_putaway_strategy(self, cr, uid, ids, product, context=None):
        ''' Returns the location where the product has to be put, if any compliant putaway strategy is found. Otherwise returns None.'''
        location = self.browse(cr, uid, ids[0], context=context)
        putaway_obj = self.pool.get('product.putaway')
        loc = location
        while loc:
            if loc.putaway_strategy_id:
                res = putaway_obj.putaway_apply(cr, uid, loc.putaway_strategy_id, product, context=context)
                if res:
                    return res
            loc = loc.location_id

    def get_warehouse(self, cr, uid, ids, context=None):
        """
            Returns warehouse id of warehouse that contains location
            :param location: browse record (stock.location)
        """
        location = self.browse(cr, uid, ids[0], context=context)
        wh_obj = self.pool.get("stock.warehouse")
        whs = wh_obj.search(cr, uid, [('view_location_id.parent_left', '<=', location.parent_left), 
                                ('view_location_id.parent_right', '>=', location.parent_left)], context=context)
        return whs and whs[0] or False

#----------------------------------------------------------
# Routes
#----------------------------------------------------------

class stock_location_route(osv.osv):
    _name = 'stock.location.route'
    _description = "Inventory Routes"
    _order = 'sequence'

    _columns = {
        'name': fields.char('Route Name', required=True, translate=True),
        'sequence': fields.integer('Sequence'),
        'pull_ids': fields.one2many('procurement.rule', 'route_id', 'Procurement Rules', copy=True),
        'active': fields.boolean('Active', help="If the active field is set to False, it will allow you to hide the route without removing it."),
        'push_ids': fields.one2many('stock.location.path', 'route_id', 'Push Rules', copy=True),
        'product_selectable': fields.boolean('Applicable on Product', help="When checked, the route will be selectable in the Inventory tab of the Product form.  It will take priority over the Warehouse route. "),
        'product_categ_selectable': fields.boolean('Applicable on Product Category', help="When checked, the route will be selectable on the Product Category.  It will take priority over the Warehouse route. "),
        'warehouse_selectable': fields.boolean('Applicable on Warehouse', help="When a warehouse is selected for this route, this route should be seen as the default route when products pass through this warehouse.  This behaviour can be overridden by the routes on the Product/Product Categories or by the Preferred Routes on the Procurement"),
        'supplied_wh_id': fields.many2one('stock.warehouse', 'Supplied Warehouse'),
        'supplier_wh_id': fields.many2one('stock.warehouse', 'Supplying Warehouse'),
        'company_id': fields.many2one('res.company', 'Company', select=1, help='Leave this field empty if this route is shared between all companies'),
        #Reverse many2many fields:
        'product_ids': fields.many2many('product.template', 'stock_route_product', 'route_id', 'product_id', 'Products'),
        'categ_ids': fields.many2many('product.category', 'stock_location_route_categ', 'route_id', 'categ_id', 'Product Categories'),
        'warehouse_ids': fields.many2many('stock.warehouse', 'stock_route_warehouse', 'route_id', 'warehouse_id', 'Warehouses'),
    }

    _defaults = {
        'sequence': lambda self, cr, uid, ctx: 0,
        'active': True,
        'product_selectable': True,
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'stock.location.route', context=c),
    }

    def write(self, cr, uid, ids, vals, context=None):
        '''when a route is deactivated, deactivate also its pull and push rules'''
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = super(stock_location_route, self).write(cr, uid, ids, vals, context=context)
        if 'active' in vals:
            push_ids = []
            pull_ids = []
            for route in self.browse(cr, uid, ids, context=context):
                if route.push_ids:
                    push_ids += [r.id for r in route.push_ids if r.active != vals['active']]
                if route.pull_ids:
                    pull_ids += [r.id for r in route.pull_ids if r.active != vals['active']]
            if push_ids:
                self.pool.get('stock.location.path').write(cr, uid, push_ids, {'active': vals['active']}, context=context)
            if pull_ids:
                self.pool.get('procurement.rule').write(cr, uid, pull_ids, {'active': vals['active']}, context=context)
        return res

    def view_product_ids(self, cr, uid, ids, context=None):
        return {
            'name': _('Products'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'product.template',
            'type': 'ir.actions.act_window',
            'domain': [('route_ids', 'in', ids[0])],
        }

    def view_categ_ids(self, cr, uid, ids, context=None):
        return {
            'name': _('Product Categories'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'product.category',
            'type': 'ir.actions.act_window',
            'domain': [('route_ids', 'in', ids[0])],
        }


class stock_location_path(osv.osv):
    _name = "stock.location.path"
    _description = "Pushed Flows"
    _order = "name"

    def _get_rules(self, cr, uid, ids, context=None):
        res = []
        for route in self.browse(cr, uid, ids, context=context):
            res += [x.id for x in route.push_ids]
        return res

    _columns = {
        'name': fields.char('Operation Name', required=True),
        'company_id': fields.many2one('res.company', 'Company'),
        'route_id': fields.many2one('stock.location.route', 'Route'),
        'location_from_id': fields.many2one('stock.location', 'Source Location', ondelete='cascade', select=1, required=True,
                                            help="This rule can be applied when a move is confirmed that has this location as destination location"),
        'location_dest_id': fields.many2one('stock.location', 'Destination Location', ondelete='cascade', select=1, required=True,
                                            help="The new location where the goods need to go"),
        'delay': fields.integer('Delay (days)', help="Number of days needed to transfer the goods"),
        'picking_type_id': fields.many2one('stock.picking.type', 'Picking Type', required=True,
                                           help="This is the picking type that will be put on the stock moves"),
        'auto': fields.selection(
            [('manual','Manual Operation'),('transparent','Automatic No Step Added')],
            'Automatic Move',
            required=True, select=1,
            help="The 'Manual Operation' value will create a stock move after the current one.  " \
                 "With 'Automatic No Step Added', the location is replaced in the original move."
            ),
        'propagate': fields.boolean('Propagate cancel and split', help='If checked, when the previous move is cancelled or split, the move generated by this move will too'),
        'active': fields.boolean('Active'),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse'),
        'route_sequence': fields.related('route_id', 'sequence', string='Route Sequence',
            store={
                'stock.location.route': (_get_rules, ['sequence'], 10),
                'stock.location.path': (lambda self, cr, uid, ids, c={}: ids, ['route_id'], 10),
        }),
        'sequence': fields.integer('Sequence'),
    }
    _defaults = {
        'auto': 'manual',
        'delay': 0,
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'procurement.order', context=c),
        'propagate': True,
        'active': True,
    }

    def _prepare_push_apply(self, cr, uid, ids, move, context=None):
        rule = self.browse(cr, uid, ids[0], context=context)
        newdate = (datetime.strptime(move.date_expected, DEFAULT_SERVER_DATETIME_FORMAT) + relativedelta.relativedelta(days=rule.delay or 0)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        return {
                'origin': move.origin or move.picking_id.name or "/",
                'location_id': move.location_dest_id.id,
                'location_dest_id': rule.location_dest_id.id,
                'date': newdate,
                'company_id': rule.company_id and rule.company_id.id or False,
                'date_expected': newdate,
                'picking_id': False,
                'picking_type_id': rule.picking_type_id and rule.picking_type_id.id or False,
                'propagate': rule.propagate,
                'push_rule_id': rule.id,
                'warehouse_id': rule.warehouse_id and rule.warehouse_id.id or False,
            }

    def _apply(self, cr, uid, ids, move, context=None):
        rule = self.browse(cr, uid, ids[0], context=context)
        move_obj = self.pool.get('stock.move')
        newdate = (datetime.strptime(move.date_expected, DEFAULT_SERVER_DATETIME_FORMAT) + relativedelta.relativedelta(days=rule.delay or 0)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        if rule.auto == 'transparent':
            old_dest_location = move.location_dest_id.id
            move_obj.write(cr, uid, [move.id], {
                'date': newdate,
                'date_expected': newdate,
                'location_dest_id': rule.location_dest_id.id
            })
            #avoid looping if a push rule is not well configured
            if rule.location_dest_id.id != old_dest_location:
                #call again push_apply to see if a next step is defined
                move._push_apply()
        else:
            vals = self._prepare_push_apply(cr, uid, [rule.id], move, context=context)
            move_id = move_obj.copy(cr, uid, move.id, vals, context=context)
            move_obj.write(cr, uid, [move.id], {
                'move_dest_id': move_id,
            })
            move_obj.action_confirm(cr, uid, [move_id], context=None)
