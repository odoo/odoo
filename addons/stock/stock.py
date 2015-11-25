# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime
from dateutil import relativedelta
import json
import time
import sets

import openerp
from openerp.osv import fields, osv
from openerp.tools.float_utils import float_compare, float_round
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from openerp import SUPERUSER_ID, api, models
import openerp.addons.decimal_precision as dp
from openerp.addons.procurement import procurement
import logging
from openerp.exceptions import UserError


_logger = logging.getLogger(__name__)
#----------------------------------------------------------
# Incoterms
#----------------------------------------------------------
class stock_incoterms(osv.osv):
    _name = "stock.incoterms"
    _description = "Incoterms"
    _columns = {
        'name': fields.char('Name', required=True, help="Incoterms are series of sales terms. They are used to divide transaction costs and responsibilities between buyer and seller and reflect state-of-the-art transportation practices."),
        'code': fields.char('Code', size=3, required=True, help="Incoterm Standard Code"),
        'active': fields.boolean('Active', help="By unchecking the active field, you may hide an INCOTERM you will not use."),
    }
    _defaults = {
        'active': True,
    }

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

    def _location_owner(self, cr, uid, location, context=None):
        ''' Return the company owning the location if any '''
        return location and (location.usage == 'internal') and location.company_id or False

    def _complete_name(self, cr, uid, ids, name, args, context=None):
        """ Forms complete name of location from parent location to child location.
        @return: Dictionary of values
        """
        res = {}
        for m in self.browse(cr, uid, ids, context=context):
            res[m.id] = m.name
            parent = m.location_id
            while parent:
                res[m.id] = parent.name + ' / ' + res[m.id]
                parent = parent.location_id
        return res

    def _get_sublocations(self, cr, uid, ids, context=None):
        """ return all sublocations of the given stock locations (included) """
        if context is None:
            context = {}
        context_with_inactive = context.copy()
        context_with_inactive['active_test'] = False
        return self.search(cr, uid, [('id', 'child_of', ids)], context=context_with_inactive)

    def _name_get(self, cr, uid, location, context=None):
        name = location.name
        while location.location_id and location.usage != 'view':
            location = location.location_id
            name = location.name + '/' + name
        return name

    def name_get(self, cr, uid, ids, context=None):
        res = []
        for location in self.browse(cr, uid, ids, context=context):
            res.append((location.id, self._name_get(cr, uid, location, context=context)))
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
        'location_id': fields.many2one('stock.location', 'Parent Location', select=True, ondelete='cascade'),
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

    def create(self, cr, uid, default, context=None):
        if not default.get('barcode', False):
            default.update({'barcode': default.get('complete_name', False)})
        return super(stock_location, self).create(cr, uid, default, context=context)

    def get_putaway_strategy(self, cr, uid, location, product, context=None):
        ''' Returns the location where the product has to be put, if any compliant putaway strategy is found. Otherwise returns None.'''
        putaway_obj = self.pool.get('product.putaway')
        loc = location
        while loc:
            if loc.putaway_strategy_id:
                res = putaway_obj.putaway_apply(cr, uid, loc.putaway_strategy_id, product, context=context)
                if res:
                    return res
            loc = loc.location_id

    def _default_removal_strategy(self, cr, uid, context=None):
        return 'fifo'

    def get_removal_strategy(self, cr, uid, qty, move, ops=False, context=None):
        ''' Returns the removal strategy to consider for the given move/ops
            :rtype: char
        '''
        product = move.product_id
        location = move.location_id
        if product.categ_id.removal_strategy_id:
            return product.categ_id.removal_strategy_id.method
        loc = location
        while loc:
            if loc.removal_strategy_id:
                return loc.removal_strategy_id.method
            loc = loc.location_id
        return self._default_removal_strategy(cr, uid, context=context)

    def get_warehouse(self, cr, uid, location, context=None):
        """
            Returns warehouse id of warehouse that contains location
            :param location: browse record (stock.location)
        """
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


#----------------------------------------------------------
# Quants
#----------------------------------------------------------

class stock_quant(osv.osv):
    """
    Quants are the smallest unit of stock physical instances
    """
    _name = "stock.quant"
    _description = "Quants"

    def _get_quant_name(self, cr, uid, ids, name, args, context=None):
        """ Forms complete name of location from parent location to child location.
        @return: Dictionary of values
        """
        res = {}
        for q in self.browse(cr, uid, ids, context=context):

            res[q.id] = q.product_id.code or ''
            if q.lot_id:
                res[q.id] = q.lot_id.name
            res[q.id] += ': ' + str(q.qty) + q.product_id.uom_id.name
        return res

    def _calc_inventory_value(self, cr, uid, ids, name, attr, context=None):
        context = dict(context or {})
        res = {}
        uid_company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        for quant in self.browse(cr, uid, ids, context=context):
            context.pop('force_company', None)
            if quant.company_id.id != uid_company_id:
                #if the company of the quant is different than the current user company, force the company in the context
                #then re-do a browse to read the property fields for the good company.
                context['force_company'] = quant.company_id.id
                quant = self.browse(cr, uid, quant.id, context=context)
            res[quant.id] = self._get_inventory_value(cr, uid, quant, context=context)
        return res

    def _get_inventory_value(self, cr, uid, quant, context=None):
        return quant.product_id.standard_price * quant.qty

    _columns = {
        'name': fields.function(_get_quant_name, type='char', string='Identifier'),
        'product_id': fields.many2one('product.product', 'Product', required=True, ondelete="restrict", readonly=True, select=True),
        'location_id': fields.many2one('stock.location', 'Location', required=True, ondelete="restrict", readonly=True, select=True, auto_join=True),
        'qty': fields.float('Quantity', required=True, help="Quantity of products in this quant, in the default unit of measure of the product", readonly=True, select=True),
        'product_uom_id': fields.related('product_id', 'uom_id', type='many2one', relation="product.uom", string='Unit of Measure', readonly=True),
        'package_id': fields.many2one('stock.quant.package', string='Package', help="The package containing this quant", readonly=True, select=True),
        'packaging_type_id': fields.related('package_id', 'packaging_id', type='many2one', relation='product.packaging', string='Type of packaging', readonly=True, store=True),
        'reservation_id': fields.many2one('stock.move', 'Reserved for Move', help="The move the quant is reserved for", readonly=True, select=True),
        'lot_id': fields.many2one('stock.production.lot', 'Lot', readonly=True, select=True, ondelete="restrict"),
        'cost': fields.float('Unit Cost'),
        'owner_id': fields.many2one('res.partner', 'Owner', help="This is the owner of the quant", readonly=True, select=True),

        'create_date': fields.datetime('Creation Date', readonly=True),
        'in_date': fields.datetime('Incoming Date', readonly=True, select=True),

        'history_ids': fields.many2many('stock.move', 'stock_quant_move_rel', 'quant_id', 'move_id', 'Moves', help='Moves that operate(d) on this quant', copy=False),
        'company_id': fields.many2one('res.company', 'Company', help="The company to which the quants belong", required=True, readonly=True, select=True),
        'inventory_value': fields.function(_calc_inventory_value, string="Inventory Value", type='float', readonly=True),

        # Used for negative quants to reconcile after compensated by a new positive one
        'propagated_from_id': fields.many2one('stock.quant', 'Linked Quant', help='The negative quant this is coming from', readonly=True, select=True),
        'negative_move_id': fields.many2one('stock.move', 'Move Negative Quant', help='If this is a negative quant, this will be the move that caused this negative quant.', readonly=True),
        'negative_dest_location_id': fields.related('negative_move_id', 'location_dest_id', type='many2one', relation='stock.location', string="Negative Destination Location", readonly=True, 
                                                    help="Technical field used to record the destination location of a move that created a negative quant"),
    }

    _defaults = {
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'stock.quant', context=c),
    }

    def init(self, cr):
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('stock_quant_product_location_index',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX stock_quant_product_location_index ON stock_quant (product_id, location_id, company_id, qty, in_date, reservation_id)')

    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False, lazy=True):
        ''' Overwrite the read_group in order to sum the function field 'inventory_value' in group by'''
        res = super(stock_quant, self).read_group(cr, uid, domain, fields, groupby, offset=offset, limit=limit, context=context, orderby=orderby, lazy=lazy)
        if 'inventory_value' in fields:
            for line in res:
                if '__domain' in line:
                    lines = self.search(cr, uid, line['__domain'], context=context)
                    inv_value = 0.0
                    for line2 in self.browse(cr, uid, lines, context=context):
                        inv_value += line2.inventory_value
                    line['inventory_value'] = inv_value
        return res

    def action_view_quant_history(self, cr, uid, ids, context=None):
        '''
        This function returns an action that display the history of the quant, which
        mean all the stock moves that lead to this quant creation with this quant quantity.
        '''
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')

        result = mod_obj.get_object_reference(cr, uid, 'stock', 'action_move_form2')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context={})[0]

        move_ids = []
        for quant in self.browse(cr, uid, ids, context=context):
            move_ids += [move.id for move in quant.history_ids]

        result['domain'] = "[('id','in',[" + ','.join(map(str, move_ids)) + "])]"
        return result

    def quants_reserve(self, cr, uid, quants, move, link=False, context=None):
        '''This function reserves quants for the given move (and optionally given link). If the total of quantity reserved is enough, the move's state
        is also set to 'assigned'

        :param quants: list of tuple(quant browse record or None, qty to reserve). If None is given as first tuple element, the item will be ignored. Negative quants should not be received as argument
        :param move: browse record
        :param link: browse record (stock.move.operation.link)
        '''
        toreserve = []
        reserved_availability = move.reserved_availability
        #split quants if needed
        for quant, qty in quants:
            if qty <= 0.0 or (quant and quant.qty <= 0.0):
                raise UserError(_('You can not reserve a negative quantity or a negative quant.'))
            if not quant:
                continue
            self._quant_split(cr, uid, quant, qty, context=context)
            toreserve.append(quant.id)
            reserved_availability += quant.qty
        #reserve quants
        if toreserve:
            self.write(cr, SUPERUSER_ID, toreserve, {'reservation_id': move.id}, context=context)
        #check if move'state needs to be set as 'assigned'
        rounding = move.product_id.uom_id.rounding
        if float_compare(reserved_availability, move.product_qty, precision_rounding=rounding) == 0 and move.state in ('confirmed', 'waiting')  :
            self.pool.get('stock.move').write(cr, uid, [move.id], {'state': 'assigned'}, context=context)
        elif float_compare(reserved_availability, 0, precision_rounding=rounding) > 0 and not move.partially_available:
            self.pool.get('stock.move').write(cr, uid, [move.id], {'partially_available': True}, context=context)

    def quants_move(self, cr, uid, quants, move, location_to, location_from=False, lot_id=False, owner_id=False, src_package_id=False, dest_package_id=False, entire_pack=False, context=None):
        """Moves all given stock.quant in the given destination location.  Unreserve from current move.
        :param quants: list of tuple(browse record(stock.quant) or None, quantity to move)
        :param move: browse record (stock.move)
        :param location_to: browse record (stock.location) depicting where the quants have to be moved
        :param location_from: optional browse record (stock.location) explaining where the quant has to be taken (may differ from the move source location in case a removal strategy applied). This parameter is only used to pass to _quant_create if a negative quant must be created
        :param lot_id: ID of the lot that must be set on the quants to move
        :param owner_id: ID of the partner that must own the quants to move
        :param src_package_id: ID of the package that contains the quants to move
        :param dest_package_id: ID of the package that must be set on the moved quant
        """
        quants_reconcile = []
        to_move_quants = []
        self._check_location(cr, uid, location_to, context=context)
        for quant, qty in quants:
            if not quant:
                #If quant is None, we will create a quant to move (and potentially a negative counterpart too)
                quant = self._quant_create(cr, uid, qty, move, lot_id=lot_id, owner_id=owner_id, src_package_id=src_package_id, dest_package_id=dest_package_id, force_location_from=location_from, force_location_to=location_to, context=context)
            else:
                self._quant_split(cr, uid, quant, qty, context=context)
                to_move_quants.append(quant)
            quants_reconcile.append(quant)
        if to_move_quants:
            to_recompute_move_ids = [x.reservation_id.id for x in to_move_quants if x.reservation_id and x.reservation_id.id != move.id]
            self.move_quants_write(cr, uid, to_move_quants, move, location_to, dest_package_id, lot_id=lot_id, entire_pack=entire_pack, context=context)
            self.pool.get('stock.move').recalculate_move_state(cr, uid, to_recompute_move_ids, context=context)
        if location_to.usage == 'internal':
            # Do manual search for quant to avoid full table scan (order by id)
            cr.execute("""
                SELECT 0 FROM stock_quant, stock_location WHERE product_id = %s AND stock_location.id = stock_quant.location_id AND
                ((stock_location.parent_left >= %s AND stock_location.parent_left < %s) OR stock_location.id = %s) AND qty < 0.0 LIMIT 1
            """, (move.product_id.id, location_to.parent_left, location_to.parent_right, location_to.id))
            if cr.fetchone():
                for quant in quants_reconcile:
                    self._quant_reconcile_negative(cr, uid, quant, move, context=context)

    def move_quants_write(self, cr, uid, quants, move, location_dest_id, dest_package_id, lot_id = False, entire_pack=False, context=None):
        context=context or {}
        vals = {'location_id': location_dest_id.id,
                'history_ids': [(4, move.id)],
                'reservation_id': False}
        if lot_id and any(x.id for x in quants if not x.lot_id.id):
            vals['lot_id'] = lot_id
        if not entire_pack:
            vals.update({'package_id': dest_package_id})
        self.write(cr, SUPERUSER_ID, [q.id for q in quants], vals, context=context)

    def quants_get_preferred_domain(self, cr, uid, qty, move, ops=False, lot_id=False, domain=None, preferred_domain_list=[], context=None):
        ''' This function tries to find quants for the given domain and move/ops, by trying to first limit
            the choice on the quants that match the first item of preferred_domain_list as well. But if the qty requested is not reached
            it tries to find the remaining quantity by looping on the preferred_domain_list (tries with the second item and so on).
            Make sure the quants aren't found twice => all the domains of preferred_domain_list should be orthogonal
        '''
        context = context or {}
        domain = domain or [('qty', '>', 0.0)]
        domain = list(domain)
        quants = [(None, qty)]
        if ops:
            restrict_lot_id = lot_id
            location = ops.location_id
            domain += [('owner_id', '=', ops.owner_id.id)]
            if ops.package_id and not ops.product_id:
                domain += [('package_id', 'child_of', ops.package_id.id)]
            elif ops.package_id and ops.product_id:
                domain += [('package_id', '=', ops.package_id.id)]
            else:
                domain += [('package_id', '=', False)]
            domain += [('location_id', '=', ops.location_id.id)]
        else:
            restrict_lot_id = move.restrict_lot_id.id
            location = move.location_id
            domain += [('owner_id', '=', move.restrict_partner_id.id)]
            domain += [('location_id', 'child_of', move.location_id.id)]
        if context.get('force_company'): 
            domain += [('company_id', '=', context.get('force_company'))]
        else:
            domain += [('company_id', '=', move.company_id.id)]
        removal_strategy = self.pool.get('stock.location').get_removal_strategy(cr, uid, qty, move, ops=ops, context=context)
        product = move.product_id
        domain += [('product_id', '=', move.product_id.id)]

        #don't look for quants in location that are of type production, supplier or inventory.
        if location.usage in ['inventory', 'production', 'supplier']:
            return quants
        res_qty = qty
        if restrict_lot_id:
            if not preferred_domain_list:
                preferred_domain_list = [[('lot_id', '=', restrict_lot_id)], [('lot_id', '=', False)]]
            else:
                lot_list = []
                no_lot_list = []
                for pref_domain in preferred_domain_list:
                    pref_lot_domain = pref_domain + [('lot_id', '=', restrict_lot_id)]
                    pref_no_lot_domain = pref_domain + [('lot_id', '=', False)]
                    lot_list.append(pref_lot_domain)
                    no_lot_list.append(pref_no_lot_domain)
                preferred_domain_list = lot_list + no_lot_list

        if not preferred_domain_list:
            return self.quants_get(cr, uid, qty, move, ops=ops, domain=domain, removal_strategy=removal_strategy, context=context)
        for preferred_domain in preferred_domain_list:
            res_qty_cmp = float_compare(res_qty, 0, precision_rounding=product.uom_id.rounding)
            if res_qty_cmp > 0:
                #try to replace the last tuple (None, res_qty) with something that wasn't chosen at first because of the preferred order
                quants.pop()
                tmp_quants = self.quants_get(cr, uid, res_qty, move, ops=ops, domain=domain + preferred_domain,
                                             removal_strategy=removal_strategy, context=context)
                for quant in tmp_quants:
                    if quant[0]:
                        res_qty -= quant[1]
                quants += tmp_quants
        return quants

    def quants_get(self, cr, uid, qty, move, ops=False, domain=None, removal_strategy='fifo', context=None):
        """
        Use the removal strategies of product to search for the correct quants
        If you inherit, put the super at the end of your method.

        :location: browse record of the parent location where the quants have to be found
        :product: browse record of the product to find
        :qty in UoM of product
        """
        domain = domain or [('qty', '>', 0.0)]
        return self.apply_removal_strategy(cr, uid, qty, move, ops=ops, domain=domain, removal_strategy=removal_strategy, context=context)

    def apply_removal_strategy(self, cr, uid, quantity, move, ops=False, domain=None, removal_strategy='fifo', context=None):
        if removal_strategy == 'fifo':
            order = 'in_date, id'
            return self._quants_get_order(cr, uid, quantity, move, ops=ops, domain=domain, orderby=order, context=context)
        elif removal_strategy == 'lifo':
            order = 'in_date desc, id desc'
            return self._quants_get_order(cr, uid, quantity, move, ops=ops, domain=domain, orderby=order, context=context)
        raise UserError(_('Removal strategy %s not implemented.' % (removal_strategy,)))

    def _quant_create(self, cr, uid, qty, move, lot_id=False, owner_id=False, src_package_id=False, dest_package_id=False,
                      force_location_from=False, force_location_to=False, context=None):
        '''Create a quant in the destination location and create a negative quant in the source location if it's an internal location.
        '''
        if context is None:
            context = {}
        price_unit = self.pool.get('stock.move').get_price_unit(cr, uid, move, context=context)
        location = force_location_to or move.location_dest_id
        rounding = move.product_id.uom_id.rounding
        vals = {
            'product_id': move.product_id.id,
            'location_id': location.id,
            'qty': float_round(qty, precision_rounding=rounding),
            'cost': price_unit,
            'history_ids': [(4, move.id)],
            'in_date': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            'company_id': move.company_id.id,
            'lot_id': lot_id,
            'owner_id': owner_id,
            'package_id': dest_package_id,
        }
        if move.location_id.usage == 'internal':
            #if we were trying to move something from an internal location and reach here (quant creation),
            #it means that a negative quant has to be created as well.
            negative_vals = vals.copy()
            negative_vals['location_id'] = force_location_from and force_location_from.id or move.location_id.id
            negative_vals['qty'] = float_round(-qty, precision_rounding=rounding)
            negative_vals['cost'] = price_unit
            negative_vals['negative_move_id'] = move.id
            negative_vals['package_id'] = src_package_id
            negative_quant_id = self.create(cr, SUPERUSER_ID, negative_vals, context=context)
            vals.update({'propagated_from_id': negative_quant_id})

        # In case of serial tracking, check if the product does not exist somewhere internally already
        picking_type = move.picking_id and move.picking_id.picking_type_id or False
        if lot_id and move.product_id.tracking == 'serial' and (not picking_type or (picking_type.use_create_lots or picking_type.use_existing_lots)):
            if qty != 1.0:
                raise UserError(_('You should only receive by the piece with the same serial number'))
            other_quants = self.search(cr, uid, [('product_id', '=', move.product_id.id), ('lot_id', '=', lot_id),
                                                 ('qty', '>', 0.0), ('location_id.usage', '=', 'internal')], context=context)
            if other_quants:
                lot_name = self.pool['stock.production.lot'].browse(cr, uid, lot_id, context=context).name
                raise UserError(_('The serial number %s is already in stock') % lot_name)

        #create the quant as superuser, because we want to restrict the creation of quant manually: we should always use this method to create quants
        quant_id = self.create(cr, SUPERUSER_ID, vals, context=context)
        return self.browse(cr, uid, quant_id, context=context)

    def _quant_split(self, cr, uid, quant, qty, context=None):
        context = context or {}
        rounding = quant.product_id.uom_id.rounding
        if float_compare(abs(quant.qty), abs(qty), precision_rounding=rounding) <= 0: # if quant <= qty in abs, take it entirely
            return False
        qty_round = float_round(qty, precision_rounding=rounding)
        new_qty_round = float_round(quant.qty - qty, precision_rounding=rounding)
        # Fetch the history_ids manually as it will not do a join with the stock moves then (=> a lot faster)
        cr.execute("""SELECT move_id FROM stock_quant_move_rel WHERE quant_id = %s""", (quant.id,))
        res = cr.fetchall()
        new_quant = self.copy(cr, SUPERUSER_ID, quant.id, default={'qty': new_qty_round, 'history_ids': [(4, x[0]) for x in res]}, context=context)
        self.write(cr, SUPERUSER_ID, quant.id, {'qty': qty_round}, context=context)
        return self.browse(cr, uid, new_quant, context=context)

    def _get_latest_move(self, cr, uid, quant, context=None):
        move = False
        for m in quant.history_ids:
            if not move or m.date > move.date:
                move = m
        return move

    @api.cr_uid_ids_context
    def _quants_merge(self, cr, uid, solved_quant_ids, solving_quant, context=None):
        path = []
        for move in solving_quant.history_ids:
            path.append((4, move.id))
        self.write(cr, SUPERUSER_ID, solved_quant_ids, {'history_ids': path}, context=context)

    def _search_quants_to_reconcile(self, cr, uid, quant, context=None):
        """
            Searches negative quants to reconcile for where the quant to reconcile is put
        """
        dom = [('qty', '<', 0)]
        order = 'in_date'
        dom += [('location_id', 'child_of', quant.location_id.id), ('product_id', '=', quant.product_id.id),
                ('owner_id', '=', quant.owner_id.id)]
        if quant.package_id.id:
            dom += [('package_id', '=', quant.package_id.id)]
        if quant.lot_id:
            dom += ['|', ('lot_id', '=', False), ('lot_id', '=', quant.lot_id.id)]
            order = 'lot_id, in_date'
        # Do not let the quant eat itself, or it will kill its history (e.g. returns / Stock -> Stock)
        dom += [('id', '!=', quant.propagated_from_id.id)]
        quants_search = self.search(cr, uid, dom, order=order, context=context)
        product = quant.product_id
        quants = []
        quantity = quant.qty
        for quant in self.browse(cr, uid, quants_search, context=context):
            rounding = product.uom_id.rounding
            if float_compare(quantity, abs(quant.qty), precision_rounding=rounding) >= 0:
                quants += [(quant, abs(quant.qty))]
                quantity -= abs(quant.qty)
            elif float_compare(quantity, 0.0, precision_rounding=rounding) != 0:
                quants += [(quant, quantity)]
                quantity = 0
                break
        return quants

    def _quant_reconcile_negative(self, cr, uid, quant, move, context=None):
        """
            When new quant arrive in a location, try to reconcile it with
            negative quants. If it's possible, apply the cost of the new
            quant to the counterpart of the negative quant.
        """
        solving_quant = quant
        quants = self._search_quants_to_reconcile(cr, uid, quant, context=context)
        product_uom_rounding = quant.product_id.uom_id.rounding
        for quant_neg, qty in quants:
            if not quant_neg or not solving_quant:
                continue
            to_solve_quant_ids = self.search(cr, uid, [('propagated_from_id', '=', quant_neg.id)], context=context)
            if not to_solve_quant_ids:
                continue
            solving_qty = qty
            solved_quant_ids = []
            for to_solve_quant in self.browse(cr, uid, to_solve_quant_ids, context=context):
                if float_compare(solving_qty, 0, precision_rounding=product_uom_rounding) <= 0:
                    continue
                solved_quant_ids.append(to_solve_quant.id)
                self._quant_split(cr, uid, to_solve_quant, min(solving_qty, to_solve_quant.qty), context=context)
                solving_qty -= min(solving_qty, to_solve_quant.qty)
            remaining_solving_quant = self._quant_split(cr, uid, solving_quant, qty, context=context)
            remaining_neg_quant = self._quant_split(cr, uid, quant_neg, -qty, context=context)
            #if the reconciliation was not complete, we need to link together the remaining parts
            if remaining_neg_quant:
                remaining_to_solve_quant_ids = self.search(cr, uid, [('propagated_from_id', '=', quant_neg.id), ('id', 'not in', solved_quant_ids)], context=context)
                if remaining_to_solve_quant_ids:
                    self.write(cr, SUPERUSER_ID, remaining_to_solve_quant_ids, {'propagated_from_id': remaining_neg_quant.id}, context=context)
            if solving_quant.propagated_from_id and solved_quant_ids:
                self.write(cr, SUPERUSER_ID, solved_quant_ids, {'propagated_from_id': solving_quant.propagated_from_id.id}, context=context)
            #delete the reconciled quants, as it is replaced by the solved quants
            self.unlink(cr, SUPERUSER_ID, [quant_neg.id], context=context)
            if solved_quant_ids:
                #price update + accounting entries adjustments
                self._price_update(cr, uid, solved_quant_ids, solving_quant.cost, context=context)
                #merge history (and cost?)
                self._quants_merge(cr, uid, solved_quant_ids, solving_quant, context=context)
            self.unlink(cr, SUPERUSER_ID, [solving_quant.id], context=context)
            solving_quant = remaining_solving_quant

    def _price_update(self, cr, uid, ids, newprice, context=None):
        self.write(cr, SUPERUSER_ID, ids, {'cost': newprice}, context=context)

    def quants_unreserve(self, cr, uid, move, context=None):
        related_quants = [x.id for x in move.reserved_quant_ids]
        if related_quants:
            #if move has a picking_id, write on that picking that pack_operation might have changed and need to be recomputed
            if move.partially_available:
                self.pool.get("stock.move").write(cr, uid, [move.id], {'partially_available': False}, context=context)
            self.write(cr, SUPERUSER_ID, related_quants, {'reservation_id': False}, context=context)

    def _quants_get_order(self, cr, uid, quantity, move, ops=False, domain=[], orderby='in_date', context=None):
        ''' Implementation of removal strategies
            If it can not reserve, it will return a tuple (None, qty)
        '''
        if context is None:
            context = {}
        product = move.product_id
        res = []
        offset = 0
        while float_compare(quantity, 0, precision_rounding=product.uom_id.rounding) > 0:
            quants = self.search(cr, uid, domain, order=orderby, limit=10, offset=offset, context=context)
            if not quants:
                res.append((None, quantity))
                break
            for quant in self.browse(cr, uid, quants, context=context):
                rounding = product.uom_id.rounding
                if float_compare(quantity, abs(quant.qty), precision_rounding=rounding) >= 0:
                    res += [(quant, abs(quant.qty))]
                    quantity -= abs(quant.qty)
                elif float_compare(quantity, 0.0, precision_rounding=rounding) != 0:
                    res += [(quant, quantity)]
                    quantity = 0
                    break
            offset += 10
        return res

    def _check_location(self, cr, uid, location, context=None):
        if location.usage == 'view':
            raise UserError(_('You cannot move to a location of type view %s.') % (location.name))
        return True

#----------------------------------------------------------
# Stock Picking
#----------------------------------------------------------

class stock_picking(models.Model):
    _name = "stock.picking"
    _inherit = ['mail.thread']
    _description = "Transfer"
    _order = "priority desc, date asc, id desc"

    def _set_min_date(self, cr, uid, id, field, value, arg, context=None):
        move_obj = self.pool.get("stock.move")
        if value:
            move_ids = [move.id for move in self.browse(cr, uid, id, context=context).move_lines]
            move_obj.write(cr, uid, move_ids, {'date_expected': value}, context=context)

    def _set_priority(self, cr, uid, id, field, value, arg, context=None):
        move_obj = self.pool.get("stock.move")
        if value:
            move_ids = [move.id for move in self.browse(cr, uid, id, context=context).move_lines]
            move_obj.write(cr, uid, move_ids, {'priority': value}, context=context)

    def get_min_max_date(self, cr, uid, ids, field_name, arg, context=None):
        """ Finds minimum and maximum dates for picking.
        @return: Dictionary of values
        """
        res = {}
        for id in ids:
            res[id] = {'min_date': False, 'max_date': False, 'priority': '1'}
        if not ids:
            return res
        cr.execute("""select
                picking_id,
                min(date_expected),
                max(date_expected),
                max(priority)
            from
                stock_move
            where
                picking_id IN %s
            group by
                picking_id""", (tuple(ids),))
        for pick, dt1, dt2, prio in cr.fetchall():
            res[pick]['min_date'] = dt1
            res[pick]['max_date'] = dt2
            res[pick]['priority'] = prio
        return res

    def create(self, cr, user, vals, context=None):
        context = context or {}
        if ('name' not in vals) or (vals.get('name') in ('/', False)):
            ptype_id = vals.get('picking_type_id', context.get('default_picking_type_id', False))
            sequence_id = self.pool.get('stock.picking.type').browse(cr, user, ptype_id, context=context).sequence_id.id
            vals['name'] = self.pool.get('ir.sequence').next_by_id(cr, user, sequence_id, context=context)
        # As the on_change in one2many list is WIP, we will overwrite the locations on the stock moves here
        # As it is a create the format will be a list of (0, 0, dict)
        if vals.get('move_lines') and vals.get('location_id') and vals.get('location_dest_id'):
            for move in vals['move_lines']:
                if len(move) == 3:
                    move[2]['location_id'] = vals['location_id']
                    move[2]['location_dest_id'] = vals['location_dest_id']
        return super(stock_picking, self).create(cr, user, vals, context)

    def write(self, cr, uid, ids, vals, context=None):
        res = super(stock_picking, self).write(cr, uid, ids, vals, context=context)
        after_vals = {}
        if vals.get('location_id'):
            after_vals['location_id'] = vals['location_id']
        if vals.get('location_dest_id'):
            after_vals['location_dest_id'] = vals['location_dest_id']
        # Change locations of moves if those of the picking change
        if after_vals:
            moves = []
            for pick in self.browse(cr, uid, ids, context=context):
                moves += [x.id for x in pick.move_lines if not x.scrapped]
            if moves:
                self.pool['stock.move'].write(cr, uid, moves, after_vals, context=context)
        return res

    def _state_get(self, cr, uid, ids, field_name, arg, context=None):
        '''The state of a picking depends on the state of its related stock.move
            draft: the picking has no line or any one of the lines is draft
            done, draft, cancel: all lines are done / draft / cancel
            confirmed, waiting, assigned, partially_available depends on move_type (all at once or partial)
        '''
        res = {}
        for pick in self.browse(cr, uid, ids, context=context):
            if not pick.move_lines:
                res[pick.id] = pick.launch_pack_operations and 'assigned' or 'draft'
                continue
            if any([x.state == 'draft' for x in pick.move_lines]):
                res[pick.id] = 'draft'
                continue
            if all([x.state == 'cancel' for x in pick.move_lines]):
                res[pick.id] = 'cancel'
                continue
            if all([x.state in ('cancel', 'done') for x in pick.move_lines]):
                res[pick.id] = 'done'
                continue

            order = {'confirmed': 0, 'waiting': 1, 'assigned': 2}
            order_inv = {0: 'confirmed', 1: 'waiting', 2: 'assigned'}
            lst = [order[x.state] for x in pick.move_lines if x.state not in ('cancel', 'done')]
            if pick.move_type == 'one':
                res[pick.id] = order_inv[min(lst)]
            else:
                #we are in the case of partial delivery, so if all move are assigned, picking
                #should be assign too, else if one of the move is assigned, or partially available, picking should be
                #in partially available state, otherwise, picking is in waiting or confirmed state
                res[pick.id] = order_inv[max(lst)]
                if not all(x == 2 for x in lst):
                    if any(x == 2 for x in lst):
                        res[pick.id] = 'partially_available'
                    else:
                        #if all moves aren't assigned, check if we have one product partially available
                        for move in pick.move_lines:
                            if move.partially_available:
                                res[pick.id] = 'partially_available'
                                break
        return res

    def _get_pickings(self, cr, uid, ids, context=None):
        res = set()
        for move in self.browse(cr, uid, ids, context=context):
            if move.picking_id:
                res.add(move.picking_id.id)
        return list(res)

    def _get_pickings_dates_priority(self, cr, uid, ids, context=None):
        res = set()
        for move in self.browse(cr, uid, ids, context=context):
            if move.picking_id and (not (move.picking_id.min_date < move.date_expected < move.picking_id.max_date) or move.priority > move.picking_id.priority):
                res.add(move.picking_id.id)
        return list(res)

    def _get_pack_operation_exist(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for pick in self.browse(cr, uid, ids, context=context):
            res[pick.id] = False
            if pick.pack_operation_ids:
                res[pick.id] = True
        return res

    def _get_quant_reserved_exist(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for pick in self.browse(cr, uid, ids, context=context):
            res[pick.id] = False
            for move in pick.move_lines:
                if move.reserved_quant_ids:
                    res[pick.id] = True
                    continue
        return res

    def action_assign_owner(self, cr, uid, ids, context=None):
        for picking in self.browse(cr, uid, ids, context=context):
            packop_ids = [op.id for op in picking.pack_operation_ids]
            self.pool.get('stock.pack.operation').write(cr, uid, packop_ids, {'owner_id': picking.owner_id.id}, context=context)

    def onchange_picking_type(self, cr, uid, ids, picking_type_id, partner_id, context=None):
        res = {}
        if picking_type_id:
            picking_type = self.pool['stock.picking.type'].browse(cr, uid, picking_type_id, context=context)
            if not picking_type.default_location_src_id:
                if partner_id:
                    partner = self.pool['res.partner'].browse(cr, uid, partner_id, context=context)
                    location_id = partner.property_stock_supplier.id
                else:
                    customerloc, supplierloc = self.pool['stock.warehouse']._get_partner_locations(cr, uid, [], context=context)
                    location_id = supplierloc.id
            else:
                location_id = picking_type.default_location_src_id.id

            if not picking_type.default_location_dest_id:
                if partner_id:
                    partner = self.pool['res.partner'].browse(cr, uid, partner_id, context=context)
                    location_dest_id = partner.property_stock_customer.id
                else:
                    customerloc, supplierloc = self.pool['stock.warehouse']._get_partner_locations(cr, uid, [], context=context)
                    location_dest_id = customerloc.id
            else:
                location_dest_id = picking_type.default_location_dest_id.id

            res['value'] = {'location_id': location_id,
                            'location_dest_id': location_dest_id,}
        return res

    def _default_location_destination(self):
        # retrieve picking type from context; if none this returns an empty recordset
        picking_type_id = self._context.get('default_picking_type_id')
        picking_type = self.env['stock.picking.type'].browse(picking_type_id)
        return picking_type.default_location_dest_id

    def _default_location_source(self):
        # retrieve picking type from context; if none this returns an empty recordset
        picking_type_id = self._context.get('default_picking_type_id')
        picking_type = self.env['stock.picking.type'].browse(picking_type_id)
        return picking_type.default_location_src_id

    _columns = {
        'name': fields.char('Reference', select=True, states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}, copy=False),
        'origin': fields.char('Source Document', states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}, help="Reference of the document", select=True),
        'backorder_id': fields.many2one('stock.picking', 'Back Order of', states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}, help="If this shipment was split, then this field links to the shipment which contains the already processed part.", select=True, copy=False),
        'note': fields.text('Notes'),
        'move_type': fields.selection([('direct', 'Partial'), ('one', 'All at once')], 'Delivery Method', required=True, states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}, help="It specifies goods to be deliver partially or all at once"),
        'state': fields.function(_state_get, type="selection", copy=False,
            store={
                'stock.picking': (lambda self, cr, uid, ids, ctx: ids, ['move_type', 'launch_pack_operations'], 20),
                'stock.move': (_get_pickings, ['state', 'picking_id', 'partially_available'], 20)},
            selection=[
                ('draft', 'Draft'),
                ('cancel', 'Cancelled'),
                ('waiting', 'Waiting Another Operation'),
                ('confirmed', 'Waiting Availability'),
                ('partially_available', 'Partially Available'),
                ('assigned', 'Available'),
                ('done', 'Done'),
                ], string='Status', readonly=True, select=True, track_visibility='onchange',
            help="""
                * Draft: not confirmed yet and will not be scheduled until confirmed\n
                * Waiting Another Operation: waiting for another move to proceed before it becomes automatically available (e.g. in Make-To-Order flows)\n
                * Waiting Availability: still waiting for the availability of products\n
                * Partially Available: some products are available and reserved\n
                * Ready to Transfer: products reserved, simply waiting for confirmation.\n
                * Transferred: has been processed, can't be modified or cancelled anymore\n
                * Cancelled: has been cancelled, can't be confirmed anymore"""
        ),
        'location_id': fields.many2one('stock.location', required=True, string="Source Location Zone",
                                      default=_default_location_source, readonly=True, states={'draft': [('readonly', False)]}),
        'location_dest_id': fields.many2one('stock.location', required=True,string="Destination Location Zone",
                                           default=_default_location_destination, readonly=True, states={'draft': [('readonly', False)]}),
        'move_lines': fields.one2many('stock.move', 'picking_id', string="Stock Moves", copy=True),
        'move_lines_related': fields.related('move_lines', type='one2many', relation='stock.move', string="Move Lines"),
        'picking_type_id': fields.many2one('stock.picking.type', 'Picking Type', states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}, required=True),
        'picking_type_code': fields.related('picking_type_id', 'code', type='selection', selection=[('incoming', 'Suppliers'), ('outgoing', 'Customers'), ('internal', 'Internal')]),
        'picking_type_entire_packs': fields.related('picking_type_id', 'show_entire_packs', type='boolean'),
        'priority': fields.function(get_min_max_date, multi="min_max_date", fnct_inv=_set_priority, type='selection', selection=procurement.PROCUREMENT_PRIORITIES, string='Priority',
                                    store={'stock.move': (_get_pickings_dates_priority, ['priority', 'picking_id'], 20)}, states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}, select=1, help="Priority for this picking. Setting manually a value here would set it as priority for all the moves",
                                    track_visibility='onchange', required=True),
        'min_date': fields.function(get_min_max_date, multi="min_max_date", fnct_inv=_set_min_date,
                 store={'stock.move': (_get_pickings_dates_priority, ['date_expected', 'picking_id'], 20)}, type='datetime', states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}, string='Scheduled Date', select=1, help="Scheduled time for the first part of the shipment to be processed. Setting manually a value here would set it as expected date for all the stock moves.", track_visibility='onchange'),
        'max_date': fields.function(get_min_max_date, multi="min_max_date",
                 store={'stock.move': (_get_pickings_dates_priority, ['date_expected', 'picking_id'], 20)}, type='datetime', string='Max. Expected Date', select=2, help="Scheduled time for the last part of the shipment to be processed"),
        'date': fields.datetime('Creation Date', help="Creation Date, usually the time of the order", select=True, states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}, track_visibility='onchange'),
        'date_done': fields.datetime('Date of Transfer', help="Completion Date of Transfer", readonly=True, copy=False),
        'quant_reserved_exist': fields.function(_get_quant_reserved_exist, type='boolean', string='Has quants already reserved', help='Check the existance of quants linked to this picking'),
        'partner_id': fields.many2one('res.partner', 'Partner', states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}),
        'company_id': fields.many2one('res.company', 'Company', required=True, select=True, states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}),
        'pack_operation_ids': fields.one2many('stock.pack.operation', 'picking_id', states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}, string='Related Packing Operations'),
        'pack_operation_product_ids': fields.one2many('stock.pack.operation', 'picking_id', states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}, domain=[('product_id', '!=', False)], string='Non pack'),
        'pack_operation_pack_ids': fields.one2many('stock.pack.operation', 'picking_id', states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}, domain=[('product_id', '=', False)], string='Pack'),
        # technical field for attrs in view
        'pack_operation_exist': fields.function(_get_pack_operation_exist, type='boolean', string='Has Pack Operations', help='Check the existance of pack operation on the picking'),
        'owner_id': fields.many2one('res.partner', 'Owner', states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}, help="Default Owner"),
        'printed': fields.boolean('Printed'),
        # Used to search on pickings
        'product_id': fields.related('move_lines', 'product_id', type='many2one', relation='product.product', string='Product'),
        'recompute_pack_op': fields.boolean('Recompute pack operation?', help='True if reserved quants changed, which mean we might need to recompute the package operations', copy=False),
        'group_id': fields.related('move_lines', 'group_id', type='many2one', relation='procurement.group', string='Procurement Group', readonly=True,
              store={
                  'stock.picking': (lambda self, cr, uid, ids, ctx: ids, ['move_lines'], 10),
                  'stock.move': (_get_pickings, ['group_id', 'picking_id'], 10),
              }),
        'launch_pack_operations': fields.boolean("Launch Pack Operations", copy=False),
    }

    _defaults = {
        'name': '/',
        'state': 'draft',
        'move_type': 'direct',
        'printed': False,
        'priority': '1',  # normal
        'date': fields.datetime.now,
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'stock.picking', context=c),
        'recompute_pack_op': False,
        'launch_pack_operations': False,
    }
    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)', 'Reference must be unique per company!'),
    ]

    def do_print_picking(self, cr, uid, ids, context=None):
        '''This function prints the picking list'''
        context = dict(context or {}, active_ids=ids)
        self.write(cr, uid, ids, {'printed': True}, context=context)
        return self.pool.get("report").get_action(cr, uid, ids, 'stock.report_picking', context=context)

    def launch_packops(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'launch_pack_operations': True}, context=context)

    def action_confirm(self, cr, uid, ids, context=None):
        todo = []
        todo_force_assign = []
        for picking in self.browse(cr, uid, ids, context=context):
            if not picking.move_lines:
                self.launch_packops(cr, uid, [picking.id], context=context)
            if picking.location_id.usage in ('supplier', 'inventory', 'production'):
                todo_force_assign.append(picking.id)
            for r in picking.move_lines:
                if r.state == 'draft':
                    todo.append(r.id)
        if len(todo):
            self.pool.get('stock.move').action_confirm(cr, uid, todo, context=context)

        if todo_force_assign:
            self.force_assign(cr, uid, todo_force_assign, context=context)
        return True

    def action_assign(self, cr, uid, ids, context=None):
        """ Check availability of picking moves.
        This has the effect of changing the state and reserve quants on available moves, and may
        also impact the state of the picking as it is computed based on move's states.
        @return: True
        """
        for pick in self.browse(cr, uid, ids, context=context):
            if pick.state == 'draft':
                self.action_confirm(cr, uid, [pick.id], context=context)
            #skip the moves that don't need to be checked
            move_ids = [x.id for x in pick.move_lines if x.state not in ('draft', 'cancel', 'done')]
            if not move_ids:
                raise UserError(_('Nothing to check the availability for.'))
            self.pool.get('stock.move').action_assign(cr, uid, move_ids, context=context)
        return True

    def force_assign(self, cr, uid, ids, context=None):
        """ Changes state of picking to available if moves are confirmed or waiting.
        @return: True
        """
        pickings = self.browse(cr, uid, ids, context=context)
        for pick in pickings:
            move_ids = [x.id for x in pick.move_lines if x.state in ['confirmed', 'waiting']]
            self.pool.get('stock.move').force_assign(cr, uid, move_ids, context=context)
        return True

    def action_cancel(self, cr, uid, ids, context=None):
        for pick in self.browse(cr, uid, ids, context=context):
            ids2 = [move.id for move in pick.move_lines]
            self.pool.get('stock.move').action_cancel(cr, uid, ids2, context)
        return True

    def action_done(self, cr, uid, ids, context=None):
        """Changes picking state to done by processing the Stock Moves of the Picking

        Normally that happens when the button "Done" is pressed on a Picking view.
        @return: True
        """
        for pick in self.browse(cr, uid, ids, context=context):
            todo = []
            for move in pick.move_lines:
                if move.state == 'draft':
                    todo.extend(self.pool.get('stock.move').action_confirm(cr, uid, [move.id], context=context))
                elif move.state in ('assigned', 'confirmed'):
                    todo.append(move.id)
            if len(todo):
                self.pool.get('stock.move').action_done(cr, uid, todo, context=context)
        return True

    def unlink(self, cr, uid, ids, context=None):
        #on picking deletion, cancel its move then unlink them too
        move_obj = self.pool.get('stock.move')
        context = context or {}
        for pick in self.browse(cr, uid, ids, context=context):
            move_ids = [move.id for move in pick.move_lines]
            move_obj.action_cancel(cr, uid, move_ids, context=context)
            move_obj.unlink(cr, uid, move_ids, context=context)
        return super(stock_picking, self).unlink(cr, uid, ids, context=context)

    def _create_backorder(self, cr, uid, picking, backorder_moves=[], context=None):
        """ Move all non-done lines into a new backorder picking. If the key 'do_only_split' is given in the context, then move all lines not in context.get('split', []) instead of all non-done lines.
        """
        if not backorder_moves:
            backorder_moves = picking.move_lines
        backorder_move_ids = [x.id for x in backorder_moves if x.state not in ('done', 'cancel')]
        if 'do_only_split' in context and context['do_only_split']:
            backorder_move_ids = [x.id for x in backorder_moves if x.id not in context.get('split', [])]

        if backorder_move_ids:
            backorder_id = self.copy(cr, uid, picking.id, {
                'name': '/',
                'move_lines': [],
                'pack_operation_ids': [],
                'backorder_id': picking.id,
            })
            backorder = self.browse(cr, uid, backorder_id, context=context)
            self.message_post(cr, uid, picking.id, body=_("Back order <em>%s</em> <b>created</b>.") % (backorder.name), context=context)
            move_obj = self.pool.get("stock.move")
            move_obj.write(cr, uid, backorder_move_ids, {'picking_id': backorder_id}, context=context)

            if not picking.date_done:
                self.write(cr, uid, [picking.id], {'date_done': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)}, context=context)
            self.action_confirm(cr, uid, [backorder_id], context=context)
            self.action_assign(cr, uid, [backorder_id], context=context)
            return backorder_id
        return False

    @api.cr_uid_ids_context
    def recheck_availability(self, cr, uid, picking_ids, context=None):
        self.action_assign(cr, uid, picking_ids, context=context)
        self.do_prepare_partial(cr, uid, picking_ids, context=context)

    def _get_top_level_packages(self, cr, uid, quants_suggested_locations, context=None):
        """This method searches for the higher level packages that can be moved as a single operation, given a list of quants
           to move and their suggested destination, and returns the list of matching packages.
        """
        # Try to find as much as possible top-level packages that can be moved
        pack_obj = self.pool.get("stock.quant.package")
        quant_obj = self.pool.get("stock.quant")
        top_lvl_packages = set()
        quants_to_compare = quants_suggested_locations.keys()
        for pack in list(set([x.package_id for x in quants_suggested_locations.keys() if x and x.package_id])):
            loop = True
            test_pack = pack
            good_pack = False
            pack_destination = False
            while loop:
                pack_quants = pack_obj.get_content(cr, uid, [test_pack.id], context=context)
                all_in = True
                for quant in quant_obj.browse(cr, uid, pack_quants, context=context):
                    # If the quant is not in the quants to compare and not in the common location
                    if not quant in quants_to_compare:
                        all_in = False
                        break
                    else:
                        #if putaway strat apply, the destination location of each quant may be different (and thus the package should not be taken as a single operation)
                        if not pack_destination:
                            pack_destination = quants_suggested_locations[quant]
                        elif pack_destination != quants_suggested_locations[quant]:
                            all_in = False
                            break
                if all_in:
                    good_pack = test_pack
                    if test_pack.parent_id:
                        test_pack = test_pack.parent_id
                    else:
                        #stop the loop when there's no parent package anymore
                        loop = False
                else:
                    #stop the loop when the package test_pack is not totally reserved for moves of this picking
                    #(some quants may be reserved for other picking or not reserved at all)
                    loop = False
            if good_pack:
                top_lvl_packages.add(good_pack)
        return list(top_lvl_packages)

    def _prepare_pack_ops(self, cr, uid, picking, quants, forced_qties, context=None):
        """ returns a list of dict, ready to be used in create() of stock.pack.operation.

        :param picking: browse record (stock.picking)
        :param quants: browse record list (stock.quant). List of quants associated to the picking
        :param forced_qties: dictionary showing for each product (keys) its corresponding quantity (value) that is not covered by the quants associated to the picking
        """
        def _picking_putaway_apply(product):
            location = False
            # Search putaway strategy
            if product_putaway_strats.get(product.id):
                location = product_putaway_strats[product.id]
            else:
                location = self.pool.get('stock.location').get_putaway_strategy(cr, uid, picking.location_dest_id, product, context=context)
                product_putaway_strats[product.id] = location
            return location or picking.location_dest_id.id

        # If we encounter an UoM that is smaller than the default UoM or the one already chosen, use the new one instead.
        product_uom = {} # Determines UoM used in pack operations
        location_dest_id = None
        location_id = None
        for move in [x for x in picking.move_lines if x.state not in ('done', 'cancel')]:
            if not product_uom.get(move.product_id.id):
                product_uom[move.product_id.id] = move.product_id.uom_id
            if move.product_uom.id != move.product_id.uom_id.id and move.product_uom.factor > product_uom[move.product_id.id].factor:
                product_uom[move.product_id.id] = move.product_uom
            if not move.scrapped:
                if location_dest_id and move.location_dest_id.id != location_dest_id:
                    raise UserError(_('The destination location must be the same for all the moves of the picking.'))
                location_dest_id = move.location_dest_id.id
                if location_id and move.location_id.id != location_id:
                    raise UserError(_('The source location must be the same for all the moves of the picking.'))
                location_id = move.location_id.id

        pack_obj = self.pool.get("stock.quant.package")
        quant_obj = self.pool.get("stock.quant")
        vals = []
        qtys_grouped = {}
        lots_grouped = {}
        #for each quant of the picking, find the suggested location
        quants_suggested_locations = {}
        product_putaway_strats = {}
        for quant in quants:
            if quant.qty <= 0:
                continue
            suggested_location_id = _picking_putaway_apply(quant.product_id)
            quants_suggested_locations[quant] = suggested_location_id

        #find the packages we can movei as a whole
        top_lvl_packages = self._get_top_level_packages(cr, uid, quants_suggested_locations, context=context)
        # and then create pack operations for the top-level packages found
        for pack in top_lvl_packages:
            pack_quant_ids = pack_obj.get_content(cr, uid, [pack.id], context=context)
            pack_quants = quant_obj.browse(cr, uid, pack_quant_ids, context=context)
            vals.append({
                    'picking_id': picking.id,
                    'package_id': pack.id,
                    'product_qty': 1.0,
                    'location_id': pack.location_id.id,
                    'location_dest_id': quants_suggested_locations[pack_quants[0]],
                    'owner_id': pack.owner_id.id,
                })
            #remove the quants inside the package so that they are excluded from the rest of the computation
            for quant in pack_quants:
                del quants_suggested_locations[quant]
        # Go through all remaining reserved quants and group by product, package, owner, source location and dest location
        # Lots will go into pack operation lot object
        for quant, dest_location_id in quants_suggested_locations.items():
            key = (quant.product_id.id, quant.package_id.id, quant.owner_id.id, quant.location_id.id, dest_location_id)
            if qtys_grouped.get(key):
                qtys_grouped[key] += quant.qty
            else:
                qtys_grouped[key] = quant.qty
            if quant.product_id.tracking != 'none' and quant.lot_id:
                lots_grouped.setdefault(key, {}).setdefault(quant.lot_id.id, 0.0)
                lots_grouped[key][quant.lot_id.id] += quant.qty

        # Do the same for the forced quantities (in cases of force_assign or incomming shipment for example)
        for product, qty in forced_qties.items():
            if qty <= 0:
                continue
            suggested_location_id = _picking_putaway_apply(product)
            key = (product.id, False, picking.owner_id.id, picking.location_id.id, suggested_location_id)
            if qtys_grouped.get(key):
                qtys_grouped[key] += qty
            else:
                qtys_grouped[key] = qty

        # Create the necessary operations for the grouped quants and remaining qtys
        uom_obj = self.pool.get('product.uom')
        prevals = {}
        for key, qty in qtys_grouped.items():
            product = self.pool.get("product.product").browse(cr, uid, key[0], context=context)
            uom_id = product.uom_id.id
            qty_uom = qty
            if product_uom.get(key[0]):
                uom_id = product_uom[key[0]].id
                qty_uom = uom_obj._compute_qty(cr, uid, product.uom_id.id, qty, uom_id)
            pack_lot_ids = []
            if lots_grouped.get(key):
                for lot in lots_grouped[key].keys():
                    pack_lot_ids += [(0, 0, {'lot_id': lot, 'qty': 0.0, 'qty_todo': lots_grouped[key][lot]})]
            val_dict = {
                'picking_id': picking.id,
                'product_qty': qty_uom,
                'product_id': key[0],
                'package_id': key[1],
                'owner_id': key[2],
                'location_id': key[3],
                'location_dest_id': key[4],
                'product_uom_id': uom_id,
                'pack_lot_ids': pack_lot_ids,
            }
            if key[0] in prevals:
                prevals[key[0]].append(val_dict)
            else:
                prevals[key[0]] = [val_dict]
        # prevals var holds the operations in order to create them in the same order than the picking stock moves if possible
        processed_products = set()
        for move in [x for x in picking.move_lines if x.state not in ('done', 'cancel')]:
            if move.product_id.id not in processed_products:
                vals += prevals.get(move.product_id.id, [])
                processed_products.add(move.product_id.id)
        return vals

    @api.cr_uid_ids_context
    def do_prepare_partial(self, cr, uid, picking_ids, context=None):
        context = context or {}
        pack_operation_obj = self.pool.get('stock.pack.operation')

        #get list of existing operations and delete them
        existing_package_ids = pack_operation_obj.search(cr, uid, [('picking_id', 'in', picking_ids)], context=context)
        if existing_package_ids:
            pack_operation_obj.unlink(cr, uid, existing_package_ids, context)
        for picking in self.browse(cr, uid, picking_ids, context=context):
            forced_qties = {}  # Quantity remaining after calculating reserved quants
            picking_quants = []
            #Calculate packages, reserved quants, qtys of this picking's moves
            for move in picking.move_lines:
                if move.state not in ('assigned', 'confirmed', 'waiting'):
                    continue
                move_quants = move.reserved_quant_ids
                picking_quants += move_quants
                forced_qty = (move.state == 'assigned') and move.product_qty - sum([x.qty for x in move_quants]) or 0
                #if we used force_assign() on the move, or if the move is incoming, forced_qty > 0
                if float_compare(forced_qty, 0, precision_rounding=move.product_id.uom_id.rounding) > 0:
                    if forced_qties.get(move.product_id):
                        forced_qties[move.product_id] += forced_qty
                    else:
                        forced_qties[move.product_id] = forced_qty
            for vals in self._prepare_pack_ops(cr, uid, picking, picking_quants, forced_qties, context=context):
                vals['fresh_record'] = False
                pack_operation_obj.create(cr, uid, vals, context=context)
        #recompute the remaining quantities all at once
        self.do_recompute_remaining_quantities(cr, uid, picking_ids, context=context)
        self.write(cr, uid, picking_ids, {'recompute_pack_op': False}, context=context)

    @api.cr_uid_ids_context
    def do_unreserve(self, cr, uid, picking_ids, context=None):
        """
          Will remove all quants for picking in picking_ids
        """
        moves_to_unreserve = []
        pack_line_to_unreserve = []
        for picking in self.browse(cr, uid, picking_ids, context=context):
            moves_to_unreserve += [m.id for m in picking.move_lines if m.state not in ('done', 'cancel')]
            pack_line_to_unreserve += [p.id for p in picking.pack_operation_ids]
        if moves_to_unreserve:
            if pack_line_to_unreserve:
                self.pool.get('stock.pack.operation').unlink(cr, uid, pack_line_to_unreserve, context=context)
            self.pool.get('stock.move').do_unreserve(cr, uid, moves_to_unreserve, context=context)

    def recompute_remaining_qty(self, cr, uid, picking, done_qtys=False, context=None):
        def _create_link_for_index(operation_id, index, product_id, qty_to_assign, quant_id=False):
            move_dict = prod2move_ids[product_id][index]
            qty_on_link = min(move_dict['remaining_qty'], qty_to_assign)
            self.pool.get('stock.move.operation.link').create(cr, uid, {'move_id': move_dict['move'].id, 'operation_id': operation_id, 'qty': qty_on_link, 'reserved_quant_id': quant_id}, context=context)
            if move_dict['remaining_qty'] == qty_on_link:
                prod2move_ids[product_id].pop(index)
            else:
                move_dict['remaining_qty'] -= qty_on_link
            return qty_on_link

        def _create_link_for_quant(operation_id, quant, qty):
            """create a link for given operation and reserved move of given quant, for the max quantity possible, and returns this quantity"""
            if not quant.reservation_id.id:
                return _create_link_for_product(operation_id, quant.product_id.id, qty)
            qty_on_link = 0
            for i in range(0, len(prod2move_ids[quant.product_id.id])):
                if prod2move_ids[quant.product_id.id][i]['move'].id != quant.reservation_id.id:
                    continue
                qty_on_link = _create_link_for_index(operation_id, i, quant.product_id.id, qty, quant_id=quant.id)
                break
            return qty_on_link

        def _create_link_for_product(operation_id, product_id, qty):
            '''method that creates the link between a given operation and move(s) of given product, for the given quantity.
            Returns True if it was possible to create links for the requested quantity (False if there was not enough quantity on stock moves)'''
            qty_to_assign = qty
            prod_obj = self.pool.get("product.product")
            product = prod_obj.browse(cr, uid, product_id)
            rounding = product.uom_id.rounding
            qtyassign_cmp = float_compare(qty_to_assign, 0.0, precision_rounding=rounding)
            if prod2move_ids.get(product_id):
                while prod2move_ids[product_id] and qtyassign_cmp > 0:
                    qty_on_link = _create_link_for_index(operation_id, 0, product_id, qty_to_assign, quant_id=False)
                    qty_to_assign -= qty_on_link
                    qtyassign_cmp = float_compare(qty_to_assign, 0.0, precision_rounding=rounding)
            return qtyassign_cmp == 0

        uom_obj = self.pool.get('product.uom')
        package_obj = self.pool.get('stock.quant.package')
        quant_obj = self.pool.get('stock.quant')
        link_obj = self.pool.get('stock.move.operation.link')
        quants_in_package_done = set()
        prod2move_ids = {}
        still_to_do = []
        #make a dictionary giving for each product, the moves and related quantity that can be used in operation links
        for move in [x for x in picking.move_lines if x.state not in ('done', 'cancel')]:
            if not prod2move_ids.get(move.product_id.id):
                prod2move_ids[move.product_id.id] = [{'move': move, 'remaining_qty': move.product_qty}]
            else:
                prod2move_ids[move.product_id.id].append({'move': move, 'remaining_qty': move.product_qty})

        need_rereserve = False
        #sort the operations in order to give higher priority to those with a package, then a serial number
        operations = picking.pack_operation_ids
        operations = sorted(operations, key=lambda x: ((x.package_id and not x.product_id) and -4 or 0) + (x.package_id and -2 or 0) + (x.pack_lot_ids and -1 or 0))
        #delete existing operations to start again from scratch
        links = link_obj.search(cr, uid, [('operation_id', 'in', [x.id for x in operations])], context=context)
        if links:
            link_obj.unlink(cr, uid, links, context=context)
        #1) first, try to create links when quants can be identified without any doubt
        for ops in operations:
            lot_qty = {}
            for packlot in ops.pack_lot_ids:
                lot_qty[packlot.lot_id.id] = uom_obj._compute_qty(cr, uid, ops.product_uom_id.id, packlot.qty, ops.product_id.uom_id.id)
            #for each operation, create the links with the stock move by seeking on the matching reserved quants,
            #and deffer the operation if there is some ambiguity on the move to select
            if ops.package_id and not ops.product_id and (not done_qtys or ops.qty_done):
                #entire package
                quant_ids = package_obj.get_content(cr, uid, [ops.package_id.id], context=context)
                for quant in quant_obj.browse(cr, uid, quant_ids, context=context):
                    remaining_qty_on_quant = quant.qty
                    if quant.reservation_id:
                        #avoid quants being counted twice
                        quants_in_package_done.add(quant.id)
                        qty_on_link = _create_link_for_quant(ops.id, quant, quant.qty)
                        remaining_qty_on_quant -= qty_on_link
                    if remaining_qty_on_quant:
                        still_to_do.append((ops, quant.product_id.id, remaining_qty_on_quant))
                        need_rereserve = True
            elif ops.product_id.id:
                #Check moves with same product
                product_qty = ops.qty_done if done_qtys else ops.product_qty
                qty_to_assign = uom_obj._compute_qty_obj(cr, uid, ops.product_uom_id, product_qty, ops.product_id.uom_id, context=context)
                for move_dict in prod2move_ids.get(ops.product_id.id, []):
                    move = move_dict['move']
                    for quant in move.reserved_quant_ids:
                        if not qty_to_assign > 0:
                            break
                        if quant.id in quants_in_package_done:
                            continue

                        #check if the quant is matching the operation details
                        if ops.package_id:
                            flag = quant.package_id and bool(package_obj.search(cr, uid, [('id', 'child_of', [ops.package_id.id])], context=context)) or False
                        else:
                            flag = not quant.package_id.id
                        flag = flag and (ops.owner_id.id == quant.owner_id.id)
                        if flag:
                            if not lot_qty:
                                max_qty_on_link = min(quant.qty, qty_to_assign)
                                qty_on_link = _create_link_for_quant(ops.id, quant, max_qty_on_link)
                                qty_to_assign -= qty_on_link
                            else:
                                if lot_qty.get(quant.lot_id.id): #if there is still some qty left
                                    max_qty_on_link = min(quant.qty, qty_to_assign, lot_qty[quant.lot_id.id])
                                    qty_on_link = _create_link_for_quant(ops.id, quant, max_qty_on_link)
                                    qty_to_assign -= qty_on_link
                                    lot_qty[quant.lot_id.id] -= qty_on_link

                qty_assign_cmp = float_compare(qty_to_assign, 0, precision_rounding=ops.product_id.uom_id.rounding)
                if qty_assign_cmp > 0:
                    #qty reserved is less than qty put in operations. We need to create a link but it's deferred after we processed
                    #all the quants (because they leave no choice on their related move and needs to be processed with higher priority)
                    still_to_do += [(ops, ops.product_id.id, qty_to_assign)]
                    need_rereserve = True

        #2) then, process the remaining part
        all_op_processed = True
        for ops, product_id, remaining_qty in still_to_do:
            all_op_processed = _create_link_for_product(ops.id, product_id, remaining_qty) and all_op_processed
        return (need_rereserve, all_op_processed)

    def picking_recompute_remaining_quantities(self, cr, uid, picking, done_qtys=False, context=None):
        need_rereserve = False
        all_op_processed = True
        if picking.pack_operation_ids:
            need_rereserve, all_op_processed = self.recompute_remaining_qty(cr, uid, picking, done_qtys=done_qtys, context=context)
        return need_rereserve, all_op_processed

    @api.cr_uid_ids_context
    def do_recompute_remaining_quantities(self, cr, uid, picking_ids, done_qtys=False, context=None):
        for picking in self.browse(cr, uid, picking_ids, context=context):
            if picking.pack_operation_ids:
                self.recompute_remaining_qty(cr, uid, picking, done_qtys=done_qtys, context=context)

    def _prepare_values_extra_move(self, cr, uid, op, product, remaining_qty, context=None):
        """
        Creates an extra move when there is no corresponding original move to be copied
        """
        uom_obj = self.pool.get("product.uom")
        uom_id = product.uom_id.id
        qty = remaining_qty
        if op.product_id and op.product_uom_id and op.product_uom_id.id != product.uom_id.id:
            if op.product_uom_id.factor > product.uom_id.factor: #If the pack operation's is a smaller unit
                uom_id = op.product_uom_id.id
                #HALF-UP rounding as only rounding errors will be because of propagation of error from default UoM
                qty = uom_obj._compute_qty_obj(cr, uid, product.uom_id, remaining_qty, op.product_uom_id, rounding_method='HALF-UP')
        picking = op.picking_id
        ref = product.default_code
        name = '[' + ref + ']' + ' ' + product.name if ref else product.name
        proc_id = False
        for m in op.linked_move_operation_ids:
            if m.move_id.procurement_id:
                proc_id = m.move_id.procurement_id.id
                break
        res = {
            'picking_id': picking.id,
            'location_id': picking.location_id.id,
            'location_dest_id': picking.location_dest_id.id,
            'product_id': product.id,
            'procurement_id': proc_id,
            'product_uom': uom_id,
            'product_uom_qty': qty,
            'name': _('Extra Move: ') + name,
            'state': 'draft',
            'restrict_partner_id': op.owner_id,
            'group_id': picking.group_id.id,
            }
        return res

    def _create_extra_moves(self, cr, uid, picking, context=None):
        '''This function creates move lines on a picking, at the time of do_transfer, based on
        unexpected product transfers (or exceeding quantities) found in the pack operations.
        '''
        move_obj = self.pool.get('stock.move')
        operation_obj = self.pool.get('stock.pack.operation')
        moves = []
        for op in picking.pack_operation_ids:
            for product, remaining_qty in operation_obj._get_remaining_prod_quantities(cr, uid, op, context=context).items():
                if float_compare(remaining_qty, 0, precision_rounding=product.uom_id.rounding) > 0:
                    vals = self._prepare_values_extra_move(cr, uid, op, product, remaining_qty, context=context)
                    moves.append(move_obj.create(cr, uid, vals, context=context))
        if moves:
            move_obj.action_confirm(cr, uid, moves, context=context)
        return moves

    def rereserve_pick(self, cr, uid, ids, context=None):
        """
        This can be used to provide a button that rereserves taking into account the existing pack operations
        """
        for pick in self.browse(cr, uid, ids, context=context):
            self.rereserve_quants(cr, uid, pick, move_ids = [x.id for x in pick.move_lines
                                                             if x.state not in ('done', 'cancel')], context=context)

    def rereserve_quants(self, cr, uid, picking, move_ids=[], context=None):
        """ Unreserve quants then try to reassign quants."""
        stock_move_obj = self.pool.get('stock.move')
        if not move_ids:
            self.do_unreserve(cr, uid, [picking.id], context=context)
            self.action_assign(cr, uid, [picking.id], context=context)
        else:
            stock_move_obj.do_unreserve(cr, uid, move_ids, context=context)
            stock_move_obj.action_assign(cr, uid, move_ids, no_prepare=True, context=context)

    def do_new_transfer(self, cr, uid, ids, context=None):
        pack_op_obj = self.pool['stock.pack.operation']
        data_obj = self.pool['ir.model.data']
        for pick in self.browse(cr, uid, ids, context=context):
            to_delete = []
            if not pick.move_lines and not pick.pack_operation_ids:
                raise UserError(_('Please create some Initial Demand or Mark as Todo and create some Operations. '))
            # In draft or with no pack operations edited yet, ask if we can just do everything
            if pick.state == 'draft' or all([x.qty_done == 0.0 for x in pick.pack_operation_ids]):
                # If no lots when needed, raise error
                picking_type = pick.picking_type_id
                if (picking_type.use_create_lots or picking_type.use_existing_lots):
                    for pack in pick.pack_operation_ids:
                        if pack.product_id and pack.product_id.tracking != 'none':
                            raise UserError(_('Some products require lots, so you need to specify those first!'))

                view = data_obj.xmlid_to_res_id(cr, uid, 'stock.view_immediate_transfer')
                wiz_id = self.pool['stock.immediate.transfer'].create(cr, uid, {'pick_id': pick.id}, context=context)
                return {
                     'name': _('Immediate Transfer?'),
                     'type': 'ir.actions.act_window',
                     'view_type': 'form',
                     'view_mode': 'form',
                     'res_model': 'stock.immediate.transfer',
                     'views': [(view, 'form')],
                     'view_id': view,
                     'target': 'new',
                     'res_id': wiz_id,
                     'context': context,
                 }

            # Check backorder should check for other barcodes
            if self.check_backorder(cr, uid, pick, context=context):
                view = data_obj.xmlid_to_res_id(cr, uid, 'stock.view_backorder_confirmation')
                wiz_id = self.pool['stock.backorder.confirmation'].create(cr, uid, {'pick_id': pick.id}, context=context)
                return {
                         'name': _('Create Backorder?'),
                         'type': 'ir.actions.act_window',
                         'view_type': 'form',
                         'view_mode': 'form',
                         'res_model': 'stock.backorder.confirmation',
                         'views': [(view, 'form')],
                         'view_id': view,
                         'target': 'new',
                         'res_id': wiz_id,
                         'context': context,
                     }
            for operation in pick.pack_operation_ids:
                if operation.qty_done < 0:
                    raise UserError(_('No negative quantities allowed'))
                if operation.qty_done > 0:
                    pack_op_obj.write(cr, uid, operation.id, {'product_qty': operation.qty_done}, context=context)
                else:
                    to_delete.append(operation.id)
            if to_delete:
                pack_op_obj.unlink(cr, uid, to_delete, context=context)
        self.do_transfer(cr, uid, ids, context=context)
        return

    def check_backorder(self, cr, uid, picking, context=None):
        need_rereserve, all_op_processed = self.picking_recompute_remaining_quantities(cr, uid, picking, done_qtys=True, context=context)
        for move in picking.move_lines:
            if float_compare(move.remaining_qty, 0, precision_rounding = move.product_id.uom_id.rounding) != 0:
                return True
        return False

    def create_lots_for_picking(self, cr, uid, ids, context=None):
        lot_obj = self.pool['stock.production.lot']
        opslot_obj = self.pool['stock.pack.operation.lot']
        to_unlink = []
        for picking in self.browse(cr, uid, ids, context=context):
            for ops in picking.pack_operation_ids:
                for opslot in ops.pack_lot_ids:
                    if not opslot.lot_id:
                        lot_id = lot_obj.create(cr, uid, {'name': opslot.lot_name, 'product_id': ops.product_id.id}, context=context)
                        opslot_obj.write(cr, uid, [opslot.id], {'lot_id':lot_id}, context=context)
                #Unlink pack operations where qty = 0
                to_unlink += [x.id for x in ops.pack_lot_ids if x.qty == 0.0]
        opslot_obj.unlink(cr, uid, to_unlink, context=context)

    def do_transfer(self, cr, uid, ids, context=None):
        """
            If no pack operation, we do simple action_done of the picking
            Otherwise, do the pack operations
        """
        if not context:
            context = {}

        stock_move_obj = self.pool.get('stock.move')
        self.create_lots_for_picking(cr, uid, ids, context=context)
        for picking in self.browse(cr, uid, ids, context=context):
            if not picking.pack_operation_ids:
                self.action_done(cr, uid, [picking.id], context=context)
                continue
            else:
                need_rereserve, all_op_processed = self.picking_recompute_remaining_quantities(cr, uid, picking, context=context)
                #create extra moves in the picking (unexpected product moves coming from pack operations)
                todo_move_ids = []
                if not all_op_processed:
                    todo_move_ids += self._create_extra_moves(cr, uid, picking, context=context)

                #split move lines if needed
                toassign_move_ids = []
                for move in picking.move_lines:
                    remaining_qty = move.remaining_qty
                    if move.state in ('done', 'cancel'):
                        #ignore stock moves cancelled or already done
                        continue
                    elif move.state == 'draft':
                        toassign_move_ids.append(move.id)
                    if float_compare(remaining_qty, 0,  precision_rounding = move.product_id.uom_id.rounding) == 0:
                        if move.state in ('draft', 'assigned', 'confirmed'):
                            todo_move_ids.append(move.id)
                    elif float_compare(remaining_qty,0, precision_rounding = move.product_id.uom_id.rounding) > 0 and \
                                float_compare(remaining_qty, move.product_qty, precision_rounding = move.product_id.uom_id.rounding) < 0:
                        new_move = stock_move_obj.split(cr, uid, move, remaining_qty, context=context)
                        todo_move_ids.append(move.id)
                        #Assign move as it was assigned before
                        toassign_move_ids.append(new_move)
                todo_move_ids = list(set(todo_move_ids))
                if need_rereserve or not all_op_processed: 
                    if not picking.location_id.usage in ("supplier", "production", "inventory"):
                        self.rereserve_quants(cr, uid, picking, move_ids=todo_move_ids, context=context)
                    self.do_recompute_remaining_quantities(cr, uid, [picking.id], context=context)
                if todo_move_ids and not context.get('do_only_split'):
                    self.pool.get('stock.move').action_done(cr, uid, todo_move_ids, context=context)
                elif context.get('do_only_split'):
                    context = dict(context, split=todo_move_ids)
            self._create_backorder(cr, uid, picking, context=context)
        return True

    @api.cr_uid_ids_context
    def do_split(self, cr, uid, picking_ids, context=None):
        """ just split the picking (create a backorder) without making it 'done' """
        if context is None:
            context = {}
        ctx = context.copy()
        ctx['do_only_split'] = True
        return self.do_transfer(cr, uid, picking_ids, context=ctx)

    def put_in_pack(self, cr, uid, ids, context=None):
        stock_move_obj = self.pool["stock.move"]
        stock_operation_obj = self.pool["stock.pack.operation"]
        package_obj = self.pool["stock.quant.package"]
        package_id = False
        for pick in self.browse(cr, uid, ids, context=context):
            operations = [x for x in pick.pack_operation_ids if x.qty_done > 0 and (not x.result_package_id)]
            pack_operation_ids = []
            for operation in operations:
                #If we haven't done all qty in operation, we have to split into 2 operation
                op = operation
                if operation.qty_done < operation.product_qty:
                    new_operation = stock_operation_obj.copy(cr, uid, operation.id, {'product_qty': operation.qty_done,'qty_done': operation.qty_done}, context=context)

                    stock_operation_obj.write(cr, uid, operation.id, {'product_qty': operation.product_qty - operation.qty_done,'qty_done': 0}, context=context)
                    if operation.pack_lot_ids:
                        packlots_transfer = [(4, x.id) for x in operation.pack_lot_ids]
                        stock_operation_obj.write(cr, uid, [new_operation], {'pack_lot_ids': packlots_transfer}, context=context)

                    op = stock_operation_obj.browse(cr, uid, new_operation, context=context)
                pack_operation_ids.append(op.id)
            if operations:
                stock_operation_obj.check_tracking(cr, uid, pack_operation_ids, context=context)
                package_id = package_obj.create(cr, uid, {}, context=context)
                stock_operation_obj.write(cr, uid, pack_operation_ids, {'result_package_id': package_id}, context=context)
            else:
                raise UserError(_('Please process some quantities to put in the pack first!'))
        return package_id


class stock_production_lot(osv.osv):
    _name = 'stock.production.lot'
    _inherit = ['mail.thread']
    _description = 'Lot/Serial'
    _columns = {
        'name': fields.char('Serial Number', required=True, help="Unique Serial Number"),
        'ref': fields.char('Internal Reference', help="Internal reference number in case it differs from the manufacturer's serial number"),
        'product_id': fields.many2one('product.product', 'Product', required=True, domain=[('type', 'in', ['product', 'consu'])]),
        'quant_ids': fields.one2many('stock.quant', 'lot_id', 'Quants', readonly=True),
        'create_date': fields.datetime('Creation Date'),
    }
    _defaults = {
        'name': lambda x, y, z, c: x.pool.get('ir.sequence').next_by_code(y, z, 'stock.lot.serial'),
        'product_id': lambda x, y, z, c: c.get('product_id', False),
    }
    _sql_constraints = [
        ('name_ref_uniq', 'unique (name, product_id)', 'The combination of serial number and product must be unique !'),
    ]

    def action_traceability(self, cr, uid, ids, context=None):
        """ It traces the information of lots
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: List of IDs selected
        @param context: A standard dictionary
        @return: A dictionary of values
        """
        quant_obj = self.pool.get("stock.quant")
        quants = quant_obj.search(cr, uid, [('lot_id', 'in', ids)], context=context)
        moves = set()
        for quant in quant_obj.browse(cr, uid, quants, context=context):
            moves |= {move.id for move in quant.history_ids}
        if moves:
            return {
                'domain': "[('id','in',[" + ','.join(map(str, list(moves))) + "])]",
                'name': _('Traceability'),
                'view_mode': 'tree,form',
                'view_type': 'form',
                'context': {'tree_view_ref': 'stock.view_move_tree'},
                'res_model': 'stock.move',
                'type': 'ir.actions.act_window',
                    }
        return False


# ----------------------------------------------------
# Move
# ----------------------------------------------------

class stock_move(osv.osv):
    _name = "stock.move"
    _description = "Stock Move"
    _order = 'picking_id, sequence, id'
    _log_create = False

    def get_price_unit(self, cr, uid, move, context=None):
        """ Returns the unit price to store on the quant """
        return move.price_unit or move.product_id.standard_price

    def name_get(self, cr, uid, ids, context=None):
        res = []
        for line in self.browse(cr, uid, ids, context=context):
            name = line.location_id.name + ' > ' + line.location_dest_id.name
            if line.product_id.code:
                name = line.product_id.code + ': ' + name
            if line.picking_id.origin:
                name = line.picking_id.origin + '/ ' + name
            res.append((line.id, name))
        return res

    def _quantity_normalize(self, cr, uid, ids, name, args, context=None):
        uom_obj = self.pool.get('product.uom')
        res = {}
        for m in self.browse(cr, uid, ids, context=context):
            res[m.id] = uom_obj._compute_qty_obj(cr, uid, m.product_uom, m.product_uom_qty, m.product_id.uom_id, context=context)
        return res

    def _get_remaining_qty(self, cr, uid, ids, field_name, args, context=None):
        uom_obj = self.pool.get('product.uom')
        res = {}
        for move in self.browse(cr, uid, ids, context=context):
            qty = move.product_qty
            for record in move.linked_move_operation_ids:
                qty -= record.qty
            # Keeping in product default UoM
            res[move.id] = float_round(qty, precision_rounding=move.product_id.uom_id.rounding)
        return res

    def _get_lot_ids(self, cr, uid, ids, field_name, args, context=None):
        res = dict.fromkeys(ids, False)
        for move in self.browse(cr, uid, ids, context=context):
            if move.state == 'done':
                res[move.id] = [q.lot_id.id for q in move.quant_ids if q.lot_id]
            else:
                res[move.id] = [q.lot_id.id for q in move.reserved_quant_ids if q.lot_id]
        return res

    def _get_product_availability(self, cr, uid, ids, field_name, args, context=None):
        quant_obj = self.pool.get('stock.quant')
        res = dict.fromkeys(ids, False)
        for move in self.browse(cr, uid, ids, context=context):
            if move.state == 'done':
                res[move.id] = move.product_qty
            else:
                sublocation_ids = self.pool.get('stock.location').search(cr, uid, [('id', 'child_of', [move.location_id.id])], context=context)
                quant_ids = quant_obj.search(cr, uid, [('location_id', 'in', sublocation_ids), ('product_id', '=', move.product_id.id), ('reservation_id', '=', False)], context=context)
                availability = 0
                for quant in quant_obj.browse(cr, uid, quant_ids, context=context):
                    availability += quant.qty
                res[move.id] = min(move.product_qty, availability)
        return res

    def _get_string_qty_information(self, cr, uid, ids, field_name, args, context=None):
        settings_obj = self.pool.get('stock.config.settings')
        uom_obj = self.pool.get('product.uom')
        res = dict.fromkeys(ids, '')
        precision = self.pool['decimal.precision'].precision_get(cr, uid, 'Product Unit of Measure')
        for move in self.browse(cr, uid, ids, context=context):
            if move.state in ('draft', 'done', 'cancel') or move.location_id.usage != 'internal':
                res[move.id] = ''  # 'not applicable' or 'n/a' could work too
                continue
            total_available = min(move.product_qty, move.reserved_availability + move.availability)
            total_available = uom_obj._compute_qty_obj(cr, uid, move.product_id.uom_id, total_available, move.product_uom, round=False, context=context)
            total_available = float_round(total_available, precision_digits=precision)
            info = str(total_available)
            #look in the settings if we need to display the UoM name or not
            config_ids = settings_obj.search(cr, uid, [], limit=1, order='id DESC', context=context)
            if config_ids:
                stock_settings = settings_obj.browse(cr, uid, config_ids[0], context=context)
                if stock_settings.group_uom:
                    info += ' ' + move.product_uom.name
            if move.reserved_availability:
                if move.reserved_availability != total_available:
                    #some of the available quantity is assigned and some are available but not reserved
                    reserved_available = uom_obj._compute_qty_obj(cr, uid, move.product_id.uom_id, move.reserved_availability, move.product_uom, round=False, context=context)
                    reserved_available = float_round(reserved_available, precision_digits=precision)
                    info += _(' (%s reserved)') % str(reserved_available)
                else:
                    #all available quantity is assigned
                    info += _(' (reserved)')
            res[move.id] = info
        return res

    def _get_reserved_availability(self, cr, uid, ids, field_name, args, context=None):
        res = dict.fromkeys(ids, 0)
        for move in self.browse(cr, uid, ids, context=context):
            res[move.id] = sum([quant.qty for quant in move.reserved_quant_ids])
        return res

    def _get_move(self, cr, uid, ids, context=None):
        res = set()
        for quant in self.browse(cr, uid, ids, context=context):
            if quant.reservation_id:
                res.add(quant.reservation_id.id)
        return list(res)

    def _get_move_ids(self, cr, uid, ids, context=None):
        res = []
        for picking in self.browse(cr, uid, ids, context=context):
            res += [x.id for x in picking.move_lines]
        return res

    def _get_moves_from_prod(self, cr, uid, ids, context=None):
        if ids:
            return self.pool.get('stock.move').search(cr, uid, [('product_id', 'in', ids)], context=context)
        return []

    def _set_product_qty(self, cr, uid, id, field, value, arg, context=None):
        """ The meaning of product_qty field changed lately and is now a functional field computing the quantity
            in the default product UoM. This code has been added to raise an error if a write is made given a value
            for `product_qty`, where the same write should set the `product_uom_qty` field instead, in order to
            detect errors.
        """
        raise UserError(_('The requested operation cannot be processed because of a programming error setting the `product_qty` field instead of the `product_uom_qty`.'))

    _columns = {
        'sequence': fields.integer('Sequence'),
        'name': fields.char('Description', required=True, select=True),
        'priority': fields.selection(procurement.PROCUREMENT_PRIORITIES, 'Priority'),
        'create_date': fields.datetime('Creation Date', readonly=True, select=True),
        'date': fields.datetime('Date', required=True, select=True, help="Move date: scheduled date until move is done, then date of actual move processing", states={'done': [('readonly', True)]}),
        'date_expected': fields.datetime('Expected Date', states={'done': [('readonly', True)]}, required=True, select=True, help="Scheduled date for the processing of this move"),
        'product_id': fields.many2one('product.product', 'Product', required=True, select=True, domain=[('type', 'in', ['product', 'consu'])], states={'done': [('readonly', True)]}),
        'product_qty': fields.function(_quantity_normalize, fnct_inv=_set_product_qty, type='float', digits=0, store={
            _name: (lambda self, cr, uid, ids, c={}: ids, ['product_id', 'product_uom', 'product_uom_qty'], 10),
        }, string='Quantity',
            help='Quantity in the default UoM of the product'),
        'product_uom_qty': fields.float('Quantity', digits_compute=dp.get_precision('Product Unit of Measure'),
            required=True, states={'done': [('readonly', True)]},
            help="This is the quantity of products from an inventory "
                "point of view. For moves in the state 'done', this is the "
                "quantity of products that were actually moved. For other "
                "moves, this is the quantity of product that is planned to "
                "be moved. Lowering this quantity does not generate a "
                "backorder. Changing this quantity on assigned moves affects "
                "the product reservation, and should be done with care."
        ),
        'product_uom': fields.many2one('product.uom', 'Unit of Measure', required=True, states={'done': [('readonly', True)]}),
        'product_tmpl_id': fields.related('product_id', 'product_tmpl_id', type='many2one', relation='product.template', string='Product Template'),

        'product_packaging': fields.many2one('product.packaging', 'preferred Packaging', help="It specifies attributes of packaging like type, quantity of packaging,etc."),

        'location_id': fields.many2one('stock.location', 'Source Location', required=True, select=True, auto_join=True,
                                       states={'done': [('readonly', True)]}, help="Sets a location if you produce at a fixed location. This can be a partner location if you subcontract the manufacturing operations."),
        'location_dest_id': fields.many2one('stock.location', 'Destination Location', required=True, states={'done': [('readonly', True)]}, select=True,
                                            auto_join=True, help="Location where the system will stock the finished products."),

        'partner_id': fields.many2one('res.partner', 'Destination Address ', states={'done': [('readonly', True)]}, help="Optional address where goods are to be delivered, specifically used for allotment"),


        'move_dest_id': fields.many2one('stock.move', 'Destination Move', help="Optional: next stock move when chaining them", select=True, copy=False),
        'move_orig_ids': fields.one2many('stock.move', 'move_dest_id', 'Original Move', help="Optional: previous stock move when chaining them", select=True),

        'picking_id': fields.many2one('stock.picking', 'Transfer Reference', select=True, states={'done': [('readonly', True)]}),
        'note': fields.text('Notes'),
        'state': fields.selection([('draft', 'New'),
                                   ('cancel', 'Cancelled'),
                                   ('waiting', 'Waiting Another Move'),
                                   ('confirmed', 'Waiting Availability'),
                                   ('assigned', 'Available'),
                                   ('done', 'Done'),
                                   ], 'Status', readonly=True, select=True, copy=False,
                 help= "* New: When the stock move is created and not yet confirmed.\n"\
                       "* Waiting Another Move: This state can be seen when a move is waiting for another one, for example in a chained flow.\n"\
                       "* Waiting Availability: This state is reached when the procurement resolution is not straight forward. It may need the scheduler to run, a component to me manufactured...\n"\
                       "* Available: When products are reserved, it is set to \'Available\'.\n"\
                       "* Done: When the shipment is processed, the state is \'Done\'."),
        'partially_available': fields.boolean('Partially Available', readonly=True, help="Checks if the move has some stock reserved", copy=False),
        'price_unit': fields.float('Unit Price', help="Technical field used to record the product cost set by the user during a picking confirmation (when costing method used is 'average price' or 'real'). Value given in company currency and in product uom."),  # as it's a technical field, we intentionally don't provide the digits attribute

        'company_id': fields.many2one('res.company', 'Company', required=True, select=True),
        'split_from': fields.many2one('stock.move', string="Move Split From", help="Technical field used to track the origin of a split move, which can be useful in case of debug", copy=False),
        'backorder_id': fields.related('picking_id', 'backorder_id', type='many2one', relation="stock.picking", string="Back Order of", select=True),
        'origin': fields.char("Source Document"),
        'procure_method': fields.selection([('make_to_stock', 'Default: Take From Stock'), ('make_to_order', 'Advanced: Apply Procurement Rules')], 'Supply Method', required=True, 
                                           help="""By default, the system will take from the stock in the source location and passively wait for availability. The other possibility allows you to directly create a procurement on the source location (and thus ignore its current stock) to gather products. If we want to chain moves and have this one to wait for the previous, this second option should be chosen."""),

        # used for colors in tree views:
        'scrapped': fields.related('location_dest_id', 'scrap_location', type='boolean', relation='stock.location', string='Scrapped', readonly=True),

        'quant_ids': fields.many2many('stock.quant', 'stock_quant_move_rel', 'move_id', 'quant_id', 'Moved Quants', copy=False),
        'reserved_quant_ids': fields.one2many('stock.quant', 'reservation_id', 'Reserved quants'),
        'linked_move_operation_ids': fields.one2many('stock.move.operation.link', 'move_id', string='Linked Operations', readonly=True, help='Operations that impact this move for the computation of the remaining quantities'),
        'remaining_qty': fields.function(_get_remaining_qty, type='float', string='Remaining Quantity', digits=0,
                                         states={'done': [('readonly', True)]}, help="Remaining Quantity in default UoM according to operations matched with this move"),
        'procurement_id': fields.many2one('procurement.order', 'Procurement'),
        'group_id': fields.many2one('procurement.group', 'Procurement Group'),
        'rule_id': fields.many2one('procurement.rule', 'Procurement Rule', help='The procurement rule that created this stock move'),
        'push_rule_id': fields.many2one('stock.location.path', 'Push Rule', help='The push rule that created this stock move'),
        'propagate': fields.boolean('Propagate cancel and split', help='If checked, when this move is cancelled, cancel the linked move too'),
        'picking_type_id': fields.many2one('stock.picking.type', 'Picking Type'),
        'inventory_id': fields.many2one('stock.inventory', 'Inventory'),
        'lot_ids': fields.function(_get_lot_ids, type='many2many', relation='stock.production.lot', string='Lots'),
        'origin_returned_move_id': fields.many2one('stock.move', 'Origin return move', help='move that created the return move', copy=False),
        'returned_move_ids': fields.one2many('stock.move', 'origin_returned_move_id', 'All returned moves', help='Optional: all returned moves created from this move'),
        'reserved_availability': fields.function(_get_reserved_availability, type='float', string='Quantity Reserved', readonly=True, help='Quantity that has already been reserved for this move'),
        'availability': fields.function(_get_product_availability, type='float', string='Forecasted Quantity', readonly=True, help='Quantity in stock that can still be reserved for this move'),
        'string_availability_info': fields.function(_get_string_qty_information, type='text', string='Availability', readonly=True, help='Show various information on stock availability for this move'),
        'restrict_lot_id': fields.many2one('stock.production.lot', 'Lot', help="Technical field used to depict a restriction on the lot of quants to consider when marking this move as 'done'"),
        'restrict_partner_id': fields.many2one('res.partner', 'Owner ', help="Technical field used to depict a restriction on the ownership of quants to consider when marking this move as 'done'"),
        'route_ids': fields.many2many('stock.location.route', 'stock_location_route_move', 'move_id', 'route_id', 'Destination route', help="Preferred route to be followed by the procurement order"),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse', help="Technical field depicting the warehouse to consider for the route selection on the next procurement (if any)."),
    }

    def _default_destination_address(self, cr, uid, context=None):
        return False

    def _default_group_id(self, cr, uid, context=None):
        context = context or {}
        if context.get('default_picking_id', False):
            picking = self.pool.get('stock.picking').browse(cr, uid, context['default_picking_id'], context=context)
            return picking.group_id.id
        return False

    _defaults = {
        'partner_id': _default_destination_address,
        'state': 'draft',
        'priority': '1',
        'product_uom_qty': 1.0,
        'sequence': 10,
        'scrapped': False,
        'date': fields.datetime.now,
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'stock.move', context=c),
        'date_expected': fields.datetime.now,
        'procure_method': 'make_to_stock',
        'propagate': True,
        'partially_available': False,
        'group_id': _default_group_id,
    }

    def _check_uom(self, cr, uid, ids, context=None):
        for move in self.browse(cr, uid, ids, context=context):
            if move.product_id.uom_id.category_id.id != move.product_uom.category_id.id:
                return False
        return True

    _constraints = [
        (_check_uom,
            'You try to move a product using a UoM that is not compatible with the UoM of the product moved. Please use an UoM in the same UoM category.',
            ['product_uom']),
    ]
    def init(self, cr):
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('stock_move_product_location_index',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX stock_move_product_location_index ON stock_move (product_id, location_id, location_dest_id, company_id, state)')

    @api.cr_uid_ids_context
    def do_unreserve(self, cr, uid, move_ids, context=None):
        quant_obj = self.pool.get("stock.quant")
        for move in self.browse(cr, uid, move_ids, context=context):
            if move.state in ('done', 'cancel'):
                raise UserError(_('Cannot unreserve a done move'))
            quant_obj.quants_unreserve(cr, uid, move, context=context)
            if self.find_move_ancestors(cr, uid, move, context=context):
                self.write(cr, uid, [move.id], {'state': 'waiting'}, context=context)
            else:
                self.write(cr, uid, [move.id], {'state': 'confirmed'}, context=context)

    def _prepare_procurement_from_move(self, cr, uid, move, context=None):
        origin = (move.group_id and (move.group_id.name + ":") or "") + (move.rule_id and move.rule_id.name or move.origin or move.picking_id.name or "/")
        group_id = move.group_id and move.group_id.id or False
        if move.rule_id:
            if move.rule_id.group_propagation_option == 'fixed' and move.rule_id.group_id:
                group_id = move.rule_id.group_id.id
            elif move.rule_id.group_propagation_option == 'none':
                group_id = False
        return {
            'name': move.rule_id and move.rule_id.name or "/",
            'origin': origin,
            'company_id': move.company_id and move.company_id.id or False,
            'date_planned': move.date,
            'product_id': move.product_id.id,
            'product_qty': move.product_uom_qty,
            'product_uom': move.product_uom.id,
            'location_id': move.location_id.id,
            'move_dest_id': move.id,
            'group_id': group_id,
            'route_ids': [(4, x.id) for x in move.route_ids],
            'warehouse_id': move.warehouse_id.id or (move.picking_type_id and move.picking_type_id.warehouse_id.id or False),
            'priority': move.priority,
        }

    def _push_apply(self, cr, uid, moves, context=None):
        push_obj = self.pool.get("stock.location.path")
        for move in moves:
            #1) if the move is already chained, there is no need to check push rules
            #2) if the move is a returned move, we don't want to check push rules, as returning a returned move is the only decent way
            #   to receive goods without triggering the push rules again (which would duplicate chained operations)
            if not move.move_dest_id:
                domain = [('location_from_id', '=', move.location_dest_id.id)]
                #priority goes to the route defined on the product and product category
                route_ids = [x.id for x in move.product_id.route_ids + move.product_id.categ_id.total_route_ids]
                rules = push_obj.search(cr, uid, domain + [('route_id', 'in', route_ids)], order='route_sequence, sequence', context=context)
                if not rules:
                    #then we search on the warehouse if a rule can apply
                    wh_route_ids = []
                    if move.warehouse_id:
                        wh_route_ids = [x.id for x in move.warehouse_id.route_ids]
                    elif move.picking_id.picking_type_id.warehouse_id:
                        wh_route_ids = [x.id for x in move.picking_id.picking_type_id.warehouse_id.route_ids]
                    if wh_route_ids:
                        rules = push_obj.search(cr, uid, domain + [('route_id', 'in', wh_route_ids)], order='route_sequence, sequence', context=context)
                    if not rules:
                        #if no specialized push rule has been found yet, we try to find a general one (without route)
                        rules = push_obj.search(cr, uid, domain + [('route_id', '=', False)], order='sequence', context=context)
                if rules:
                    rule = push_obj.browse(cr, uid, rules[0], context=context)
                    # Make sure it is not returning the return
                    if (not move.origin_returned_move_id or move.origin_returned_move_id.location_id.id != rule.location_dest_id.id):
                        push_obj._apply(cr, uid, rule, move, context=context)
        return True

    def _create_procurement(self, cr, uid, move, context=None):
        """ This will create a procurement order """
        return self.pool.get("procurement.order").create(cr, uid, self._prepare_procurement_from_move(cr, uid, move, context=context), context=context)

    def _create_procurements(self, cr, uid, moves, context=None):
        res = []
        for move in moves:
            res.append(self._create_procurement(cr, uid, move, context=context))
        # Run procurements immediately when generated from multiple moves
        self.pool['procurement.order'].run(cr, uid, res, context=context)
        return res

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        # Check that we do not modify a stock.move which is done
        frozen_fields = set(['product_qty', 'product_uom', 'location_id', 'location_dest_id', 'product_id'])
        for move in self.browse(cr, uid, ids, context=context):
            if move.state == 'done':
                if frozen_fields.intersection(vals):
                    raise UserError(_('Quantities, Units of Measure, Products and Locations cannot be modified on stock moves that have already been processed (except by the Administrator).'))
        propagated_changes_dict = {}
        #propagation of quantity change
        if vals.get('product_uom_qty'):
            propagated_changes_dict['product_uom_qty'] = vals['product_uom_qty']
        if vals.get('product_uom_id'):
            propagated_changes_dict['product_uom_id'] = vals['product_uom_id']
        #propagation of expected date:
        propagated_date_field = False
        if vals.get('date_expected'):
            #propagate any manual change of the expected date
            propagated_date_field = 'date_expected'
        elif (vals.get('state', '') == 'done' and vals.get('date')):
            #propagate also any delta observed when setting the move as done
            propagated_date_field = 'date'

        if not context.get('do_not_propagate', False) and (propagated_date_field or propagated_changes_dict):
            #any propagation is (maybe) needed
            for move in self.browse(cr, uid, ids, context=context):
                if move.move_dest_id and move.propagate:
                    if 'date_expected' in propagated_changes_dict:
                        propagated_changes_dict.pop('date_expected')
                    if propagated_date_field:
                        current_date = datetime.strptime(move.date_expected, DEFAULT_SERVER_DATETIME_FORMAT)
                        new_date = datetime.strptime(vals.get(propagated_date_field), DEFAULT_SERVER_DATETIME_FORMAT)
                        delta = new_date - current_date
                        if abs(delta.days) >= move.company_id.propagation_minimum_delta:
                            old_move_date = datetime.strptime(move.move_dest_id.date_expected, DEFAULT_SERVER_DATETIME_FORMAT)
                            new_move_date = (old_move_date + relativedelta.relativedelta(days=delta.days or 0)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                            propagated_changes_dict['date_expected'] = new_move_date
                    #For pushed moves as well as for pulled moves, propagate by recursive call of write().
                    #Note that, for pulled moves we intentionally don't propagate on the procurement.
                    if propagated_changes_dict:
                        self.write(cr, uid, [move.move_dest_id.id], propagated_changes_dict, context=context)
        return super(stock_move, self).write(cr, uid, ids, vals, context=context)

    def onchange_quantity(self, cr, uid, ids, product_id, product_qty, product_uom):
        """ On change of product quantity finds UoM
        @param product_id: Product id
        @param product_qty: Changed Quantity of product
        @param product_uom: Unit of measure of product
        @return: Dictionary of values
        """
        warning = {}
        result = {}

        if (not product_id) or (product_qty <= 0.0):
            result['product_qty'] = 0.0
            return {'value': result}

        product_obj = self.pool.get('product.product')
        # Warn if the quantity was decreased
        if ids:
            for move in self.read(cr, uid, ids, ['product_qty']):
                if product_qty < move['product_qty']:
                    warning.update({
                        'title': _('Information'),
                        'message': _("By changing this quantity here, you accept the "
                                "new quantity as complete: Odoo will not "
                                "automatically generate a back order.")})
                break
        return {'warning': warning}

    def onchange_product_id(self, cr, uid, ids, prod_id=False, loc_id=False, loc_dest_id=False, partner_id=False):
        """ On change of product id, if finds UoM, quantity
        @param prod_id: Changed Product id
        @param loc_id: Source location id
        @param loc_dest_id: Destination location id
        @param partner_id: Address id of partner
        @return: Dictionary of values
        """
        if not prod_id:
            return {'domain': {'product_uom': []}}
        user = self.pool.get('res.users').browse(cr, uid, uid)
        lang = user and user.lang or False
        if partner_id:
            addr_rec = self.pool.get('res.partner').browse(cr, uid, partner_id)
            if addr_rec:
                lang = addr_rec and addr_rec.lang or False
        ctx = {'lang': lang}

        product = self.pool.get('product.product').browse(cr, uid, [prod_id], context=ctx)[0]
        result = {
            'name': product.partner_ref,
            'product_uom': product.uom_id.id,
            'product_uom_qty': 1.00,
        }
        if loc_id:
            result['location_id'] = loc_id
        if loc_dest_id:
            result['location_dest_id'] = loc_dest_id
        res = {'value': result,
               'domain': {'product_uom': [('category_id', '=', product.uom_id.category_id.id)]}
               }
        return res

    def _prepare_picking_assign(self, cr, uid, move, context=None):
        """ Prepares a new picking for this move as it could not be assigned to
        another picking. This method is designed to be inherited.
        """
        values = {
            'origin': move.origin,
            'company_id': move.company_id and move.company_id.id or False,
            'move_type': move.group_id and move.group_id.move_type or 'direct',
            'partner_id': move.partner_id.id or False,
            'picking_type_id': move.picking_type_id and move.picking_type_id.id or False,
            'location_id': move.location_id.id,
            'location_dest_id': move.location_dest_id.id,
        }
        return values

    @api.cr_uid_ids_context
    def _picking_assign(self, cr, uid, move_ids, context=None):
        """Try to assign the moves to an existing picking
        that has not been reserved yet and has the same
        procurement group, locations and picking type  (moves should already have them identical)
         Otherwise, create a new picking to assign them to.
        """
        move = self.browse(cr, uid, move_ids, context=context)[0]
        pick_obj = self.pool.get("stock.picking")
        picks = pick_obj.search(cr, uid, [
                ('group_id', '=', move.group_id.id),
                ('location_id', '=', move.location_id.id),
                ('location_dest_id', '=', move.location_dest_id.id),
                ('picking_type_id', '=', move.picking_type_id.id),
                ('printed', '=', False),
                ('state', 'in', ['draft', 'confirmed', 'waiting', 'partially_available', 'assigned'])], limit=1, context=context)
        if picks:
            pick = picks[0]
        else:
            values = self._prepare_picking_assign(cr, uid, move, context=context)
            pick = pick_obj.create(cr, uid, values, context=context)
        return self.write(cr, uid, move_ids, {'picking_id': pick}, context=context)

    def onchange_date(self, cr, uid, ids, date, date_expected, context=None):
        """ On change of Scheduled Date gives a Move date.
        @param date_expected: Scheduled Date
        @param date: Move Date
        @return: Move Date
        """
        if not date_expected:
            date_expected = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        return {'value': {'date': date_expected}}

    def attribute_price(self, cr, uid, move, context=None):
        """
            Attribute price to move, important in inter-company moves or receipts with only one partner
        """
        if not move.price_unit:
            price = move.product_id.standard_price
            self.write(cr, uid, [move.id], {'price_unit': price})

    def action_confirm(self, cr, uid, ids, context=None):
        """ Confirms stock move or put it in waiting if it's linked to another move.
        @return: List of ids.
        """
        if not context:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        states = {
            'confirmed': [],
            'waiting': []
        }
        to_assign = {}
        for move in self.browse(cr, uid, ids, context=context):
            self.attribute_price(cr, uid, move, context=context)
            state = 'confirmed'
            #if the move is preceeded, then it's waiting (if preceeding move is done, then action_assign has been called already and its state is already available)
            if move.move_orig_ids:
                state = 'waiting'
            #if the move is split and some of the ancestor was preceeded, then it's waiting as well
            elif move.split_from:
                move2 = move.split_from
                while move2 and state != 'waiting':
                    if move2.move_orig_ids:
                        state = 'waiting'
                    move2 = move2.split_from
            states[state].append(move.id)

            if not move.picking_id and move.picking_type_id:
                key = (move.group_id.id, move.location_id.id, move.location_dest_id.id)
                if key not in to_assign:
                    to_assign[key] = []
                to_assign[key].append(move.id)
        moves = [move for move in self.browse(cr, uid, states['confirmed'], context=context) if move.procure_method == 'make_to_order']
        self._create_procurements(cr, uid, moves, context=context)
        for move in moves:
            states['waiting'].append(move.id)
            states['confirmed'].remove(move.id)

        for state, write_ids in states.items():
            if len(write_ids):
                self.write(cr, uid, write_ids, {'state': state})
        #assign picking in batch for all confirmed move that share the same details
        for key, move_ids in to_assign.items():
            self._picking_assign(cr, uid, move_ids, context=context)
        moves = self.browse(cr, uid, ids, context=context)
        self._push_apply(cr, uid, moves, context=context)
        return ids

    def force_assign(self, cr, uid, ids, context=None):
        """ Changes the state to assigned.
        @return: True
        """
        res = self.write(cr, uid, ids, {'state': 'assigned'}, context=context)
        self.check_recompute_pack_op(cr, uid, ids, context=context)
        return res

    def check_tracking(self, cr, uid, move, ops, context=None):
        """ Checks if serial number is assigned to stock move or not and raise an error if it had to.
        """
        if move.picking_id and (move.picking_id.picking_type_id.use_existing_lots or move.picking_id.picking_type_id.use_create_lots) and \
            move.product_id.tracking != 'none':
            if not (move.restrict_lot_id or (ops and (ops.product_id and ops.pack_lot_ids)) or (ops and not ops.product_id)):
                raise UserError(_('You need to provide a Lot/Serial Number for product %s') % move.product_id.name)

    def check_recompute_pack_op(self, cr, uid, ids, context=None):
        pickings = list(set([x.picking_id for x in self.browse(cr, uid, ids, context=context) if x.picking_id]))
        pickings_partial = []
        pickings_write = []
        pick_obj = self.pool['stock.picking']
        for pick in pickings:
            if pick.state in ('waiting', 'confirmed'): #In case of 'all at once' delivery method it should not prepare pack operations
                continue
            # Check if someone was treating the picking already
            if not any([x.qty_done > 0 for x in pick.pack_operation_ids]):
                pickings_partial.append(pick.id)
            else:
                pickings_write.append(pick.id)
        if pickings_partial:
            pick_obj.do_prepare_partial(cr, uid, pickings_partial, context=context)
        if pickings_write:
            pick_obj.write(cr, uid, pickings_write, {'recompute_pack_op': True}, context=context)

    def action_assign(self, cr, uid, ids, no_prepare=False, context=None):
        """ Checks the product type and accordingly writes the state.
        """
        context = context or {}
        quant_obj = self.pool.get("stock.quant")
        uom_obj = self.pool['product.uom']
        to_assign_moves = set()
        main_domain = {}
        todo_moves = []
        operations = set()
        self.do_unreserve(cr, uid, [x.id for x in self.browse(cr, uid, ids, context=context) if x.reserved_quant_ids and x.state in ['confirmed', 'waiting', 'assigned']], context=context)
        for move in self.browse(cr, uid, ids, context=context):
            if move.state not in ('confirmed', 'waiting', 'assigned'):
                continue
            if move.location_id.usage in ('supplier', 'inventory', 'production'):
                to_assign_moves.add(move.id)
                #in case the move is returned, we want to try to find quants before forcing the assignment
                if not move.origin_returned_move_id:
                    continue
            if move.product_id.type == 'consu':
                to_assign_moves.add(move.id)
                continue
            else:
                todo_moves.append(move)

                #we always search for yet unassigned quants
                main_domain[move.id] = [('reservation_id', '=', False), ('qty', '>', 0)]

                #if the move is preceeded, restrict the choice of quants in the ones moved previously in original move
                ancestors = self.find_move_ancestors(cr, uid, move, context=context)
                if move.state == 'waiting' and not ancestors:
                    #if the waiting move hasn't yet any ancestor (PO/MO not confirmed yet), don't find any quant available in stock
                    main_domain[move.id] += [('id', '=', False)]
                elif ancestors:
                    main_domain[move.id] += [('history_ids', 'in', ancestors)]

                #if the move is returned from another, restrict the choice of quants to the ones that follow the returned move
                if move.origin_returned_move_id:
                    main_domain[move.id] += [('history_ids', 'in', move.origin_returned_move_id.id)]
                for link in move.linked_move_operation_ids:
                    operations.add(link.operation_id)
        # Check all ops and sort them: we want to process first the packages, then operations with lot then the rest
        operations = list(operations)
        operations.sort(key=lambda x: ((x.package_id and not x.product_id) and -4 or 0) + (x.package_id and -2 or 0) + (x.pack_lot_ids and -1 or 0))
        for ops in operations:
            #first try to find quants based on specific domains given by linked operations for the case where we want to rereserve according to existing pack operations
            if not (ops.product_id and ops.pack_lot_ids):
                for record in ops.linked_move_operation_ids:
                    move = record.move_id
                    if move.id in main_domain:
                        qty = record.qty
                        domain = main_domain[move.id]
                        if qty:
                            quants = quant_obj.quants_get_preferred_domain(cr, uid, qty, move, ops=ops, domain=domain, preferred_domain_list=[], context=context)
                            quant_obj.quants_reserve(cr, uid, quants, move, record, context=context)
            else:
                lot_qty = {}
                rounding = ops.product_id.uom_id.rounding
                for pack_lot in ops.pack_lot_ids:
                    lot_qty[pack_lot.lot_id.id] = uom_obj._compute_qty(cr, uid, ops.product_uom_id.id, pack_lot.qty, ops.product_id.uom_id.id)
                for record in ops.linked_move_operation_ids:
                    move_qty = record.qty
                    move = record.move_id
                    domain = main_domain[move.id]
                    for lot in lot_qty:
                        if float_compare(lot_qty[lot], 0, precision_rounding=rounding) > 0 and float_compare(move_qty, 0, precision_rounding=rounding) > 0:
                            qty = min(lot_qty[lot], move_qty)
                            quants = quant_obj.quants_get_preferred_domain(cr, uid, qty, move, ops=ops, lot_id=lot, domain=domain, preferred_domain_list=[], context=context)
                            quant_obj.quants_reserve(cr, uid, quants, move, record, context=context)
                            lot_qty[lot] -= qty
                            move_qty -= qty

        for move in todo_moves:
            if move.linked_move_operation_ids:
                continue
            #then if the move isn't totally assigned, try to find quants without any specific domain
            if move.state != 'assigned':
                qty_already_assigned = move.reserved_availability
                qty = move.product_qty - qty_already_assigned
                quants = quant_obj.quants_get_preferred_domain(cr, uid, qty, move, domain=main_domain[move.id], preferred_domain_list=[], context=context)
                quant_obj.quants_reserve(cr, uid, quants, move, context=context)

        #force assignation of consumable products and incoming from supplier/inventory/production
        # Do not take force_assign as it would create pack operations
        if to_assign_moves:
            self.write(cr, uid, list(to_assign_moves), {'state': 'assigned'}, context=context)
        if not no_prepare:
            self.check_recompute_pack_op(cr, uid, ids, context=context)

    def action_cancel(self, cr, uid, ids, context=None):
        """ Cancels the moves and if all moves are cancelled it cancels the picking.
        @return: True
        """
        procurement_obj = self.pool.get('procurement.order')
        context = context or {}
        procs_to_check = []
        for move in self.browse(cr, uid, ids, context=context):
            if move.state == 'done':
                raise UserError(_('You cannot cancel a stock move that has been set to \'Done\'.'))
            if move.reserved_quant_ids:
                self.pool.get("stock.quant").quants_unreserve(cr, uid, move, context=context)
            if context.get('cancel_procurement'):
                if move.propagate:
                    procurement_ids = procurement_obj.search(cr, uid, [('move_dest_id', '=', move.id)], context=context)
                    procurement_obj.cancel(cr, uid, procurement_ids, context=context)
            else:
                if move.move_dest_id:
                    if move.propagate:
                        self.action_cancel(cr, uid, [move.move_dest_id.id], context=context)
                    elif move.move_dest_id.state == 'waiting':
                        #If waiting, the chain will be broken and we are not sure if we can still wait for it (=> could take from stock instead)
                        self.write(cr, uid, [move.move_dest_id.id], {'state': 'confirmed'}, context=context)
                if move.procurement_id:
                    # Does the same as procurement check, only eliminating a refresh
                    procs_to_check.append(move.procurement_id.id)

        res = self.write(cr, uid, ids, {'state': 'cancel', 'move_dest_id': False}, context=context)
        if procs_to_check:
            procurement_obj.check(cr, uid, procs_to_check, context=context)
        return res

    def _check_package_from_moves(self, cr, uid, ids, context=None):
        pack_obj = self.pool.get("stock.quant.package")
        packs = set()
        for move in self.browse(cr, uid, ids, context=context):
            packs |= set([q.package_id for q in move.quant_ids if q.package_id and q.qty > 0])
        return pack_obj._check_location_constraint(cr, uid, list(packs), context=context)

    def find_move_ancestors(self, cr, uid, move, context=None):
        '''Find the first level ancestors of given move '''
        ancestors = []
        move2 = move
        while move2:
            ancestors += [x.id for x in move2.move_orig_ids]
            #loop on the split_from to find the ancestor of split moves only if the move has not direct ancestor (priority goes to them)
            move2 = not move2.move_orig_ids and move2.split_from or False
        return ancestors

    @api.cr_uid_ids_context
    def recalculate_move_state(self, cr, uid, move_ids, context=None):
        '''Recompute the state of moves given because their reserved quants were used to fulfill another operation'''
        for move in self.browse(cr, uid, move_ids, context=context):
            vals = {}
            reserved_quant_ids = move.reserved_quant_ids
            if len(reserved_quant_ids) > 0 and not move.partially_available:
                vals['partially_available'] = True
            if len(reserved_quant_ids) == 0 and move.partially_available:
                vals['partially_available'] = False
            if move.state == 'assigned':
                if self.find_move_ancestors(cr, uid, move, context=context):
                    vals['state'] = 'waiting'
                else:
                    vals['state'] = 'confirmed'
            if vals:
                self.write(cr, uid, [move.id], vals, context=context)

    def _move_quants_by_lot(self, cr, uid, ops, lot_qty, quants_taken, false_quants, lot_move_qty, quant_dest_package_id, context=None):
        """
        This function is used to process all the pack operation lots of a pack operation
        For every move:
            First, we check the quants with lot already reserved (and those are already subtracted from the lots to do)
            Then go through all the lots to process:
                Add reserved false lots lot by lot
                Check if there are not reserved quants or reserved elsewhere with that lot or without lot (with the traditional method)
        """
        quant_obj = self.pool['stock.quant']
        fallback_domain = [('reservation_id', '=', False)]
        fallback_domain2 = ['&', ('reservation_id', 'not in', [x for x in lot_move_qty.keys()]), ('reservation_id', '!=', False)]
        preferred_domain_list = [fallback_domain] + [fallback_domain2]
        rounding = ops.product_id.uom_id.rounding
        for move in lot_move_qty:
            move_quants_dict = {}
            move_rec = self.pool['stock.move'].browse(cr, uid, move, context=context)
            # Assign quants already reserved with lot to the correct
            for quant in quants_taken:
                move_quants_dict.setdefault(quant[0].lot_id.id, [])
                move_quants_dict[quant[0].lot_id.id] += [quant]
            false_quants_move = [x for x in false_quants if x[0].reservation_id.id == move]
            for lot in lot_qty:
                move_quants_dict.setdefault(lot, [])
                redo_false_quants = False
                # Take remaining reserved quants with  no lot first
                # (This will be used mainly when incoming had no lot and you do outgoing with)
                while false_quants_move and float_compare(lot_qty[lot], 0, precision_rounding=rounding) > 0 and float_compare(lot_move_qty[move], 0, precision_rounding=rounding) > 0:
                    qty_min = min(lot_qty[lot], lot_move_qty[move])
                    if false_quants_move[0].qty > qty_min:
                        move_quants_dict[lot] += [(false_quants_move[0], qty_min)]
                        qty = qty_min
                        redo_false_quants = True
                    else:
                        qty = false_quants_move[0].qty
                        move_quants_dict[lot] += [(false_quants_move[0], qty)]
                        false_quants_move.pop(0)
                    lot_qty[lot] -= qty
                    lot_move_qty[move] -= qty

                # Search other with first matching lots and then without lots
                if float_compare(lot_move_qty[move], 0, precision_rounding=rounding) > 0 and float_compare(lot_qty[lot], 0, precision_rounding=rounding) > 0:
                    # Search if we can find quants with that lot
                    domain = [('qty', '>', 0)]
                    qty = min(lot_qty[lot], lot_move_qty[move])
                    quants = quant_obj.quants_get_preferred_domain(cr, uid, qty, move_rec, ops=ops, lot_id=lot, domain=domain,
                                                        preferred_domain_list=preferred_domain_list, context=context)
                    move_quants_dict[lot] += quants
                    lot_qty[lot] -= qty
                    lot_move_qty[move] -= qty

                #Move all the quants related to that lot/move
                if move_quants_dict[lot]:
                    quant_obj.quants_move(cr, uid, move_quants_dict[lot], move_rec, ops.location_dest_id, location_from=ops.location_id,
                                                    lot_id=lot, owner_id=ops.owner_id.id, src_package_id=ops.package_id.id,
                                                    dest_package_id=quant_dest_package_id, context=context)
                    if redo_false_quants:
                        move_rec = self.pool['stock.move'].browse(cr, uid, move, context=context)
                        false_quants_move = [x for x in move_rec.reserved_quant_ids if (not x.lot_id) and (x.owner_id.id == ops.owner_id.id) \
                                             and (x.location_id.id == ops.location_id.id) and (x.package_id.id != ops.package_id.id)]

    def action_done(self, cr, uid, ids, context=None):
        """ Process completely the moves given as ids and if all moves are done, it will finish the picking.
        """
        context = context or {}
        picking_obj = self.pool.get("stock.picking")
        quant_obj = self.pool.get("stock.quant")
        uom_obj = self.pool.get("product.uom")
        todo = [move.id for move in self.browse(cr, uid, ids, context=context) if move.state == "draft"]
        if todo:
            ids = self.action_confirm(cr, uid, todo, context=context)
        pickings = set()
        procurement_ids = set()
        #Search operations that are linked to the moves
        operations = set()
        move_qty = {}
        for move in self.browse(cr, uid, ids, context=context):
            move_qty[move.id] = move.product_qty
            for link in move.linked_move_operation_ids:
                operations.add(link.operation_id)

        #Sort operations according to entire packages first, then package + lot, package only, lot only
        operations = list(operations)
        operations.sort(key=lambda x: ((x.package_id and not x.product_id) and -4 or 0) + (x.package_id and -2 or 0) + (x.pack_lot_ids and -1 or 0))

        for ops in operations:
            if ops.picking_id:
                pickings.add(ops.picking_id.id)
            entire_pack=False
            if ops.product_id:
                #If a product is given, the result is always put immediately in the result package (if it is False, they are without package)
                quant_dest_package_id  = ops.result_package_id.id
            else:
                # When a pack is moved entirely, the quants should not be written anything for the destination package
                quant_dest_package_id = False
                entire_pack=True
            lot_qty = {}
            tot_qty = 0.0
            for pack_lot in ops.pack_lot_ids:
                qty = uom_obj._compute_qty(cr, uid, ops.product_uom_id.id, pack_lot.qty, ops.product_id.uom_id.id)
                lot_qty[pack_lot.lot_id.id] = qty
                tot_qty += pack_lot.qty
            if ops.pack_lot_ids and ops.product_id and float_compare(tot_qty, ops.product_qty, precision_rounding=ops.product_uom_id.rounding) != 0.0:
                raise UserError(_('You have a difference between the quantity on the operation and the quantities specified for the lots. '))

            quants_taken = []
            false_quants = []
            lot_move_qty = {}
            #Group links by move first
            move_qty_ops = {}
            for record in ops.linked_move_operation_ids:
                move = record.move_id
                if not move_qty_ops.get(move):
                    move_qty_ops[move] = record.qty
                else:
                    move_qty_ops[move] += record.qty
            #Process every move only once for every pack operation
            for move in move_qty_ops:
                main_domain = [('qty', '>', 0)]
                self.check_tracking(cr, uid, move, ops, context=context)
                preferred_domain = [('reservation_id', '=', move.id)]
                fallback_domain = [('reservation_id', '=', False)]
                fallback_domain2 = ['&', ('reservation_id', '!=', move.id), ('reservation_id', '!=', False)]
                if not ops.pack_lot_ids:
                    preferred_domain_list = [preferred_domain] + [fallback_domain] + [fallback_domain2]
                    quants = quant_obj.quants_get_preferred_domain(cr, uid, move_qty_ops[move], move, ops=ops, domain=main_domain,
                                                        preferred_domain_list=preferred_domain_list, context=context)
                    quant_obj.quants_move(cr, uid, quants, move, ops.location_dest_id, location_from=ops.location_id,
                                          lot_id=False, owner_id=ops.owner_id.id, src_package_id=ops.package_id.id,
                                          dest_package_id=quant_dest_package_id, entire_pack=entire_pack, context=context)
                else:
                    # Check what you can do with reserved quants already
                    qty_on_link = move_qty_ops[move]
                    rounding = ops.product_id.uom_id.rounding
                    for reserved_quant in move.reserved_quant_ids:
                        if (reserved_quant.owner_id.id != ops.owner_id.id) or (reserved_quant.location_id.id != ops.location_id.id) or \
                                (reserved_quant.package_id.id != ops.package_id.id):
                            continue
                        if not reserved_quant.lot_id:
                            false_quants += [reserved_quant]
                        elif float_compare(lot_qty.get(reserved_quant.lot_id.id, 0), 0, precision_rounding=rounding) > 0:
                            if float_compare(lot_qty[reserved_quant.lot_id.id], reserved_quant.qty, precision_rounding=rounding) >= 0:
                                lot_qty[reserved_quant.lot_id.id] -= reserved_quant.qty
                                quants_taken += [(reserved_quant, reserved_quant.qty)]
                                qty_on_link -= reserved_quant.qty
                            else:
                                quants_taken += [(reserved_quant, lot_qty[reserved_quant.lot_id.id])]
                                lot_qty[reserved_quant.lot_id.id] = 0
                                qty_on_link -= lot_qty[reserved_quant.lot_id.id]
                    lot_move_qty[move.id] = qty_on_link

                if not move_qty.get(move.id):
                    raise UserError(_("The roundings of your Unit of Measures %s on the move vs. %s on the product don't allow to do these operations or you are not transferring the picking at once. ") % (move.product_uom.name, move.product_id.uom_id.name))
                move_qty[move.id] -= move_qty_ops[move]

            #Handle lots separately
            if ops.pack_lot_ids:
                self._move_quants_by_lot(cr, uid, ops, lot_qty, quants_taken, false_quants, lot_move_qty, quant_dest_package_id, context=context)

            # Handle pack in pack
            if not ops.product_id and ops.package_id and ops.result_package_id.id != ops.package_id.parent_id.id:
                self.pool.get('stock.quant.package').write(cr, SUPERUSER_ID, [ops.package_id.id], {'parent_id': ops.result_package_id.id}, context=context)
        #Check for remaining qtys and unreserve/check move_dest_id in
        move_dest_ids = set()
        for move in self.browse(cr, uid, ids, context=context):
            move_qty_cmp = float_compare(move_qty[move.id], 0, precision_rounding=move.product_id.uom_id.rounding)
            if move_qty_cmp > 0:  # (=In case no pack operations in picking)
                main_domain = [('qty', '>', 0)]
                preferred_domain = [('reservation_id', '=', move.id)]
                fallback_domain = [('reservation_id', '=', False)]
                fallback_domain2 = ['&', ('reservation_id', '!=', move.id), ('reservation_id', '!=', False)]
                preferred_domain_list = [preferred_domain] + [fallback_domain] + [fallback_domain2]
                self.check_tracking(cr, uid, move, False, context=context)
                qty = move_qty[move.id]
                quants = quant_obj.quants_get_preferred_domain(cr, uid, qty, move, domain=main_domain, preferred_domain_list=preferred_domain_list, context=context)
                quant_obj.quants_move(cr, uid, quants, move, move.location_dest_id, lot_id=move.restrict_lot_id.id, owner_id=move.restrict_partner_id.id, context=context)

            # If the move has a destination, add it to the list to reserve
            if move.move_dest_id and move.move_dest_id.state in ('waiting', 'confirmed'):
                move_dest_ids.add(move.move_dest_id.id)

            if move.procurement_id:
                procurement_ids.add(move.procurement_id.id)

            #unreserve the quants and make them available for other operations/moves
            quant_obj.quants_unreserve(cr, uid, move, context=context)
        # Check the packages have been placed in the correct locations
        self._check_package_from_moves(cr, uid, ids, context=context)
        #set the move as done
        self.write(cr, uid, ids, {'state': 'done', 'date': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)}, context=context)
        self.pool.get('procurement.order').check(cr, uid, list(procurement_ids), context=context)
        #assign destination moves
        if move_dest_ids:
            self.action_assign(cr, uid, list(move_dest_ids), context=context)
        #check picking state to set the date_done is needed
        done_picking = []
        for picking in picking_obj.browse(cr, uid, list(pickings), context=context):
            if picking.state == 'done' and not picking.date_done:
                done_picking.append(picking.id)
        if done_picking:
            picking_obj.write(cr, uid, done_picking, {'date_done': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)}, context=context)
        return True

    def unlink(self, cr, uid, ids, context=None):
        context = context or {}
        for move in self.browse(cr, uid, ids, context=context):
            if move.state not in ('draft', 'cancel'):
                raise UserError(_('You can only delete draft moves.'))
        return super(stock_move, self).unlink(cr, uid, ids, context=context)

    def action_scrap(self, cr, uid, ids, quantity, location_id, restrict_lot_id=False, restrict_partner_id=False, context=None):
        """ Move the scrap/damaged product into scrap location
        @param cr: the database cursor
        @param uid: the user id
        @param ids: ids of stock move object to be scrapped
        @param quantity : specify scrap qty
        @param location_id : specify scrap location
        @param context: context arguments
        @return: Scraped lines
        """
        quant_obj = self.pool.get("stock.quant")
        #quantity should be given in MOVE UOM
        if quantity <= 0:
            raise UserError(_('Please provide a positive quantity to scrap.'))
        res = []
        for move in self.browse(cr, uid, ids, context=context):
            source_location = move.location_id
            if move.state == 'done':
                source_location = move.location_dest_id
            #Previously used to prevent scraping from virtual location but not necessary anymore
            #if source_location.usage != 'internal':
                #restrict to scrap from a virtual location because it's meaningless and it may introduce errors in stock ('creating' new products from nowhere)
                #raise UserError(_('Forbidden operation: it is not allowed to scrap products from a virtual location.'))
            move_qty = move.product_qty
            default_val = {
                'location_id': source_location.id,
                'product_uom_qty': quantity,
                'state': move.state,
                'scrapped': True,
                'location_dest_id': location_id,
                'restrict_lot_id': restrict_lot_id,
                'restrict_partner_id': restrict_partner_id,
            }
            new_move = self.copy(cr, uid, move.id, default_val)

            res += [new_move]
            product_obj = self.pool.get('product.product')
            for product in product_obj.browse(cr, uid, [move.product_id.id], context=context):
                if move.picking_id:
                    uom = product.uom_id.name if product.uom_id else ''
                    message = _("%s %s %s has been <b>moved to</b> scrap.") % (quantity, uom, product.name)
                    move.picking_id.message_post(body=message)

            # We "flag" the quant from which we want to scrap the products. To do so:
            #    - we select the quants related to the move we scrap from
            #    - we reserve the quants with the scrapped move
            # See self.action_done, et particularly how is defined the "preferred_domain" for clarification
            scrap_move = self.browse(cr, uid, new_move, context=context)
            if move.state == 'done' and scrap_move.location_id.usage not in ('supplier', 'inventory', 'production'):
                domain = [('qty', '>', 0), ('history_ids', 'in', [move.id])]
                # We use scrap_move data since a reservation makes sense for a move not already done
                quants = quant_obj.quants_get_preferred_domain(cr, uid, scrap_move.location_id,
                        scrap_move.product_id, quantity, domain=domain, preferred_domain_list=[],
                        restrict_lot_id=scrap_move.restrict_lot_id.id, restrict_partner_id=scrap_move.restrict_partner_id.id, context=context)
                quant_obj.quants_reserve(cr, uid, quants, scrap_move, context=context)
        self.action_done(cr, uid, res, context=context)
        return res

    def split(self, cr, uid, move, qty, restrict_lot_id=False, restrict_partner_id=False, context=None):
        """ Splits qty from move move into a new move
        :param move: browse record
        :param qty: float. quantity to split (given in product UoM)
        :param restrict_lot_id: optional production lot that can be given in order to force the new move to restrict its choice of quants to this lot.
        :param restrict_partner_id: optional partner that can be given in order to force the new move to restrict its choice of quants to the ones belonging to this partner.
        :param context: dictionay. can contains the special key 'source_location_id' in order to force the source location when copying the move

        returns the ID of the backorder move created
        """
        if move.state in ('done', 'cancel'):
            raise UserError(_('You cannot split a move done'))
        if move.state == 'draft':
            #we restrict the split of a draft move because if not confirmed yet, it may be replaced by several other moves in
            #case of phantom bom (with mrp module). And we don't want to deal with this complexity by copying the product that will explode.
            raise UserError(_('You cannot split a draft move. It needs to be confirmed first.'))

        if move.product_qty <= qty or qty == 0:
            return move.id

        uom_obj = self.pool.get('product.uom')
        context = context or {}

        #HALF-UP rounding as only rounding errors will be because of propagation of error from default UoM
        uom_qty = uom_obj._compute_qty_obj(cr, uid, move.product_id.uom_id, qty, move.product_uom, rounding_method='HALF-UP', context=context)
        defaults = {
            'product_uom_qty': uom_qty,
            'procure_method': 'make_to_stock',
            'restrict_lot_id': restrict_lot_id,
            'split_from': move.id,
            'procurement_id': move.procurement_id.id,
            'move_dest_id': move.move_dest_id.id,
            'origin_returned_move_id': move.origin_returned_move_id.id,
        }

        if restrict_partner_id:
            defaults['restrict_partner_id'] = restrict_partner_id

        if context.get('source_location_id'):
            defaults['location_id'] = context['source_location_id']
        new_move = self.copy(cr, uid, move.id, defaults, context=context)

        ctx = context.copy()
        ctx['do_not_propagate'] = True
        self.write(cr, uid, [move.id], {
            'product_uom_qty': move.product_uom_qty - uom_qty,
        }, context=ctx)

        if move.move_dest_id and move.propagate and move.move_dest_id.state not in ('done', 'cancel'):
            new_move_prop = self.split(cr, uid, move.move_dest_id, qty, context=context)
            self.write(cr, uid, [new_move], {'move_dest_id': new_move_prop}, context=context)
        #returning the first element of list returned by action_confirm is ok because we checked it wouldn't be exploded (and
        #thus the result of action_confirm should always be a list of 1 element length)
        return self.action_confirm(cr, uid, [new_move], context=context)[0]


    def get_code_from_locs(self, cr, uid, move, location_id=False, location_dest_id=False, context=None):
        """
        Returns the code the picking type should have.  This can easily be used
        to check if a move is internal or not
        move, location_id and location_dest_id are browse records
        """
        code = 'internal'
        src_loc = location_id or move.location_id
        dest_loc = location_dest_id or move.location_dest_id
        if src_loc.usage == 'internal' and dest_loc.usage != 'internal':
            code = 'outgoing'
        if src_loc.usage != 'internal' and dest_loc.usage == 'internal':
            code = 'incoming'
        return code

    def show_picking(self, cr, uid, ids, context=None):
        assert len(ids) > 0
        picking_id = self.browse(cr, uid, ids[0], context=context).picking_id.id
        if picking_id:
            data_obj = self.pool['ir.model.data']
            view = data_obj.xmlid_to_res_id(cr, uid, 'stock.view_picking_form')
            return {
                 'name': _('Transfer'),
                 'type': 'ir.actions.act_window',
                 'view_type': 'form',
                 'view_mode': 'form',
                 'res_model': 'stock.picking',
                 'views': [(view, 'form')],
                 'view_id': view,
                 'target': 'new',
                 'res_id': picking_id,
            }


class stock_inventory(osv.osv):
    _name = "stock.inventory"
    _description = "Inventory"

    def _get_move_ids_exist(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for inv in self.browse(cr, uid, ids, context=context):
            res[inv.id] = False
            if inv.move_ids:
                res[inv.id] = True
        return res

    def _get_available_filters(self, cr, uid, context=None):
        """
           This function will return the list of filter allowed according to the options checked
           in 'Settings\Warehouse'.

           :rtype: list of tuple
        """
        #default available choices
        res_filter = [('none', _('All products')), ('partial', _('Select products manually')), ('product', _('One product only'))]
        settings_obj = self.pool.get('stock.config.settings')
        config_ids = settings_obj.search(cr, uid, [], limit=1, order='id DESC', context=context)
        #If we don't have updated config until now, all fields are by default false and so should be not dipslayed
        if not config_ids:
            return res_filter

        stock_settings = settings_obj.browse(cr, uid, config_ids[0], context=context)
        if stock_settings.group_stock_tracking_owner:
            res_filter.append(('owner', _('One owner only')))
            res_filter.append(('product_owner', _('One product for a specific owner')))
        if stock_settings.group_stock_production_lot:
            res_filter.append(('lot', _('One Lot/Serial Number')))
        if stock_settings.group_stock_tracking_lot:
            res_filter.append(('pack', _('A Pack')))
        return res_filter

    def _get_total_qty(self, cr, uid, ids, field_name, args, context=None):
        res = {}
        for inv in self.browse(cr, uid, ids, context=context):
            res[inv.id] = sum([x.product_qty for x in inv.line_ids])
        return res

    INVENTORY_STATE_SELECTION = [
        ('draft', 'Draft'),
        ('cancel', 'Cancelled'),
        ('confirm', 'In Progress'),
        ('done', 'Validated'),
    ]

    _columns = {
        'name': fields.char('Inventory Reference', required=True, readonly=True, states={'draft': [('readonly', False)]}, help="Inventory Name."),
        'date': fields.datetime('Inventory Date', required=True, readonly=True, help="The date that will be used for the stock level check of the products and the validation of the stock move related to this inventory."),
        'line_ids': fields.one2many('stock.inventory.line', 'inventory_id', 'Inventories', readonly=False, states={'done': [('readonly', True)]}, help="Inventory Lines.", copy=True),
        'move_ids': fields.one2many('stock.move', 'inventory_id', 'Created Moves', help="Inventory Moves.", states={'done': [('readonly', True)]}),
        'state': fields.selection(INVENTORY_STATE_SELECTION, 'Status', readonly=True, select=True, copy=False),
        'company_id': fields.many2one('res.company', 'Company', required=True, select=True, readonly=True, states={'draft': [('readonly', False)]}),
        'location_id': fields.many2one('stock.location', 'Inventoried Location', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'product_id': fields.many2one('product.product', 'Inventoried Product', readonly=True, states={'draft': [('readonly', False)]}, help="Specify Product to focus your inventory on a particular Product."),
        'package_id': fields.many2one('stock.quant.package', 'Inventoried Pack', readonly=True, states={'draft': [('readonly', False)]}, help="Specify Pack to focus your inventory on a particular Pack."),
        'partner_id': fields.many2one('res.partner', 'Inventoried Owner', readonly=True, states={'draft': [('readonly', False)]}, help="Specify Owner to focus your inventory on a particular Owner."),
        'lot_id': fields.many2one('stock.production.lot', 'Inventoried Lot/Serial Number', readonly=True, states={'draft': [('readonly', False)]}, help="Specify Lot/Serial Number to focus your inventory on a particular Lot/Serial Number.", copy=False),
        # technical field for attrs in view
        'move_ids_exist': fields.function(_get_move_ids_exist, type='boolean', string='Has Stock Moves', help='Check the existance of stock moves linked to this inventory'),
        'filter': fields.selection(_get_available_filters, 'Inventory of', required=True,
                                   help="If you do an entire inventory, you can choose 'All Products' and it will prefill the inventory with the current stock.  If you only do some products  "\
                                      "(e.g. Cycle Counting) you can choose 'Manual Selection of Products' and the system won't propose anything.  You can also let the "\
                                      "system propose for a single product / lot /... "),
        'total_qty': fields.function(_get_total_qty, type="float"),
    }

    def _default_stock_location(self, cr, uid, context=None):
        try:
            warehouse = self.pool.get('ir.model.data').get_object(cr, uid, 'stock', 'warehouse0')
            return warehouse.lot_stock_id.id
        except:
            return False

    _defaults = {
        'date': fields.datetime.now,
        'state': 'draft',
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'stock.inventory', context=c),
        'location_id': _default_stock_location,
        'filter': 'none',
    }

    def reset_real_qty(self, cr, uid, ids, context=None):
        inventory = self.browse(cr, uid, ids[0], context=context)
        line_ids = [line.id for line in inventory.line_ids]
        self.pool.get('stock.inventory.line').write(cr, uid, line_ids, {'product_qty': 0})
        return True

    def action_done(self, cr, uid, ids, context=None):
        """ Finish the inventory
        @return: True
        """
        for inv in self.browse(cr, uid, ids, context=context):
            for inventory_line in inv.line_ids:
                if inventory_line.product_qty < 0 and inventory_line.product_qty != inventory_line.theoretical_qty:
                    raise UserError(_('You cannot set a negative product quantity in an inventory line:\n\t%s - qty: %s' % (inventory_line.product_id.name, inventory_line.product_qty)))
            self.action_check(cr, uid, [inv.id], context=context)
            self.write(cr, uid, [inv.id], {'state': 'done'}, context=context)
            self.post_inventory(cr, uid, inv, context=context)
        return True

    def post_inventory(self, cr, uid, inv, context=None):
        #The inventory is posted as a single step which means quants cannot be moved from an internal location to another using an inventory
        #as they will be moved to inventory loss, and other quants will be created to the encoded quant location. This is a normal behavior
        #as quants cannot be reuse from inventory location (users can still manually move the products before/after the inventory if they want).
        move_obj = self.pool.get('stock.move')
        move_obj.action_done(cr, uid, [x.id for x in inv.move_ids if x.state != 'done'], context=context)

    def action_check(self, cr, uid, ids, context=None):
        """ Checks the inventory and computes the stock move to do
        @return: True
        """
        inventory_line_obj = self.pool.get('stock.inventory.line')
        stock_move_obj = self.pool.get('stock.move')
        for inventory in self.browse(cr, uid, ids, context=context):
            #first remove the existing stock moves linked to this inventory
            move_ids = [move.id for move in inventory.move_ids]
            stock_move_obj.unlink(cr, uid, move_ids, context=context)
            for line in inventory.line_ids:
                #compare the checked quantities on inventory lines to the theorical one
                stock_move = inventory_line_obj._resolve_inventory_line(cr, uid, line, context=context)

    def action_cancel_draft(self, cr, uid, ids, context=None):
        """ Cancels the stock move and change inventory state to draft.
        @return: True
        """
        for inv in self.browse(cr, uid, ids, context=context):
            self.write(cr, uid, [inv.id], {'line_ids': [(5,)]}, context=context)
            self.pool.get('stock.move').action_cancel(cr, uid, [x.id for x in inv.move_ids], context=context)
            self.write(cr, uid, [inv.id], {'state': 'draft'}, context=context)
        return True

    def action_cancel_inventory(self, cr, uid, ids, context=None):
        self.action_cancel_draft(cr, uid, ids, context=context)

    def prepare_inventory(self, cr, uid, ids, context=None):
        inventory_line_obj = self.pool.get('stock.inventory.line')
        for inventory in self.browse(cr, uid, ids, context=context):
            # If there are inventory lines already (e.g. from import), respect those and set their theoretical qty
            line_ids = [line.id for line in inventory.line_ids]
            if not line_ids and inventory.filter != 'partial':
                #compute the inventory lines and create them
                vals = self._get_inventory_lines(cr, uid, inventory, context=context)
                for product_line in vals:
                    inventory_line_obj.create(cr, uid, product_line, context=context)
        return self.write(cr, uid, ids, {'state': 'confirm', 'date': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)})

    def _get_inventory_lines(self, cr, uid, inventory, context=None):
        location_obj = self.pool.get('stock.location')
        product_obj = self.pool.get('product.product')
        location_ids = location_obj.search(cr, uid, [('id', 'child_of', [inventory.location_id.id])], context=context)
        domain = ' location_id in %s'
        args = (tuple(location_ids),)
        if inventory.partner_id:
            domain += ' and owner_id = %s'
            args += (inventory.partner_id.id,)
        if inventory.lot_id:
            domain += ' and lot_id = %s'
            args += (inventory.lot_id.id,)
        if inventory.product_id:
            domain += ' and product_id = %s'
            args += (inventory.product_id.id,)
        if inventory.package_id:
            domain += ' and package_id = %s'
            args += (inventory.package_id.id,)

        cr.execute('''
           SELECT product_id, sum(qty) as product_qty, location_id, lot_id as prod_lot_id, package_id, owner_id as partner_id
           FROM stock_quant WHERE''' + domain + '''
           GROUP BY product_id, location_id, lot_id, package_id, partner_id
        ''', args)
        vals = []
        for product_line in cr.dictfetchall():
            #replace the None the dictionary by False, because falsy values are tested later on
            for key, value in product_line.items():
                if not value:
                    product_line[key] = False
            product_line['inventory_id'] = inventory.id
            product_line['theoretical_qty'] = product_line['product_qty']
            if product_line['product_id']:
                product = product_obj.browse(cr, uid, product_line['product_id'], context=context)
                product_line['product_uom_id'] = product.uom_id.id
            vals.append(product_line)
        return vals

    def _check_filter_product(self, cr, uid, ids, context=None):
        for inventory in self.browse(cr, uid, ids, context=context):
            if inventory.filter == 'none' and inventory.product_id and inventory.location_id and inventory.lot_id:
                return True
            if inventory.filter not in ('product', 'product_owner') and inventory.product_id:
                return False
            if inventory.filter != 'lot' and inventory.lot_id:
                return False
            if inventory.filter not in ('owner', 'product_owner') and inventory.partner_id:
                return False
            if inventory.filter != 'pack' and inventory.package_id:
                return False
        return True

    def onchange_filter(self, cr, uid, ids, filter, context=None):
        to_clean = { 'value': {} }
        if filter not in ('product', 'product_owner'):
            to_clean['value']['product_id'] = False
        if filter != 'lot':
            to_clean['value']['lot_id'] = False
        if filter not in ('owner', 'product_owner'):
            to_clean['value']['partner_id'] = False
        if filter != 'pack':
            to_clean['value']['package_id'] = False
        return to_clean

    _constraints = [
        (_check_filter_product, 'The selected inventory options are not coherent.',
            ['filter', 'product_id', 'lot_id', 'partner_id', 'package_id']),
    ]

class stock_inventory_line(osv.osv):
    _name = "stock.inventory.line"
    _description = "Inventory Line"
    _order = "inventory_id, location_name, product_code, product_name, prodlot_name"

    def _get_product_name_change(self, cr, uid, ids, context=None):
        return self.pool.get('stock.inventory.line').search(cr, uid, [('product_id', 'in', ids)], context=context)

    def _get_location_change(self, cr, uid, ids, context=None):
        return self.pool.get('stock.inventory.line').search(cr, uid, [('location_id', 'in', ids)], context=context)

    def _get_prodlot_change(self, cr, uid, ids, context=None):
        return self.pool.get('stock.inventory.line').search(cr, uid, [('prod_lot_id', 'in', ids)], context=context)

    def _get_theoretical_qty(self, cr, uid, ids, name, args, context=None):
        res = {}
        quant_obj = self.pool["stock.quant"]
        uom_obj = self.pool["product.uom"]
        for line in self.browse(cr, uid, ids, context=context):
            quant_ids = self._get_quants(cr, uid, line, context=context)
            quants = quant_obj.browse(cr, uid, quant_ids, context=context)
            tot_qty = sum([x.qty for x in quants])
            if line.product_uom_id and line.product_id.uom_id.id != line.product_uom_id.id:
                tot_qty = uom_obj._compute_qty_obj(cr, uid, line.product_id.uom_id, tot_qty, line.product_uom_id, context=context)
            res[line.id] = tot_qty
        return res

    _columns = {
        'inventory_id': fields.many2one('stock.inventory', 'Inventory', ondelete='cascade', select=True),
        'location_id': fields.many2one('stock.location', 'Location', required=True, select=True),
        'product_id': fields.many2one('product.product', 'Product', required=True, select=True),
        'package_id': fields.many2one('stock.quant.package', 'Pack', select=True),
        'product_uom_id': fields.many2one('product.uom', 'Product Unit of Measure', required=True),
        'product_qty': fields.float('Checked Quantity', digits_compute=dp.get_precision('Product Unit of Measure')),
        'company_id': fields.related('inventory_id', 'company_id', type='many2one', relation='res.company', string='Company', store=True, select=True, readonly=True),
        'prod_lot_id': fields.many2one('stock.production.lot', 'Serial Number', domain="[('product_id','=',product_id)]"),
        'state': fields.related('inventory_id', 'state', type='char', string='Status', readonly=True),
        'theoretical_qty': fields.function(_get_theoretical_qty, type='float', digits_compute=dp.get_precision('Product Unit of Measure'),
                                           store={'stock.inventory.line': (lambda self, cr, uid, ids, c={}: ids, ['location_id', 'product_id', 'package_id', 'product_uom_id', 'company_id', 'prod_lot_id', 'partner_id'], 20),},
                                           readonly=True, string="Theoretical Quantity"),
        'partner_id': fields.many2one('res.partner', 'Owner'),
        'product_name': fields.related('product_id', 'name', type='char', string='Product Name', store={
                                                                                            'product.product': (_get_product_name_change, ['name', 'default_code'], 20),
                                                                                            'stock.inventory.line': (lambda self, cr, uid, ids, c={}: ids, ['product_id'], 20),}),
        'product_code': fields.related('product_id', 'default_code', type='char', string='Product Code', store={
                                                                                            'product.product': (_get_product_name_change, ['name', 'default_code'], 20),
                                                                                            'stock.inventory.line': (lambda self, cr, uid, ids, c={}: ids, ['product_id'], 20),}),
        'location_name': fields.related('location_id', 'complete_name', type='char', string='Location Name', store={
                                                                                            'stock.location': (_get_location_change, ['name', 'location_id', 'active'], 20),
                                                                                            'stock.inventory.line': (lambda self, cr, uid, ids, c={}: ids, ['location_id'], 20),}),
        'prodlot_name': fields.related('prod_lot_id', 'name', type='char', string='Serial Number Name', store={
                                                                                            'stock.production.lot': (_get_prodlot_change, ['name'], 20),
                                                                                            'stock.inventory.line': (lambda self, cr, uid, ids, c={}: ids, ['prod_lot_id'], 20),}),
    }

    _defaults = {
        'product_qty': 0,
        'product_uom_id': lambda self, cr, uid, ctx=None: self.pool['ir.model.data'].get_object_reference(cr, uid, 'product', 'product_uom_unit')[1]
    }

    def create(self, cr, uid, values, context=None):
        if context is None:
            context = {}
        product_obj = self.pool.get('product.product')
        if 'product_id' in values and not 'product_uom_id' in values:
            values['product_uom_id'] = product_obj.browse(cr, uid, values.get('product_id'), context=context).uom_id.id
        return super(stock_inventory_line, self).create(cr, uid, values, context=context)

    def _get_quants(self, cr, uid, line, context=None):
        quant_obj = self.pool["stock.quant"]
        dom = [('company_id', '=', line.company_id.id), ('location_id', '=', line.location_id.id), ('lot_id', '=', line.prod_lot_id.id),
                        ('product_id','=', line.product_id.id), ('owner_id', '=', line.partner_id.id), ('package_id', '=', line.package_id.id)]
        quants = quant_obj.search(cr, uid, dom, context=context)
        return quants

    def onchange_createline(self, cr, uid, ids, location_id=False, product_id=False, uom_id=False, package_id=False, prod_lot_id=False, partner_id=False, company_id=False, context=None):
        quant_obj = self.pool["stock.quant"]
        uom_obj = self.pool["product.uom"]
        res = {'value': {}}
        # If no UoM already put the default UoM of the product
        if product_id:
            product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
            uom = self.pool['product.uom'].browse(cr, uid, uom_id, context=context)
            if product.uom_id.category_id.id != uom.category_id.id:
                res['value']['product_uom_id'] = product.uom_id.id
                res['domain'] = {'product_uom_id': [('category_id','=',product.uom_id.category_id.id)]}
                uom_id = product.uom_id.id
        # Calculate theoretical quantity by searching the quants as in quants_get
        if product_id and location_id:
            product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
            if not company_id:
                company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
            dom = [('company_id', '=', company_id), ('location_id', '=', location_id), ('lot_id', '=', prod_lot_id),
                        ('product_id','=', product_id), ('owner_id', '=', partner_id), ('package_id', '=', package_id)]
            quants = quant_obj.search(cr, uid, dom, context=context)
            th_qty = sum([x.qty for x in quant_obj.browse(cr, uid, quants, context=context)])
            if product_id and uom_id and product.uom_id.id != uom_id:
                th_qty = uom_obj._compute_qty(cr, uid, product.uom_id.id, th_qty, uom_id)
            res['value']['theoretical_qty'] = th_qty
            res['value']['product_qty'] = th_qty
        return res

    def _resolve_inventory_line(self, cr, uid, inventory_line, context=None):
        stock_move_obj = self.pool.get('stock.move')
        quant_obj = self.pool.get('stock.quant')
        diff = inventory_line.theoretical_qty - inventory_line.product_qty
        if not diff:
            return
        #each theorical_lines where difference between theoretical and checked quantities is not 0 is a line for which we need to create a stock move
        vals = {
            'name': _('INV:') + (inventory_line.inventory_id.name or ''),
            'product_id': inventory_line.product_id.id,
            'product_uom': inventory_line.product_uom_id.id,
            'date': inventory_line.inventory_id.date,
            'company_id': inventory_line.inventory_id.company_id.id,
            'inventory_id': inventory_line.inventory_id.id,
            'state': 'confirmed',
            'restrict_lot_id': inventory_line.prod_lot_id.id,
            'restrict_partner_id': inventory_line.partner_id.id,
         }
        inventory_location_id = inventory_line.product_id.property_stock_inventory.id
        if diff < 0:
            #found more than expected
            vals['location_id'] = inventory_location_id
            vals['location_dest_id'] = inventory_line.location_id.id
            vals['product_uom_qty'] = -diff
        else:
            #found less than expected
            vals['location_id'] = inventory_line.location_id.id
            vals['location_dest_id'] = inventory_location_id
            vals['product_uom_qty'] = diff
        move_id = stock_move_obj.create(cr, uid, vals, context=context)
        move = stock_move_obj.browse(cr, uid, move_id, context=context)
        if diff > 0:
            domain = [('qty', '>', 0.0), ('package_id', '=', inventory_line.package_id.id), ('lot_id', '=', inventory_line.prod_lot_id.id), ('location_id', '=', inventory_line.location_id.id)]
            preferred_domain_list = [[('reservation_id', '=', False)], [('reservation_id.inventory_id', '!=', inventory_line.inventory_id.id)]]
            quants = quant_obj.quants_get_preferred_domain(cr, uid, move.product_qty, move, domain=domain, preferred_domain_list=preferred_domain_list)
            quant_obj.quants_reserve(cr, uid, quants, move, context=context)
        elif inventory_line.package_id:
            stock_move_obj.action_done(cr, uid, move_id, context=context)
            quants = [x.id for x in move.quant_ids]
            quant_obj.write(cr, uid, quants, {'package_id': inventory_line.package_id.id}, context=context)
            res = quant_obj.search(cr, uid, [('qty', '<', 0.0), ('product_id', '=', move.product_id.id),
                                    ('location_id', '=', move.location_dest_id.id), ('package_id', '!=', False)], limit=1, context=context)
            if res:
                for quant in move.quant_ids:
                    if quant.location_id.id == move.location_dest_id.id: #To avoid we take a quant that was reconcile already
                        quant_obj._quant_reconcile_negative(cr, uid, quant, move, context=context)
        return move_id

    # Should be left out in next version
    def restrict_change(self, cr, uid, ids, theoretical_qty, context=None):
        return {}

    # Should be left out in next version
    def on_change_product_id(self, cr, uid, ids, product, uom, theoretical_qty, context=None):
        """ Changes UoM
        @param location_id: Location id
        @param product: Changed product_id
        @param uom: UoM product
        @return:  Dictionary of changed values
        """
        if not product:
            return {'value': {'product_uom_id': False}}
        obj_product = self.pool.get('product.product').browse(cr, uid, product, context=context)
        return {'value': {'product_uom_id': uom or obj_product.uom_id.id}}


#----------------------------------------------------------
# Stock Warehouse
#----------------------------------------------------------
class stock_warehouse(osv.osv):
    _name = "stock.warehouse"
    _description = "Warehouse"

    _columns = {
        'name': fields.char('Warehouse Name', required=True, select=True),
        'company_id': fields.many2one('res.company', 'Company', required=True, readonly=True, select=True),
        'partner_id': fields.many2one('res.partner', 'Address'),
        'view_location_id': fields.many2one('stock.location', 'View Location', required=True, domain=[('usage', '=', 'view')]),
        'lot_stock_id': fields.many2one('stock.location', 'Location Stock', domain=[('usage', '=', 'internal')], required=True),
        'code': fields.char('Short Name', size=5, required=True, help="Short name used to identify your warehouse"),
        'route_ids': fields.many2many('stock.location.route', 'stock_route_warehouse', 'warehouse_id', 'route_id', 'Routes', domain="[('warehouse_selectable', '=', True)]", help='Defaults routes through the warehouse'),
        'reception_steps': fields.selection([
            ('one_step', 'Receive goods directly in stock (1 step)'),
            ('two_steps', 'Unload in input location then go to stock (2 steps)'),
            ('three_steps', 'Unload in input location, go through a quality control before being admitted in stock (3 steps)')], 'Incoming Shipments', 
                                            help="Default incoming route to follow", required=True),
        'delivery_steps': fields.selection([
            ('ship_only', 'Ship directly from stock (Ship only)'),
            ('pick_ship', 'Bring goods to output location before shipping (Pick + Ship)'),
            ('pick_pack_ship', 'Make packages into a dedicated location, then bring them to the output location for shipping (Pick + Pack + Ship)')], 'Outgoing Shippings', 
                                           help="Default outgoing route to follow", required=True),
        'wh_input_stock_loc_id': fields.many2one('stock.location', 'Input Location'),
        'wh_qc_stock_loc_id': fields.many2one('stock.location', 'Quality Control Location'),
        'wh_output_stock_loc_id': fields.many2one('stock.location', 'Output Location'),
        'wh_pack_stock_loc_id': fields.many2one('stock.location', 'Packing Location'),
        'mto_pull_id': fields.many2one('procurement.rule', 'MTO rule'),
        'pick_type_id': fields.many2one('stock.picking.type', 'Pick Type'),
        'pack_type_id': fields.many2one('stock.picking.type', 'Pack Type'),
        'out_type_id': fields.many2one('stock.picking.type', 'Out Type'),
        'in_type_id': fields.many2one('stock.picking.type', 'In Type'),
        'int_type_id': fields.many2one('stock.picking.type', 'Internal Type'),
        'crossdock_route_id': fields.many2one('stock.location.route', 'Crossdock Route'),
        'reception_route_id': fields.many2one('stock.location.route', 'Receipt Route'),
        'delivery_route_id': fields.many2one('stock.location.route', 'Delivery Route'),
        'resupply_from_wh': fields.boolean('Resupply From Other Warehouses', help='Unused field'),
        'resupply_wh_ids': fields.many2many('stock.warehouse', 'stock_wh_resupply_table', 'supplied_wh_id', 'supplier_wh_id', 'Resupply Warehouses'),
        'resupply_route_ids': fields.one2many('stock.location.route', 'supplied_wh_id', 'Resupply Routes', 
                                              help="Routes will be created for these resupply warehouses and you can select them on products and product categories"),
        'default_resupply_wh_id': fields.many2one('stock.warehouse', 'Default Resupply Warehouse', help="Goods will always be resupplied from this warehouse"),
    }

    def onchange_filter_default_resupply_wh_id(self, cr, uid, ids, default_resupply_wh_id, resupply_wh_ids, context=None):
        resupply_wh_ids = set([x['id'] for x in (self.resolve_2many_commands(cr, uid, 'resupply_wh_ids', resupply_wh_ids, ['id']))])
        if default_resupply_wh_id: #If we are removing the default resupply, we don't have default_resupply_wh_id 
            resupply_wh_ids.add(default_resupply_wh_id)
        resupply_wh_ids = list(resupply_wh_ids)        
        return {'value': {'resupply_wh_ids': resupply_wh_ids}}

    def _get_external_transit_location(self, cr, uid, warehouse, context=None):
        ''' returns browse record of inter company transit location, if found'''
        data_obj = self.pool.get('ir.model.data')
        location_obj = self.pool.get('stock.location')
        try:
            inter_wh_loc = data_obj.get_object_reference(cr, uid, 'stock', 'stock_location_inter_wh')[1]
        except:
            return False
        return location_obj.browse(cr, uid, inter_wh_loc, context=context)

    def _get_inter_wh_route(self, cr, uid, warehouse, wh, context=None):
        return {
            'name': _('%s: Supply Product from %s') % (warehouse.name, wh.name),
            'warehouse_selectable': False,
            'product_selectable': True,
            'product_categ_selectable': True,
            'supplied_wh_id': warehouse.id,
            'supplier_wh_id': wh.id,
        }

    def _create_resupply_routes(self, cr, uid, warehouse, supplier_warehouses, default_resupply_wh, context=None):
        route_obj = self.pool.get('stock.location.route')
        pull_obj = self.pool.get('procurement.rule')
        #create route selectable on the product to resupply the warehouse from another one
        external_transit_location = self._get_external_transit_location(cr, uid, warehouse, context=context)
        internal_transit_location = warehouse.company_id.internal_transit_location_id
        input_loc = warehouse.wh_input_stock_loc_id
        if warehouse.reception_steps == 'one_step':
            input_loc = warehouse.lot_stock_id
        for wh in supplier_warehouses:
            transit_location = wh.company_id.id == warehouse.company_id.id and internal_transit_location or external_transit_location
            if transit_location:
                output_loc = wh.wh_output_stock_loc_id
                if wh.delivery_steps == 'ship_only':
                    output_loc = wh.lot_stock_id
                    # Create extra MTO rule (only for 'ship only' because in the other cases MTO rules already exists)
                    mto_pull_vals = self._get_mto_pull_rule(cr, uid, wh, [(output_loc, transit_location, wh.out_type_id.id)], context=context)[0]
                    pull_obj.create(cr, uid, mto_pull_vals, context=context)
                inter_wh_route_vals = self._get_inter_wh_route(cr, uid, warehouse, wh, context=context)
                inter_wh_route_id = route_obj.create(cr, uid, vals=inter_wh_route_vals, context=context)
                values = [(output_loc, transit_location, wh.out_type_id.id, wh), (transit_location, input_loc, warehouse.in_type_id.id, warehouse)]
                pull_rules_list = self._get_supply_pull_rules(cr, uid, wh.id, values, inter_wh_route_id, context=context)
                for pull_rule in pull_rules_list:
                    pull_obj.create(cr, uid, vals=pull_rule, context=context)
                #if the warehouse is also set as default resupply method, assign this route automatically to the warehouse
                if default_resupply_wh and default_resupply_wh.id == wh.id:
                    self.write(cr, uid, [warehouse.id, wh.id], {'route_ids': [(4, inter_wh_route_id)]}, context=context)

    _defaults = {
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'stock.inventory', context=c),
        'reception_steps': 'one_step',
        'delivery_steps': 'ship_only',
    }
    _sql_constraints = [
        ('warehouse_name_uniq', 'unique(name, company_id)', 'The name of the warehouse must be unique per company!'),
        ('warehouse_code_uniq', 'unique(code, company_id)', 'The code of the warehouse must be unique per company!'),
    ]

    def _get_partner_locations(self, cr, uid, ids, context=None):
        ''' returns a tuple made of the browse record of customer location and the browse record of supplier location'''
        data_obj = self.pool.get('ir.model.data')
        location_obj = self.pool.get('stock.location')
        try:
            customer_loc = data_obj.get_object_reference(cr, uid, 'stock', 'stock_location_customers')[1]
            supplier_loc = data_obj.get_object_reference(cr, uid, 'stock', 'stock_location_suppliers')[1]
        except:
            customer_loc = location_obj.search(cr, uid, [('usage', '=', 'customer')], context=context)
            customer_loc = customer_loc and customer_loc[0] or False
            supplier_loc = location_obj.search(cr, uid, [('usage', '=', 'supplier')], context=context)
            supplier_loc = supplier_loc and supplier_loc[0] or False
        if not (customer_loc and supplier_loc):
            raise UserError(_('Can\'t find any customer or supplier location.'))
        return location_obj.browse(cr, uid, [customer_loc, supplier_loc], context=context)

    def _location_used(self, cr, uid, location_id, warehouse, context=None):
        pull_obj = self.pool['procurement.rule']
        push_obj = self.pool['stock.location.path']

        domain = ['&', ('route_id', 'not in', [x.id for x in warehouse.route_ids]),
                       '|', ('location_src_id', '=', location_id),                      # noqa
                            ('location_id', '=', location_id)
                  ]
        pulls = pull_obj.search_count(cr, uid, domain, context=context)

        domain = ['&', ('route_id', 'not in', [x.id for x in warehouse.route_ids]),
                       '|', ('location_from_id', '=', location_id),                     # noqa
                            ('location_dest_id', '=', location_id)
                  ]
        pushs = push_obj.search_count(cr, uid, domain, context=context)
        if pulls or pushs:
            return True
        return False

    def switch_location(self, cr, uid, ids, warehouse, new_reception_step=False, new_delivery_step=False, context=None):
        location_obj = self.pool.get('stock.location')

        new_reception_step = new_reception_step or warehouse.reception_steps
        new_delivery_step = new_delivery_step or warehouse.delivery_steps
        if warehouse.reception_steps != new_reception_step:
            if not self._location_used(cr, uid, warehouse.wh_input_stock_loc_id.id, warehouse, context=context):
                location_obj.write(cr, uid, [warehouse.wh_input_stock_loc_id.id, warehouse.wh_qc_stock_loc_id.id], {'active': False}, context=context)
            if new_reception_step != 'one_step':
                location_obj.write(cr, uid, warehouse.wh_input_stock_loc_id.id, {'active': True}, context=context)
            if new_reception_step == 'three_steps':
                location_obj.write(cr, uid, warehouse.wh_qc_stock_loc_id.id, {'active': True}, context=context)

        if warehouse.delivery_steps != new_delivery_step:
            if not self._location_used(cr, uid, warehouse.wh_output_stock_loc_id.id, warehouse, context=context):
                location_obj.write(cr, uid, [warehouse.wh_output_stock_loc_id.id], {'active': False}, context=context)
            if not self._location_used(cr, uid, warehouse.wh_pack_stock_loc_id.id, warehouse, context=context):
                location_obj.write(cr, uid, [warehouse.wh_pack_stock_loc_id.id], {'active': False}, context=context)
            if new_delivery_step != 'ship_only':
                location_obj.write(cr, uid, warehouse.wh_output_stock_loc_id.id, {'active': True}, context=context)
            if new_delivery_step == 'pick_pack_ship':
                location_obj.write(cr, uid, warehouse.wh_pack_stock_loc_id.id, {'active': True}, context=context)
        return True

    def _get_reception_delivery_route(self, cr, uid, warehouse, route_name, context=None):
        return {
            'name': self._format_routename(cr, uid, warehouse, route_name, context=context),
            'product_categ_selectable': True,
            'product_selectable': False,
            'sequence': 10,
        }

    def _get_supply_pull_rules(self, cr, uid, supply_warehouse, values, new_route_id, context=None):
        pull_rules_list = []
        for from_loc, dest_loc, pick_type_id, warehouse in values:
            pull_rules_list.append({
                'name': self._format_rulename(cr, uid, warehouse, from_loc, dest_loc, context=context),
                'location_src_id': from_loc.id,
                'location_id': dest_loc.id,
                'route_id': new_route_id,
                'action': 'move',
                'picking_type_id': pick_type_id,
                'procure_method': warehouse.lot_stock_id.id != from_loc.id and 'make_to_order' or 'make_to_stock', # first part of the resuply route is MTS
                'warehouse_id': warehouse.id,
                'propagate_warehouse_id': supply_warehouse,
            })
        return pull_rules_list

    def _get_push_pull_rules(self, cr, uid, warehouse, active, values, new_route_id, context=None):
        first_rule = True
        push_rules_list = []
        pull_rules_list = []
        for from_loc, dest_loc, pick_type_id in values:
            push_rules_list.append({
                'name': self._format_rulename(cr, uid, warehouse, from_loc, dest_loc, context=context),
                'location_from_id': from_loc.id,
                'location_dest_id': dest_loc.id,
                'route_id': new_route_id,
                'auto': 'manual',
                'picking_type_id': pick_type_id,
                'active': active,
                'warehouse_id': warehouse.id,
            })
            pull_rules_list.append({
                'name': self._format_rulename(cr, uid, warehouse, from_loc, dest_loc, context=context),
                'location_src_id': from_loc.id,
                'location_id': dest_loc.id,
                'route_id': new_route_id,
                'action': 'move',
                'picking_type_id': pick_type_id,
                'procure_method': first_rule is True and 'make_to_stock' or 'make_to_order',
                'active': active,
                'warehouse_id': warehouse.id,
            })
            first_rule = False
        return push_rules_list, pull_rules_list

    def _get_mto_route(self, cr, uid, context=None):
        route_obj = self.pool.get('stock.location.route')
        data_obj = self.pool.get('ir.model.data')
        try:
            mto_route_id = data_obj.get_object_reference(cr, uid, 'stock', 'route_warehouse0_mto')[1]
        except:
            mto_route_id = route_obj.search(cr, uid, [('name', 'like', _('Make To Order'))], context=context)
            mto_route_id = mto_route_id and mto_route_id[0] or False
        if not mto_route_id:
            raise UserError(_('Can\'t find any generic Make To Order route.'))
        return mto_route_id

    def _check_remove_mto_resupply_rules(self, cr, uid, warehouse, context=None):
        """ Checks that the moves from the different """
        pull_obj = self.pool.get('procurement.rule')
        mto_route_id = self._get_mto_route(cr, uid, context=context)
        rules = pull_obj.search(cr, uid, ['&', ('location_src_id', '=', warehouse.lot_stock_id.id), ('location_id.usage', '=', 'transit')], context=context)
        pull_obj.unlink(cr, uid, rules, context=context)

    def _get_mto_pull_rule(self, cr, uid, warehouse, values, context=None):
        mto_route_id = self._get_mto_route(cr, uid, context=context)
        res = []
        for value in values:
            from_loc, dest_loc, pick_type_id = value
            res += [{
            'name': self._format_rulename(cr, uid, warehouse, from_loc, dest_loc, context=context) + _(' MTO'),
            'location_src_id': from_loc.id,
            'location_id': dest_loc.id,
            'route_id': mto_route_id,
            'action': 'move',
            'picking_type_id': pick_type_id,
            'procure_method': 'make_to_order',
            'active': True,
            'warehouse_id': warehouse.id,
            }]
        return res

    def _get_crossdock_route(self, cr, uid, warehouse, route_name, context=None):
        return {
            'name': self._format_routename(cr, uid, warehouse, route_name, context=context),
            'warehouse_selectable': False,
            'product_selectable': True,
            'product_categ_selectable': True,
            'active': warehouse.delivery_steps != 'ship_only' and warehouse.reception_steps != 'one_step',
            'sequence': 20,
        }

    def create_routes(self, cr, uid, ids, warehouse, context=None):
        wh_route_ids = []
        route_obj = self.pool.get('stock.location.route')
        pull_obj = self.pool.get('procurement.rule')
        push_obj = self.pool.get('stock.location.path')
        routes_dict = self.get_routes_dict(cr, uid, ids, warehouse, context=context)
        #create reception route and rules
        route_name, values = routes_dict[warehouse.reception_steps]
        route_vals = self._get_reception_delivery_route(cr, uid, warehouse, route_name, context=context)
        reception_route_id = route_obj.create(cr, uid, route_vals, context=context)
        wh_route_ids.append((4, reception_route_id))
        push_rules_list, pull_rules_list = self._get_push_pull_rules(cr, uid, warehouse, True, values, reception_route_id, context=context)
        #create the push/procurement rules
        for push_rule in push_rules_list:
            push_obj.create(cr, uid, vals=push_rule, context=context)
        for pull_rule in pull_rules_list:
            #all procurement rules in reception route are mto, because we don't want to wait for the scheduler to trigger an orderpoint on input location
            pull_rule['procure_method'] = 'make_to_order'
            pull_obj.create(cr, uid, vals=pull_rule, context=context)

        #create MTS route and procurement rules for delivery and a specific route MTO to be set on the product
        route_name, values = routes_dict[warehouse.delivery_steps]
        route_vals = self._get_reception_delivery_route(cr, uid, warehouse, route_name, context=context)
        #create the route and its procurement rules
        delivery_route_id = route_obj.create(cr, uid, route_vals, context=context)
        wh_route_ids.append((4, delivery_route_id))
        dummy, pull_rules_list = self._get_push_pull_rules(cr, uid, warehouse, True, values, delivery_route_id, context=context)
        for pull_rule in pull_rules_list:
            pull_obj.create(cr, uid, vals=pull_rule, context=context)
        #create MTO procurement rule and link it to the generic MTO route
        mto_pull_vals = self._get_mto_pull_rule(cr, uid, warehouse, values, context=context)[0]
        mto_pull_id = pull_obj.create(cr, uid, mto_pull_vals, context=context)

        #create a route for cross dock operations, that can be set on products and product categories
        route_name, values = routes_dict['crossdock']
        crossdock_route_vals = self._get_crossdock_route(cr, uid, warehouse, route_name, context=context)
        crossdock_route_id = route_obj.create(cr, uid, vals=crossdock_route_vals, context=context)
        wh_route_ids.append((4, crossdock_route_id))
        dummy, pull_rules_list = self._get_push_pull_rules(cr, uid, warehouse, warehouse.delivery_steps != 'ship_only' and warehouse.reception_steps != 'one_step', values, crossdock_route_id, context=context)
        for pull_rule in pull_rules_list:
            # Fixed cross-dock is logically mto
            pull_rule['procure_method'] = 'make_to_order'
            pull_obj.create(cr, uid, vals=pull_rule, context=context)

        #create route selectable on the product to resupply the warehouse from another one
        self._create_resupply_routes(cr, uid, warehouse, warehouse.resupply_wh_ids, warehouse.default_resupply_wh_id, context=context)

        #return routes and mto procurement rule to store on the warehouse
        return {
            'route_ids': wh_route_ids,
            'mto_pull_id': mto_pull_id,
            'reception_route_id': reception_route_id,
            'delivery_route_id': delivery_route_id,
            'crossdock_route_id': crossdock_route_id,
        }

    def change_route(self, cr, uid, ids, warehouse, new_reception_step=False, new_delivery_step=False, context=None):
        picking_type_obj = self.pool.get('stock.picking.type')
        pull_obj = self.pool.get('procurement.rule')
        push_obj = self.pool.get('stock.location.path')
        route_obj = self.pool.get('stock.location.route')
        new_reception_step = new_reception_step or warehouse.reception_steps
        new_delivery_step = new_delivery_step or warehouse.delivery_steps

        #change the default source and destination location and (de)activate picking types
        input_loc = warehouse.wh_input_stock_loc_id
        if new_reception_step == 'one_step':
            input_loc = warehouse.lot_stock_id
        output_loc = warehouse.wh_output_stock_loc_id
        if new_delivery_step == 'ship_only':
            output_loc = warehouse.lot_stock_id
        picking_type_obj.write(cr, uid, warehouse.in_type_id.id, {'default_location_dest_id': input_loc.id}, context=context)
        picking_type_obj.write(cr, uid, warehouse.out_type_id.id, {'default_location_src_id': output_loc.id}, context=context)
        picking_type_obj.write(cr, uid, warehouse.pick_type_id.id, {
                'active': new_delivery_step != 'ship_only',
                'default_location_dest_id': output_loc.id if new_delivery_step == 'pick_ship' else warehouse.wh_pack_stock_loc_id.id,
            }, context=context)
        picking_type_obj.write(cr, uid, warehouse.pack_type_id.id, {'active': new_delivery_step == 'pick_pack_ship'}, context=context)

        routes_dict = self.get_routes_dict(cr, uid, ids, warehouse, context=context)
        #update delivery route and rules: unlink the existing rules of the warehouse delivery route and recreate it
        pull_obj.unlink(cr, uid, [pu.id for pu in warehouse.delivery_route_id.pull_ids], context=context)
        route_name, values = routes_dict[new_delivery_step]
        route_obj.write(cr, uid, warehouse.delivery_route_id.id, {'name': self._format_routename(cr, uid, warehouse, route_name, context=context)}, context=context)
        dummy, pull_rules_list = self._get_push_pull_rules(cr, uid, warehouse, True, values, warehouse.delivery_route_id.id, context=context)
        #create the procurement rules
        for pull_rule in pull_rules_list:
            pull_obj.create(cr, uid, vals=pull_rule, context=context)

        #update receipt route and rules: unlink the existing rules of the warehouse receipt route and recreate it
        pull_obj.unlink(cr, uid, [pu.id for pu in warehouse.reception_route_id.pull_ids], context=context)
        push_obj.unlink(cr, uid, [pu.id for pu in warehouse.reception_route_id.push_ids], context=context)
        route_name, values = routes_dict[new_reception_step]
        route_obj.write(cr, uid, warehouse.reception_route_id.id, {'name': self._format_routename(cr, uid, warehouse, route_name, context=context)}, context=context)
        push_rules_list, pull_rules_list = self._get_push_pull_rules(cr, uid, warehouse, True, values, warehouse.reception_route_id.id, context=context)
        #create the push/procurement rules
        for push_rule in push_rules_list:
            push_obj.create(cr, uid, vals=push_rule, context=context)
        for pull_rule in pull_rules_list:
            #all procurement rules in receipt route are mto, because we don't want to wait for the scheduler to trigger an orderpoint on input location
            pull_rule['procure_method'] = 'make_to_order'
            pull_obj.create(cr, uid, vals=pull_rule, context=context)

        route_obj.write(cr, uid, warehouse.crossdock_route_id.id, {'active': new_reception_step != 'one_step' and new_delivery_step != 'ship_only'}, context=context)

        #change MTO rule
        dummy, values = routes_dict[new_delivery_step]
        mto_pull_vals = self._get_mto_pull_rule(cr, uid, warehouse, values, context=context)[0]
        pull_obj.write(cr, uid, warehouse.mto_pull_id.id, mto_pull_vals, context=context)
        return True

    def create_sequences_and_picking_types(self, cr, uid, warehouse, context=None):
        seq_obj = self.pool.get('ir.sequence')
        picking_type_obj = self.pool.get('stock.picking.type')
        #create new sequences
        in_seq_id = seq_obj.create(cr, SUPERUSER_ID, {'name': warehouse.name + _(' Sequence in'), 'prefix': warehouse.code + '/IN/', 'padding': 5}, context=context)
        out_seq_id = seq_obj.create(cr, SUPERUSER_ID, {'name': warehouse.name + _(' Sequence out'), 'prefix': warehouse.code + '/OUT/', 'padding': 5}, context=context)
        pack_seq_id = seq_obj.create(cr, SUPERUSER_ID, {'name': warehouse.name + _(' Sequence packing'), 'prefix': warehouse.code + '/PACK/', 'padding': 5}, context=context)
        pick_seq_id = seq_obj.create(cr, SUPERUSER_ID, {'name': warehouse.name + _(' Sequence picking'), 'prefix': warehouse.code + '/PICK/', 'padding': 5}, context=context)
        int_seq_id = seq_obj.create(cr, SUPERUSER_ID, {'name': warehouse.name + _(' Sequence internal'), 'prefix': warehouse.code + '/INT/', 'padding': 5}, context=context)

        wh_stock_loc = warehouse.lot_stock_id
        wh_input_stock_loc = warehouse.wh_input_stock_loc_id
        wh_output_stock_loc = warehouse.wh_output_stock_loc_id
        wh_pack_stock_loc = warehouse.wh_pack_stock_loc_id

        #create in, out, internal picking types for warehouse
        input_loc = wh_input_stock_loc
        if warehouse.reception_steps == 'one_step':
            input_loc = wh_stock_loc
        output_loc = wh_output_stock_loc
        if warehouse.delivery_steps == 'ship_only':
            output_loc = wh_stock_loc

        #choose the next available color for the picking types of this warehouse
        color = 0
        available_colors = [0, 3, 4, 5, 6, 7, 8, 1, 2]  # put white color first
        all_used_colors = self.pool.get('stock.picking.type').search_read(cr, uid, [('warehouse_id', '!=', False), ('color', '!=', False)], ['color'], order='color')
        #don't use sets to preserve the list order
        for x in all_used_colors:
            if x['color'] in available_colors:
                available_colors.remove(x['color'])
        if available_colors:
            color = available_colors[0]

        #order the picking types with a sequence allowing to have the following suit for each warehouse: reception, internal, pick, pack, ship. 
        max_sequence = self.pool.get('stock.picking.type').search_read(cr, uid, [], ['sequence'], order='sequence desc')
        max_sequence = max_sequence and max_sequence[0]['sequence'] or 0
        internal_active_false = (warehouse.reception_steps == 'one_step') and (warehouse.delivery_steps == 'ship_only')
        internal_active_false = internal_active_false and not self.user_has_groups(cr, uid, 'stock.group_locations')

        in_type_id = picking_type_obj.create(cr, uid, vals={
            'name': _('Receipts'),
            'warehouse_id': warehouse.id,
            'code': 'incoming',
            'use_create_lots': True,
            'use_existing_lots': False,
            'sequence_id': in_seq_id,
            'default_location_src_id': False,
            'default_location_dest_id': input_loc.id,
            'sequence': max_sequence + 1,
            'color': color}, context=context)
        out_type_id = picking_type_obj.create(cr, uid, vals={
            'name': _('Delivery Orders'),
            'warehouse_id': warehouse.id,
            'code': 'outgoing',
            'use_create_lots': False,
            'use_existing_lots': True,
            'sequence_id': out_seq_id,
            'return_picking_type_id': in_type_id,
            'default_location_src_id': output_loc.id,
            'default_location_dest_id': False,
            'sequence': max_sequence + 4,
            'color': color}, context=context)
        picking_type_obj.write(cr, uid, [in_type_id], {'return_picking_type_id': out_type_id}, context=context)
        int_type_id = picking_type_obj.create(cr, uid, vals={
            'name': _('Internal Transfers'),
            'warehouse_id': warehouse.id,
            'code': 'internal',
            'use_create_lots': False,
            'use_existing_lots': True,
            'sequence_id': int_seq_id,
            'default_location_src_id': wh_stock_loc.id,
            'default_location_dest_id': wh_stock_loc.id,
            'active': not internal_active_false,
            'sequence': max_sequence + 2,
            'color': color}, context=context)
        pack_type_id = picking_type_obj.create(cr, uid, vals={
            'name': _('Pack'),
            'warehouse_id': warehouse.id,
            'code': 'internal',
            'use_create_lots': False,
            'use_existing_lots': True,
            'sequence_id': pack_seq_id,
            'default_location_src_id': wh_pack_stock_loc.id,
            'default_location_dest_id': output_loc.id,
            'active': warehouse.delivery_steps == 'pick_pack_ship',
            'sequence': max_sequence + 3,
            'color': color}, context=context)
        pick_type_id = picking_type_obj.create(cr, uid, vals={
            'name': _('Pick'),
            'warehouse_id': warehouse.id,
            'code': 'internal',
            'use_create_lots': False,
            'use_existing_lots': True,
            'sequence_id': pick_seq_id,
            'default_location_src_id': wh_stock_loc.id,
            'default_location_dest_id': output_loc.id if warehouse.delivery_steps == 'pick_ship' else wh_pack_stock_loc.id,
            'active': warehouse.delivery_steps != 'ship_only',
            'sequence': max_sequence + 2,
            'color': color}, context=context)

        #write picking types on WH
        vals = {
            'in_type_id': in_type_id,
            'out_type_id': out_type_id,
            'pack_type_id': pack_type_id,
            'pick_type_id': pick_type_id,
            'int_type_id': int_type_id,
        }
        super(stock_warehouse, self).write(cr, uid, warehouse.id, vals=vals, context=context)


    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        if vals is None:
            vals = {}
        data_obj = self.pool.get('ir.model.data')
        seq_obj = self.pool.get('ir.sequence')
        picking_type_obj = self.pool.get('stock.picking.type')
        location_obj = self.pool.get('stock.location')

        #create view location for warehouse
        loc_vals = {
                'name': _(vals.get('code')),
                'usage': 'view',
                'location_id': data_obj.get_object_reference(cr, uid, 'stock', 'stock_location_locations')[1],
        }
        if vals.get('company_id'):
            loc_vals['company_id'] = vals.get('company_id')
        wh_loc_id = location_obj.create(cr, uid, loc_vals, context=context)
        vals['view_location_id'] = wh_loc_id
        #create all location
        def_values = self.default_get(cr, uid, {'reception_steps', 'delivery_steps'})
        reception_steps = vals.get('reception_steps',  def_values['reception_steps'])
        delivery_steps = vals.get('delivery_steps', def_values['delivery_steps'])
        context_with_inactive = context.copy()
        context_with_inactive['active_test'] = False
        sub_locations = [
            {'name': _('Stock'), 'active': True, 'field': 'lot_stock_id'},
            {'name': _('Input'), 'active': reception_steps != 'one_step', 'field': 'wh_input_stock_loc_id'},
            {'name': _('Quality Control'), 'active': reception_steps == 'three_steps', 'field': 'wh_qc_stock_loc_id'},
            {'name': _('Output'), 'active': delivery_steps != 'ship_only', 'field': 'wh_output_stock_loc_id'},
            {'name': _('Packing Zone'), 'active': delivery_steps == 'pick_pack_ship', 'field': 'wh_pack_stock_loc_id'},
        ]
        for values in sub_locations:
            loc_vals = {
                'name': values['name'],
                'usage': 'internal',
                'location_id': wh_loc_id,
                'active': values['active'],
            }
            if vals.get('company_id'):
                loc_vals['company_id'] = vals.get('company_id')
            location_id = location_obj.create(cr, uid, loc_vals, context=context_with_inactive)
            vals[values['field']] = location_id

        #create WH
        new_id = super(stock_warehouse, self).create(cr, uid, vals=vals, context=context)
        warehouse = self.browse(cr, uid, new_id, context=context)
        self.create_sequences_and_picking_types(cr, uid, warehouse, context=context)

        #create routes and push/procurement rules
        new_objects_dict = self.create_routes(cr, uid, new_id, warehouse, context=context)
        self.write(cr, uid, warehouse.id, new_objects_dict, context=context)

        # If partner assigned
        if vals.get('partner_id'):
            comp_obj = self.pool['res.company']
            if vals.get('company_id'):
                transit_loc = comp_obj.browse(cr, uid, vals.get('company_id'), context=context).internal_transit_location_id.id
            else:
                transit_loc = comp_obj.browse(cr, uid, comp_obj._company_default_get(cr, uid, 'stock.warehouse', context=context)).internal_transit_location_id.id
            self.pool['res.partner'].write(cr, uid, [vals['partner_id']], {'property_stock_customer': transit_loc,
                                                                            'property_stock_supplier': transit_loc}, context=context)
        return new_id

    def _format_rulename(self, cr, uid, obj, from_loc, dest_loc, context=None):
        return obj.code + ': ' + from_loc.name + ' -> ' + dest_loc.name

    def _format_routename(self, cr, uid, obj, name, context=None):
        return obj.name + ': ' + name

    def get_routes_dict(self, cr, uid, ids, warehouse, context=None):
        #fetch customer and supplier locations, for references
        customer_loc, supplier_loc = self._get_partner_locations(cr, uid, ids, context=context)

        return {
            'one_step': (_('Receipt in 1 step'), []),
            'two_steps': (_('Receipt in 2 steps'), [(warehouse.wh_input_stock_loc_id, warehouse.lot_stock_id, warehouse.int_type_id.id)]),
            'three_steps': (_('Receipt in 3 steps'), [(warehouse.wh_input_stock_loc_id, warehouse.wh_qc_stock_loc_id, warehouse.int_type_id.id), (warehouse.wh_qc_stock_loc_id, warehouse.lot_stock_id, warehouse.int_type_id.id)]),
            'crossdock': (_('Cross-Dock'), [(warehouse.wh_input_stock_loc_id, warehouse.wh_output_stock_loc_id, warehouse.int_type_id.id), (warehouse.wh_output_stock_loc_id, customer_loc, warehouse.out_type_id.id)]),
            'ship_only': (_('Ship Only'), [(warehouse.lot_stock_id, customer_loc, warehouse.out_type_id.id)]),
            'pick_ship': (_('Pick + Ship'), [(warehouse.lot_stock_id, warehouse.wh_output_stock_loc_id, warehouse.pick_type_id.id), (warehouse.wh_output_stock_loc_id, customer_loc, warehouse.out_type_id.id)]),
            'pick_pack_ship': (_('Pick + Pack + Ship'), [(warehouse.lot_stock_id, warehouse.wh_pack_stock_loc_id, warehouse.pick_type_id.id), (warehouse.wh_pack_stock_loc_id, warehouse.wh_output_stock_loc_id, warehouse.pack_type_id.id), (warehouse.wh_output_stock_loc_id, customer_loc, warehouse.out_type_id.id)]),
        }

    def _handle_renaming(self, cr, uid, warehouse, name, code, context=None):
        location_obj = self.pool.get('stock.location')
        route_obj = self.pool.get('stock.location.route')
        pull_obj = self.pool.get('procurement.rule')
        push_obj = self.pool.get('stock.location.path')
        #rename location
        location_id = warehouse.lot_stock_id.location_id.id
        location_obj.write(cr, uid, location_id, {'name': code}, context=context)
        #rename route and push-procurement rules
        for route in warehouse.route_ids:
            route_obj.write(cr, uid, route.id, {'name': route.name.replace(warehouse.name, name, 1)}, context=context)
            for pull in route.pull_ids:
                pull_obj.write(cr, uid, pull.id, {'name': pull.name.replace(warehouse.name, name, 1)}, context=context)
            for push in route.push_ids:
                push_obj.write(cr, uid, push.id, {'name': pull.name.replace(warehouse.name, name, 1)}, context=context)
        #change the mto procurement rule name
        if warehouse.mto_pull_id.id:
            pull_obj.write(cr, uid, warehouse.mto_pull_id.id, {'name': warehouse.mto_pull_id.name.replace(warehouse.name, name, 1)}, context=context)

    def _check_delivery_resupply(self, cr, uid, warehouse, new_location, change_to_multiple, context=None):
        """ Will check if the resupply routes from this warehouse follow the changes of number of delivery steps """
        #Check routes that are being delivered by this warehouse and change the rule going to transit location
        route_obj = self.pool.get("stock.location.route")
        pull_obj = self.pool.get("procurement.rule")
        routes = route_obj.search(cr, uid, [('supplier_wh_id','=', warehouse.id)], context=context)
        pulls = pull_obj.search(cr, uid, ['&', ('route_id', 'in', routes), ('location_id.usage', '=', 'transit')], context=context)
        if pulls:
            pull_obj.write(cr, uid, pulls, {'location_src_id': new_location, 'procure_method': change_to_multiple and "make_to_order" or "make_to_stock"}, context=context)
        # Create or clean MTO rules
        mto_route_id = self._get_mto_route(cr, uid, context=context)
        if not change_to_multiple:
            # If single delivery we should create the necessary MTO rules for the resupply 
            # pulls = pull_obj.search(cr, uid, ['&', ('route_id', '=', mto_route_id), ('location_id.usage', '=', 'transit'), ('location_src_id', '=', warehouse.lot_stock_id.id)], context=context)
            pull_recs = pull_obj.browse(cr, uid, pulls, context=context)
            transfer_locs = list(set([x.location_id for x in pull_recs]))
            vals = [(warehouse.lot_stock_id , x, warehouse.out_type_id.id) for x in transfer_locs]
            mto_pull_vals = self._get_mto_pull_rule(cr, uid, warehouse, vals, context=context)
            for mto_pull_val in mto_pull_vals:
                pull_obj.create(cr, uid, mto_pull_val, context=context)
        else:
            # We need to delete all the MTO procurement rules, otherwise they risk to be used in the system
            pulls = pull_obj.search(cr, uid, ['&', ('route_id', '=', mto_route_id), ('location_id.usage', '=', 'transit'), ('location_src_id', '=', warehouse.lot_stock_id.id)], context=context)
            if pulls:
                pull_obj.unlink(cr, uid, pulls, context=context)

    def _check_reception_resupply(self, cr, uid, warehouse, new_location, context=None):
        """
            Will check if the resupply routes to this warehouse follow the changes of number of receipt steps
        """
        #Check routes that are being delivered by this warehouse and change the rule coming from transit location
        route_obj = self.pool.get("stock.location.route")
        pull_obj = self.pool.get("procurement.rule")
        routes = route_obj.search(cr, uid, [('supplied_wh_id','=', warehouse.id)], context=context)
        pulls= pull_obj.search(cr, uid, ['&', ('route_id', 'in', routes), ('location_src_id.usage', '=', 'transit')])
        if pulls:
            pull_obj.write(cr, uid, pulls, {'location_id': new_location}, context=context)

    def _check_resupply(self, cr, uid, warehouse, reception_new, delivery_new, context=None):
        if reception_new:
            old_val = warehouse.reception_steps
            new_val = reception_new
            change_to_one = (old_val != 'one_step' and new_val == 'one_step')
            change_to_multiple = (old_val == 'one_step' and new_val != 'one_step')
            if change_to_one or change_to_multiple:
                new_location = change_to_one and warehouse.lot_stock_id.id or warehouse.wh_input_stock_loc_id.id
                self._check_reception_resupply(cr, uid, warehouse, new_location, context=context)
        if delivery_new:
            old_val = warehouse.delivery_steps
            new_val = delivery_new
            change_to_one = (old_val != 'ship_only' and new_val == 'ship_only')
            change_to_multiple = (old_val == 'ship_only' and new_val != 'ship_only')
            if change_to_one or change_to_multiple:
                new_location = change_to_one and warehouse.lot_stock_id.id or warehouse.wh_output_stock_loc_id.id 
                self._check_delivery_resupply(cr, uid, warehouse, new_location, change_to_multiple, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        seq_obj = self.pool.get('ir.sequence')
        route_obj = self.pool.get('stock.location.route')
        context_with_inactive = context.copy()
        context_with_inactive['active_test'] = False
        for warehouse in self.browse(cr, uid, ids, context=context_with_inactive):
            #first of all, check if we need to delete and recreate route
            if vals.get('reception_steps') or vals.get('delivery_steps'):
                #activate and deactivate location according to reception and delivery option
                self.switch_location(cr, uid, warehouse.id, warehouse, vals.get('reception_steps', False), vals.get('delivery_steps', False), context=context)
                # switch between route
                self.change_route(cr, uid, ids, warehouse, vals.get('reception_steps', False), vals.get('delivery_steps', False), context=context_with_inactive)
                # Check if we need to change something to resupply warehouses and associated MTO rules
                self._check_resupply(cr, uid, warehouse, vals.get('reception_steps'), vals.get('delivery_steps'), context=context)
            if vals.get('code') or vals.get('name'):
                name = warehouse.name
                #rename sequence
                if vals.get('name'):
                    name = vals.get('name', warehouse.name)
                self._handle_renaming(cr, uid, warehouse, name, vals.get('code', warehouse.code), context=context_with_inactive)
                if warehouse.in_type_id:
                    seq_obj.write(cr, uid, warehouse.in_type_id.sequence_id.id, {'name': name + _(' Sequence in'), 'prefix': vals.get('code', warehouse.code) + '\IN\\'}, context=context)
                if warehouse.out_type_id:
                    seq_obj.write(cr, uid, warehouse.out_type_id.sequence_id.id, {'name': name + _(' Sequence out'), 'prefix': vals.get('code', warehouse.code) + '\OUT\\'}, context=context)
                if warehouse.pack_type_id:
                    seq_obj.write(cr, uid, warehouse.pack_type_id.sequence_id.id, {'name': name + _(' Sequence packing'), 'prefix': vals.get('code', warehouse.code) + '\PACK\\'}, context=context)
                if warehouse.pick_type_id:
                    seq_obj.write(cr, uid, warehouse.pick_type_id.sequence_id.id, {'name': name + _(' Sequence picking'), 'prefix': vals.get('code', warehouse.code) + '\PICK\\'}, context=context)
                if warehouse.int_type_id:
                    seq_obj.write(cr, uid, warehouse.int_type_id.sequence_id.id, {'name': name + _(' Sequence internal'), 'prefix': vals.get('code', warehouse.code) + '\INT\\'}, context=context)
        if vals.get('resupply_wh_ids') and not vals.get('resupply_route_ids'):
            for cmd in vals.get('resupply_wh_ids'):
                if cmd[0] == 6:
                    new_ids = set(cmd[2])
                    old_ids = set([wh.id for wh in warehouse.resupply_wh_ids])
                    to_add_wh_ids = new_ids - old_ids
                    if to_add_wh_ids:
                        supplier_warehouses = self.browse(cr, uid, list(to_add_wh_ids), context=context)
                        self._create_resupply_routes(cr, uid, warehouse, supplier_warehouses, warehouse.default_resupply_wh_id, context=context)
                    to_remove_wh_ids = old_ids - new_ids
                    if to_remove_wh_ids:
                        to_remove_route_ids = route_obj.search(cr, uid, [('supplied_wh_id', '=', warehouse.id), ('supplier_wh_id', 'in', list(to_remove_wh_ids))], context=context)
                        if to_remove_route_ids:
                            route_obj.unlink(cr, uid, to_remove_route_ids, context=context)
                else:
                    #not implemented
                    pass
        if 'default_resupply_wh_id' in vals:
            if vals.get('default_resupply_wh_id') == warehouse.id:
                raise UserError(_('The default resupply warehouse should be different than the warehouse itself!'))
            if warehouse.default_resupply_wh_id:
                #remove the existing resupplying route on the warehouse
                to_remove_route_ids = route_obj.search(cr, uid, [('supplied_wh_id', '=', warehouse.id), ('supplier_wh_id', '=', warehouse.default_resupply_wh_id.id)], context=context)
                for inter_wh_route_id in to_remove_route_ids:
                    self.write(cr, uid, [warehouse.id], {'route_ids': [(3, inter_wh_route_id)]})
            if vals.get('default_resupply_wh_id'):
                #assign the new resupplying route on all products
                to_assign_route_ids = route_obj.search(cr, uid, [('supplied_wh_id', '=', warehouse.id), ('supplier_wh_id', '=', vals.get('default_resupply_wh_id'))], context=context)
                for inter_wh_route_id in to_assign_route_ids:
                    self.write(cr, uid, [warehouse.id], {'route_ids': [(4, inter_wh_route_id)]})

        # If another partner assigned
        if vals.get('partner_id'):
            if not vals.get('company_id'):
                company = self.browse(cr, uid, ids[0], context=context).company_id
            else:
                company = self.pool['res.company'].browse(cr, uid, vals['company_id'])
            transit_loc = company.internal_transit_location_id.id
            self.pool['res.partner'].write(cr, uid, [vals['partner_id']], {'property_stock_customer': transit_loc,
                                                                            'property_stock_supplier': transit_loc}, context=context)
        return super(stock_warehouse, self).write(cr, uid, ids, vals=vals, context=context)

    def get_all_routes_for_wh(self, cr, uid, warehouse, context=None):
        route_obj = self.pool.get("stock.location.route")
        all_routes = [route.id for route in warehouse.route_ids]
        all_routes += route_obj.search(cr, uid, [('supplied_wh_id', '=', warehouse.id)], context=context)
        all_routes += [warehouse.mto_pull_id.route_id.id]
        return all_routes

    def view_all_routes_for_wh(self, cr, uid, ids, context=None):
        all_routes = []
        for wh in self.browse(cr, uid, ids, context=context):
            all_routes += self.get_all_routes_for_wh(cr, uid, wh, context=context)

        domain = [('id', 'in', all_routes)]
        return {
            'name': _('Warehouse\'s Routes'),
            'domain': domain,
            'res_model': 'stock.location.route',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'tree,form',
            'view_type': 'form',
            'limit': 20
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
            [('auto','Automatic Move'), ('manual','Manual Operation'),('transparent','Automatic No Step Added')],
            'Automatic Move',
            required=True, select=1,
            help="The 'Automatic Move' / 'Manual Operation' value will create a stock move after the current one.  " \
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
        'auto': 'auto',
        'delay': 0,
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'procurement.order', context=c),
        'propagate': True,
        'active': True,
    }

    def _prepare_push_apply(self, cr, uid, rule, move, context=None):
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

    def _apply(self, cr, uid, rule, move, context=None):
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
                move_obj._push_apply(cr, uid, [move], context=context)
        else:
            vals = self._prepare_push_apply(cr, uid, rule, move, context=context)
            move_id = move_obj.copy(cr, uid, move.id, vals, context=context)
            move_obj.write(cr, uid, [move.id], {
                'move_dest_id': move_id,
            })
            move_obj.action_confirm(cr, uid, [move_id], context=None)


# -------------------------
# Packaging related stuff
# -------------------------

from openerp.report import report_sxw

class stock_package(osv.osv):
    """
    These are the packages, containing quants and/or other packages
    """
    _name = "stock.quant.package"
    _description = "Physical Packages"
    _parent_name = "parent_id"
    _parent_store = True
    _parent_order = 'name'
    _order = 'parent_left'

    def name_get(self, cr, uid, ids, context=None):
        res = self._complete_name(cr, uid, ids, 'complete_name', None, context=context)
        return res.items()

    def _complete_name(self, cr, uid, ids, name, args, context=None):
        """ Forms complete name of location from parent location to child location.
        @return: Dictionary of values
        """
        res = {}
        for m in self.browse(cr, uid, ids, context=context):
            res[m.id] = m.name
            parent = m.parent_id
            while parent:
                res[m.id] = parent.name + ' / ' + res[m.id]
                parent = parent.parent_id
        return res

    def _get_packages(self, cr, uid, ids, context=None):
        """Returns packages from quants for store"""
        res = set()
        for quant in self.browse(cr, uid, ids, context=context):
            pack = quant.package_id
            while pack:
                res.add(pack.id)
                pack = pack.parent_id
        return list(res)

    def _get_package_info(self, cr, uid, ids, name, args, context=None):
        quant_obj = self.pool.get("stock.quant")
        default_company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        res = dict((res_id, {'location_id': False, 'company_id': default_company_id, 'owner_id': False}) for res_id in ids)
        for pack in self.browse(cr, uid, ids, context=context):
            quants = quant_obj.search(cr, uid, [('package_id', 'child_of', pack.id)], context=context)
            if quants:
                quant = quant_obj.browse(cr, uid, quants[0], context=context)
                res[pack.id]['location_id'] = quant.location_id.id
                res[pack.id]['owner_id'] = quant.owner_id.id
                res[pack.id]['company_id'] = quant.company_id.id
            else:
                res[pack.id]['location_id'] = False
                res[pack.id]['owner_id'] = False
                res[pack.id]['company_id'] = False
        return res

    def _get_packages_to_relocate(self, cr, uid, ids, context=None):
        res = set()
        for pack in self.browse(cr, uid, ids, context=context):
            res.add(pack.id)
            if pack.parent_id:
                res.add(pack.parent_id.id)
        return list(res)

    _columns = {
        'name': fields.char('Package Reference', select=True, copy=False),
        'complete_name': fields.function(_complete_name, type='char', string="Package Name",),
        'parent_left': fields.integer('Left Parent', select=1),
        'parent_right': fields.integer('Right Parent', select=1),
        'packaging_id': fields.many2one('product.packaging', 'Packaging', help="This field should be completed only if everything inside the package share the same product, otherwise it doesn't really makes sense.", select=True),
        'location_id': fields.function(_get_package_info, type='many2one', relation='stock.location', string='Location', multi="package",
                                    store={
                                       'stock.quant': (_get_packages, ['location_id'], 10),
                                       'stock.quant.package': (_get_packages_to_relocate, ['quant_ids', 'children_ids', 'parent_id'], 10),
                                    }, readonly=True, select=True),
        'quant_ids': fields.one2many('stock.quant', 'package_id', 'Bulk Content', readonly=True),
        'parent_id': fields.many2one('stock.quant.package', 'Parent Package', help="The package containing this item", ondelete='restrict', readonly=True),
        'children_ids': fields.one2many('stock.quant.package', 'parent_id', 'Contained Packages', readonly=True),
        'company_id': fields.function(_get_package_info, type="many2one", relation='res.company', string='Company', multi="package", 
                                    store={
                                       'stock.quant': (_get_packages, ['company_id'], 10),
                                       'stock.quant.package': (_get_packages_to_relocate, ['quant_ids', 'children_ids', 'parent_id'], 10),
                                    }, readonly=True, select=True),
        'owner_id': fields.function(_get_package_info, type='many2one', relation='res.partner', string='Owner', multi="package",
                                store={
                                       'stock.quant': (_get_packages, ['owner_id'], 10),
                                       'stock.quant.package': (_get_packages_to_relocate, ['quant_ids', 'children_ids', 'parent_id'], 10),
                                    }, readonly=True, select=True),
    }
    _defaults = {
        'name': lambda self, cr, uid, context: self.pool.get('ir.sequence').next_by_code(cr, uid, 'stock.quant.package') or _('Unknown Pack')
    }

    def _check_location_constraint(self, cr, uid, packs, context=None):
        '''checks that all quants in a package are stored in the same location. This function cannot be used
           as a constraint because it needs to be checked on pack operations (they may not call write on the
           package)
        '''
        quant_obj = self.pool.get('stock.quant')
        for pack in packs:
            parent = pack
            while parent.parent_id:
                parent = parent.parent_id
            quant_ids = self.get_content(cr, uid, [parent.id], context=context)
            quants = [x for x in quant_obj.browse(cr, uid, quant_ids, context=context) if x.qty > 0]
            location_id = quants and quants[0].location_id.id or False
            if not [quant.location_id.id == location_id for quant in quants]:
                raise UserError(_('Everything inside a package should be in the same location'))
        return True

    def action_print(self, cr, uid, ids, context=None):
        context = dict(context or {}, active_ids=ids)
        return self.pool.get("report").get_action(cr, uid, ids, 'stock.report_package_barcode_small', context=context)
    
    
    def unpack(self, cr, uid, ids, context=None):
        quant_obj = self.pool.get('stock.quant')
        for package in self.browse(cr, uid, ids, context=context):
            quant_ids = [quant.id for quant in package.quant_ids]
            quant_obj.write(cr, uid, quant_ids, {'package_id': package.parent_id.id or False}, context=context)
            children_package_ids = [child_package.id for child_package in package.children_ids]
            self.write(cr, uid, children_package_ids, {'parent_id': package.parent_id.id or False}, context=context)
        #delete current package since it contains nothing anymore
        self.unlink(cr, uid, ids, context=context)
        return self.pool.get('ir.actions.act_window').for_xml_id(cr, uid, 'stock', 'action_package_view', context=context)

    def get_content(self, cr, uid, ids, context=None):
        child_package_ids = self.search(cr, uid, [('id', 'child_of', ids)], context=context)
        return self.pool.get('stock.quant').search(cr, uid, [('package_id', 'in', child_package_ids)], context=context)

    def get_content_package(self, cr, uid, ids, context=None):
        quants_ids = self.get_content(cr, uid, ids, context=context)
        res = self.pool.get('ir.actions.act_window').for_xml_id(cr, uid, 'stock', 'quantsact', context=context)
        res['domain'] = [('id', 'in', quants_ids)]
        return res

    def _get_product_total_qty(self, cr, uid, package_record, product_id, context=None):
        ''' find the total of given product 'product_id' inside the given package 'package_id'''
        quant_obj = self.pool.get('stock.quant')
        all_quant_ids = self.get_content(cr, uid, [package_record.id], context=context)
        total = 0
        for quant in quant_obj.browse(cr, uid, all_quant_ids, context=context):
            if quant.product_id.id == product_id:
                total += quant.qty
        return total

    def _get_all_products_quantities(self, cr, uid, package_id, context=None):
        '''This function computes the different product quantities for the given package
        '''
        quant_obj = self.pool.get('stock.quant')
        res = {}
        for quant in quant_obj.browse(cr, uid, self.get_content(cr, uid, package_id, context=context)):
            if quant.product_id.id not in res:
                res[quant.product_id.id] = 0
            res[quant.product_id.id] += quant.qty
        return res

    #Remove me?
    def copy_pack(self, cr, uid, id, default_pack_values=None, default=None, context=None):
        stock_pack_operation_obj = self.pool.get('stock.pack.operation')
        if default is None:
            default = {}
        new_package_id = self.copy(cr, uid, id, default_pack_values, context=context)
        default['result_package_id'] = new_package_id
        op_ids = stock_pack_operation_obj.search(cr, uid, [('result_package_id', '=', id)], context=context)
        for op_id in op_ids:
            stock_pack_operation_obj.copy(cr, uid, op_id, default, context=context)


class stock_pack_operation(osv.osv):
    _name = "stock.pack.operation"
    _description = "Packing Operation"

    _order = "result_package_id desc, id"

    def _get_remaining_prod_quantities(self, cr, uid, operation, context=None):
        '''Get the remaining quantities per product on an operation with a package. This function returns a dictionary'''
        #if the operation doesn't concern a package, it's not relevant to call this function
        if not operation.package_id or operation.product_id:
            return {operation.product_id: operation.remaining_qty}
        #get the total of products the package contains
        res = self.pool.get('stock.quant.package')._get_all_products_quantities(cr, uid, operation.package_id.id, context=context)
        #reduce by the quantities linked to a move
        for record in operation.linked_move_operation_ids:
            if record.move_id.product_id.id not in res:
                res[record.move_id.product_id] = 0
            res[record.move_id.product_id] -= record.qty
        return res

    def _get_remaining_qty(self, cr, uid, ids, name, args, context=None):
        uom_obj = self.pool.get('product.uom')
        res = {}
        for ops in self.browse(cr, uid, ids, context=context):
            res[ops.id] = 0
            if ops.package_id and not ops.product_id:
                #dont try to compute the remaining quantity for packages because it's not relevant (a package could include different products).
                #should use _get_remaining_prod_quantities instead
                continue
            else:
                qty = ops.product_qty
                if ops.product_uom_id:
                    qty = uom_obj._compute_qty_obj(cr, uid, ops.product_uom_id, ops.product_qty, ops.product_id.uom_id, context=context)
                for record in ops.linked_move_operation_ids:
                    qty -= record.qty
                res[ops.id] = float_round(qty, precision_rounding=ops.product_id.uom_id.rounding)
        return res

    def product_id_change(self, cr, uid, ids, product_id, product_uom_id, product_qty, context=None):
        res = self.on_change_tests(cr, uid, ids, product_id, product_uom_id, product_qty, context=context)
        uom_obj = self.pool['product.uom']
        product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
        if product_id and not product_uom_id or uom_obj.browse(cr, uid, product_uom_id, context=context).category_id.id != product.uom_id.category_id.id:
            res['value']['product_uom_id'] = product.uom_id.id
        if product:
            res['value']['lots_visible'] = (product.tracking != 'none')
            res['domain'] = {'product_uom_id': [('category_id','=',product.uom_id.category_id.id)]}
        else:
            res['domain'] = {'product_uom_id': []}
        return res

    def on_change_tests(self, cr, uid, ids, product_id, product_uom_id, product_qty, context=None):
        res = {'value': {}}
        uom_obj = self.pool.get('product.uom')
        if product_id:
            product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
            product_uom_id = product_uom_id or product.uom_id.id
            selected_uom = uom_obj.browse(cr, uid, product_uom_id, context=context)
            if selected_uom.category_id.id != product.uom_id.category_id.id:
                res['warning'] = {
                    'title': _('Warning: wrong UoM!'),
                    'message': _('The selected UoM for product %s is not compatible with the UoM set on the product form. \nPlease choose an UoM within the same UoM category.') % (product.name)
                }
            if product_qty and 'warning' not in res:
                rounded_qty = uom_obj._compute_qty(cr, uid, product_uom_id, product_qty, product_uom_id, round=True)
                if rounded_qty != product_qty:
                    res['warning'] = {
                        'title': _('Warning: wrong quantity!'),
                        'message': _('The chosen quantity for product %s is not compatible with the UoM rounding. It will be automatically converted at confirmation') % (product.name)
                    }
        return res

    def _compute_location_description(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for op in self.browse(cr, uid, ids, context=context):
            from_name = op.location_id.name
            to_name = op.location_dest_id.name
            if op.package_id and op.product_id:
                from_name += " : " + op.package_id.name
            if op.result_package_id:
                to_name += " : " + op.result_package_id.name
            res[op.id] = {'from_loc': from_name,
                          'to_loc': to_name}
        return res

    def _get_bool(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for pack in self.browse(cr, uid, ids, context=context):
            res[pack.id] = (pack.qty_done > 0.0)
        return res

    def _set_processed_qty(self, cr, uid, id, field_name, field_value, arg, context=None):
        op = self.browse(cr, uid, id, context=context)
        if not op.product_id:
            if field_value and op.qty_done == 0:
                self.write(cr, uid, [id], {'qty_done': 1.0}, context=context)
            if not field_value and op.qty_done != 0:
                self.write(cr, uid, [id], {'qty_done': 0.0}, context=context)
        return True

    def _compute_lots_visible(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for pack in self.browse(cr, uid, ids, context=context):
            if pack.pack_lot_ids:
                res[pack.id] = True
                continue
            pick = pack.picking_id
            product_requires = (pack.product_id.tracking != 'none')
            if pick.picking_type_id:
                res[pack.id] = (pick.picking_type_id.use_existing_lots or pick.picking_type_id.use_create_lots) and product_requires
            else:
                res[pack.id] = product_requires
        return res

    def _get_default_from_loc(self, cr, uid, context=None):
        default_loc = context.get('default_location_id')
        if default_loc:
            return self.pool['stock.location'].browse(cr, uid, default_loc, context=context).name

    def _get_default_to_loc(self, cr, uid, context=None):
        default_loc = context.get('default_location_dest_id')
        if default_loc:
            return self.pool['stock.location'].browse(cr, uid, default_loc, context=context).name

    _columns = {
        'picking_id': fields.many2one('stock.picking', 'Stock Picking', help='The stock operation where the packing has been made', required=True),
        'product_id': fields.many2one('product.product', 'Product', ondelete="CASCADE"),  # 1
        'product_uom_id': fields.many2one('product.uom', 'Unit of Measure'),
        'product_qty': fields.float('To Do', digits_compute=dp.get_precision('Product Unit of Measure'), required=True),
        'qty_done': fields.float('Done', digits_compute=dp.get_precision('Product Unit of Measure')),
        'processed_boolean': fields.function(_get_bool, fnct_inv=_set_processed_qty, type='boolean', string='Done'),
        'package_id': fields.many2one('stock.quant.package', 'Source Package'),  # 2
        'pack_lot_ids': fields.one2many('stock.pack.operation.lot', 'operation_id', 'Lots Used'),
        'result_package_id': fields.many2one('stock.quant.package', 'Destination Package', help="If set, the operations are packed into this package", required=False, ondelete='cascade'),
        'date': fields.datetime('Date', required=True),
        'owner_id': fields.many2one('res.partner', 'Owner', help="Owner of the quants"),
        'linked_move_operation_ids': fields.one2many('stock.move.operation.link', 'operation_id', string='Linked Moves', readonly=True, help='Moves impacted by this operation for the computation of the remaining quantities'),
        'remaining_qty': fields.function(_get_remaining_qty, type='float', digits = 0, string="Remaining Qty", help="Remaining quantity in default UoM according to moves matched with this operation. "),
        'location_id': fields.many2one('stock.location', 'Source Location', required=True),
        'location_dest_id': fields.many2one('stock.location', 'Destination Location', required=True),
        'picking_source_location_id': fields.related('picking_id', 'location_id', type='many2one', relation='stock.location'),
        'picking_destination_location_id': fields.related('picking_id', 'location_dest_id', type='many2one', relation='stock.location'),
        'from_loc': fields.function(_compute_location_description, type='char', string='From', multi='loc'),
        'to_loc': fields.function(_compute_location_description, type='char', string='To', multi='loc'),
        'fresh_record': fields.boolean('Newly created pack operation'),
        'lots_visible': fields.function(_compute_lots_visible, type='boolean'),
        'state': fields.related('picking_id', 'state', type='selection', selection=[
                ('draft', 'Draft'),
                ('cancel', 'Cancelled'),
                ('waiting', 'Waiting Another Operation'),
                ('confirmed', 'Waiting Availability'),
                ('partially_available', 'Partially Available'),
                ('assigned', 'Available'),
                ('done', 'Done'),
                ]),
    }

    _defaults = {
        'date': fields.date.context_today,
        'qty_done': 0.0,
        'product_qty': 0.0,
        'processed_boolean': lambda *a: False,
        'fresh_record': True,
        'from_loc': _get_default_from_loc,
        'to_loc': _get_default_to_loc,
    }

    def split_quantities(self, cr, uid, ids, context=None):
        for pack in self.browse(cr, uid, ids, context=context):
            if pack.product_qty - pack.qty_done > 0.0 and pack.qty_done < pack.product_qty:
                pack2 = self.copy(cr, uid, pack.id, default={'qty_done': 0.0, 'product_qty': pack.product_qty - pack.qty_done}, context=context)
                self.write(cr, uid, [pack.id], {'product_qty': pack.qty_done}, context=context)
            else:
                raise UserError(_('The quantity to split should be smaller than the quantity To Do.  '))
        return True

    def write(self, cr, uid, ids, vals, context=None):
        vals['fresh_record'] = False
        context = context or {}
        res = super(stock_pack_operation, self).write(cr, uid, ids, vals, context=context)
        return res

    def unlink(self, cr, uid, ids, context=None):
        if any([x.state in ('done', 'cancel') for x in self.browse(cr, uid, ids, context=context)]):
            raise UserError(_('You can not delete pack operations of a done picking'))
        return super(stock_pack_operation, self).unlink(cr, uid, ids, context=context)

    def check_tracking(self, cr, uid, ids, context=None):
        """ Checks if serial number is assigned to stock move or not and raise an error if it had to.
        """
        operations = self.browse(cr, uid, ids, context=context)
        for ops in operations:
            if ops.picking_id and (ops.picking_id.picking_type_id.use_existing_lots or ops.picking_id.picking_type_id.use_create_lots) and \
                ops.product_id and ops.product_id.tracking != 'none' and ops.qty_done > 0.0:
                if not ops.pack_lot_ids:
                    raise UserError(_('You need to provide a Lot/Serial Number for product %s') % ops.product_id.name)
                if ops.product_id.tracking == 'serial':
                    for opslot in ops.pack_lot_ids:
                        if opslot.qty not in (1.0, 0.0):
                            raise UserError(_('You should provide a different serial number for each piece'))

    def save(self, cr, uid, ids, context=None):
        for pack in self.browse(cr, uid, ids, context=context):
            if pack.product_id.tracking != 'none':
                qty_done = sum([x.qty for x in pack.pack_lot_ids])
                self.pool['stock.pack.operation'].write(cr, uid, [pack.id], {'qty_done': qty_done}, context=context)
        return {'type': 'ir.actions.act_window_close'}

    def split_lot(self, cr, uid, ids, context=None):
        context = context or {}
        ctx=context.copy()
        assert len(ids) > 0
        data_obj = self.pool['ir.model.data']
        pack = self.browse(cr, uid, ids[0], context=context)
        picking_type = pack.picking_id.picking_type_id
        serial = (pack.product_id.tracking == 'serial')
        view = data_obj.xmlid_to_res_id(cr, uid, 'stock.view_pack_operation_lot_form')
        only_create = picking_type.use_create_lots and not picking_type.use_existing_lots
        show_reserved = any([x for x in pack.pack_lot_ids if x.qty_todo > 0.0])
        ctx.update({'serial': serial,
                    'only_create': only_create,
                    'create_lots': picking_type.use_create_lots,
                    'state_done': pack.picking_id.state == 'done',
                    'show_reserved': show_reserved})
        return {
             'name': _('Lot Details'),
             'type': 'ir.actions.act_window',
             'view_type': 'form',
             'view_mode': 'form',
             'res_model': 'stock.pack.operation',
             'views': [(view, 'form')],
             'view_id': view,
             'target': 'new',
             'res_id': pack.id,
             'context': ctx,
        }

    def show_details(self, cr, uid, ids, context=None):
        data_obj = self.pool['ir.model.data']
        view = data_obj.xmlid_to_res_id(cr, uid, 'stock.view_pack_operation_details_form_save')
        pack = self.browse(cr, uid, ids[0], context=context)
        return {
             'name': _('Operation Details'),
             'type': 'ir.actions.act_window',
             'view_type': 'form',
             'view_mode': 'form',
             'res_model': 'stock.pack.operation',
             'views': [(view, 'form')],
             'view_id': view,
             'target': 'new',
             'res_id': pack.id,
             'context': context,
        }


class stock_pack_operation_lot(osv.osv):
    _name = "stock.pack.operation.lot"
    _description = "Specifies lot/serial number for pack operations that need it"

    def _get_plus(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for packlot in self.browse(cr, uid, ids, context=context):
            if packlot.operation_id.product_id.tracking == 'serial':
                res[packlot.id] = (packlot.qty == 0.0)
            else:
                res[packlot.id] = (packlot.qty_todo == 0.0) or (packlot.qty < packlot.qty_todo)
        return res

    _columns = {
        'operation_id': fields.many2one('stock.pack.operation'),
        'qty': fields.float('Done'),
        'lot_id': fields.many2one('stock.production.lot', 'Lot/Serial Number'),
        'lot_name': fields.char('Lot Name'),
        'qty_todo': fields.float('To Do'),
        'plus_visible': fields.function(_get_plus, type='boolean'),
    }

    _defaults = {
        'qty': lambda cr, uid, ids, c: 1.0,
        'qty_todo': lambda cr, uid, ids, c: 0.0,
        'plus_visible': True,
    }

    def _check_lot(self, cr, uid, ids, context=None):
        for packlot in self.browse(cr, uid, ids, context=context):
            if not packlot.lot_name and not packlot.lot_id:
                return False
        return True

    _constraints = [
        (_check_lot,
            'Lot is required',
            ['lot_id', 'lot_name']),
    ]

    _sql_constraints = [
        ('qty', 'CHECK(qty >= 0.0)','Quantity must be greater than or equal to 0.0!'),
        ('uniq_lot_id', 'unique(operation_id, lot_id)', 'You have already mentioned this lot in another line'),
        ('uniq_lot_name', 'unique(operation_id, lot_name)', 'You have already mentioned this lot name in another line')]

    def do_plus(self, cr, uid, ids, context=None):
        pack_obj = self.pool['stock.pack.operation']
        for packlot in self.browse(cr, uid, ids, context=context):
            self.write(cr, uid, [packlot.id], {'qty': packlot.qty + 1}, context=context)
        pack = self.browse(cr, uid, ids[0], context=context).operation_id
        qty_done = sum([x.qty for x in pack.pack_lot_ids])
        pack_obj.write(cr, uid, [pack.id], {'qty_done': qty_done}, context=context)
        return pack_obj.split_lot(cr, uid, [pack.id], context=context)

    def do_minus(self, cr, uid, ids, context=None):
        pack_obj = self.pool['stock.pack.operation']
        for packlot in self.browse(cr, uid, ids, context=context):
            self.write(cr, uid, [packlot.id], {'qty': packlot.qty - 1}, context=context)
        pack = self.browse(cr, uid, ids[0], context=context).operation_id
        qty_done = sum([x.qty for x in pack.pack_lot_ids])
        pack_obj.write(cr, uid, [pack.id], {'qty_done': qty_done}, context=context)
        return pack_obj.split_lot(cr, uid, [pack.id], context=context)


class stock_move_operation_link(osv.osv):
    """
    Table making the link between stock.moves and stock.pack.operations to compute the remaining quantities on each of these objects
    """
    _name = "stock.move.operation.link"
    _description = "Link between stock moves and pack operations"

    _columns = {
        'qty': fields.float('Quantity', help="Quantity of products to consider when talking about the contribution of this pack operation towards the remaining quantity of the move (and inverse). Given in the product main uom."),
        'operation_id': fields.many2one('stock.pack.operation', 'Operation', required=True, ondelete="cascade"),
        'move_id': fields.many2one('stock.move', 'Move', required=True, ondelete="cascade"),
        'reserved_quant_id': fields.many2one('stock.quant', 'Reserved Quant', help="Technical field containing the quant that created this link between an operation and a stock move. Used at the stock_move_obj.action_done() time to avoid seeking a matching quant again"),
    }


class stock_warehouse_orderpoint(osv.osv):
    """
    Defines Minimum stock rules.
    """
    _name = "stock.warehouse.orderpoint"
    _description = "Minimum Inventory Rule"

    def subtract_procurements_from_orderpoints(self, cr, uid, orderpoint_ids, context=None):
        '''This function returns quantity of product that needs to be deducted from the orderpoint computed quantity because there's already a procurement created with aim to fulfill it.
        '''

        cr.execute("""select op.id, p.id, p.product_uom, p.product_qty, pt.uom_id, sm.product_qty from procurement_order as p left join stock_move as sm ON sm.procurement_id = p.id,
                                    stock_warehouse_orderpoint op, product_product pp, product_template pt
                                WHERE p.orderpoint_id = op.id AND p.state not in ('done', 'cancel') AND (sm.state IS NULL OR sm.state not in ('draft'))
                                AND pp.id = p.product_id AND pp.product_tmpl_id = pt.id
                                AND op.id IN %s
                                ORDER BY op.id, p.id
                    """, (tuple(orderpoint_ids),))
        results = cr.fetchall()
        current_proc = False
        current_op = False
        uom_obj = self.pool.get("product.uom")
        op_qty = 0
        res = dict.fromkeys(orderpoint_ids, 0.0)
        for move_result in results:
            op = move_result[0]
            if current_op != op:
                if current_op:
                    res[current_op] = op_qty
                current_op = op
                op_qty = 0
            proc = move_result[1]
            if proc != current_proc:
                op_qty += uom_obj._compute_qty(cr, uid, move_result[2], move_result[3], move_result[4], round=False)
                current_proc = proc
            if move_result[5]: #If a move is associated (is move qty)
                op_qty -= move_result[5]
        if current_op:
            res[current_op] = op_qty
        return res

    def _check_product_uom(self, cr, uid, ids, context=None):
        '''
        Check if the UoM has the same category as the product standard UoM
        '''
        if not context:
            context = {}

        for rule in self.browse(cr, uid, ids, context=context):
            if rule.product_id.uom_id.category_id.id != rule.product_uom.category_id.id:
                return False
        return True

    _columns = {
        'name': fields.char('Name', required=True, copy=False),
        'active': fields.boolean('Active', help="If the active field is set to False, it will allow you to hide the orderpoint without removing it."),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse', required=True, ondelete="cascade"),
        'location_id': fields.many2one('stock.location', 'Location', required=True, ondelete="cascade"),
        'product_id': fields.many2one('product.product', 'Product', required=True, ondelete='cascade', domain=[('type', '=', 'product')]),
        'product_uom': fields.related('product_id', 'uom_id', type='many2one', relation='product.uom', string='Product Unit of Measure', readonly=True, required=True),
        'product_min_qty': fields.float('Minimum Quantity', required=True,
            digits_compute=dp.get_precision('Product Unit of Measure'),
            help="When the virtual stock goes below the Min Quantity specified for this field, Odoo generates "\
            "a procurement to bring the forecasted quantity to the Max Quantity."),
        'product_max_qty': fields.float('Maximum Quantity', required=True,
            digits_compute=dp.get_precision('Product Unit of Measure'),
            help="When the virtual stock goes below the Min Quantity, Odoo generates "\
            "a procurement to bring the forecasted quantity to the Quantity specified as Max Quantity."),
        'qty_multiple': fields.float('Qty Multiple', required=True,
            digits_compute=dp.get_precision('Product Unit of Measure'),
            help="The procurement quantity will be rounded up to this multiple.  If it is 0, the exact quantity will be used.  "),
        'procurement_ids': fields.one2many('procurement.order', 'orderpoint_id', 'Created Procurements'),
        'group_id': fields.many2one('procurement.group', 'Procurement Group', help="Moves created through this orderpoint will be put in this procurement group. If none is given, the moves generated by procurement rules will be grouped into one big picking.", copy=False),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'lead_days': fields.integer('Lead Time', help="Number of days after the orderpoint is triggered to receive the products or to order to the vendor"),
        'lead_type': fields.selection([
            ('net', 'Day(s) to get the products'),
            ('supplier', 'Day(s) to purchase')
         ], 'Lead Type', required=True)
    }
    _defaults = {
        'active': lambda *a: 1,
        'lead_days': lambda *a: 1,
        'lead_type': lambda *a: 'supplier',
        'qty_multiple': lambda *a: 1,
        'name': lambda self, cr, uid, context: self.pool.get('ir.sequence').next_by_code(cr, uid, 'stock.orderpoint') or '',
        'product_uom': lambda self, cr, uid, context: context.get('product_uom', False),
        'company_id': lambda self, cr, uid, context: self.pool.get('res.company')._company_default_get(cr, uid, 'stock.warehouse.orderpoint', context=context)
    }
    _sql_constraints = [
        ('qty_multiple_check', 'CHECK( qty_multiple >= 0 )', 'Qty Multiple must be greater than or equal to zero.'),
    ]
    _constraints = [
        (_check_product_uom, 'You have to select a product unit of measure in the same category than the default unit of measure of the product', ['product_id', 'product_uom']),
    ]

    def default_get(self, cr, uid, fields, context=None):
        warehouse_obj = self.pool.get('stock.warehouse')
        res = super(stock_warehouse_orderpoint, self).default_get(cr, uid, fields, context)
        # default 'warehouse_id' and 'location_id'
        if 'warehouse_id' not in res:
            warehouse_ids = res.get('company_id') and warehouse_obj.search(cr, uid, [('company_id', '=', res['company_id'])], limit=1, context=context) or []
            res['warehouse_id'] = warehouse_ids and warehouse_ids[0] or False
        if 'location_id' not in res:
            res['location_id'] = res.get('warehouse_id') and warehouse_obj.browse(cr, uid, res['warehouse_id'], context).lot_stock_id.id or False
        return res

    def onchange_warehouse_id(self, cr, uid, ids, warehouse_id, context=None):
        """ Finds location id for changed warehouse.
        @param warehouse_id: Changed id of warehouse.
        @return: Dictionary of values.
        """
        if warehouse_id:
            w = self.pool.get('stock.warehouse').browse(cr, uid, warehouse_id, context=context)
            v = {'location_id': w.lot_stock_id.id}
            return {'value': v}
        return {}

    def onchange_product_id(self, cr, uid, ids, product_id, context=None):
        """ Finds UoM for changed product.
        @param product_id: Changed id of product.
        @return: Dictionary of values.
        """
        if product_id:
            prod = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
            d = {'product_uom': [('category_id', '=', prod.uom_id.category_id.id)]}
            v = {'product_uom': prod.uom_id.id}
            return {'value': v, 'domain': d}
        return {'domain': {'product_uom': []}}

class stock_picking_type(osv.osv):
    _name = "stock.picking.type"
    _description = "The picking type determines the picking view"
    _order = 'sequence'

    def open_barcode_interface(self, cr, uid, ids, context=None):
        final_url = "/stock/barcode/#action=stock.ui&picking_type_id=" + str(ids[0]) if len(ids) else '0'
        return {'type': 'ir.actions.act_url', 'url': final_url, 'target': 'self'}

    def _get_tristate_values(self, cr, uid, ids, field_name, arg, context=None):
        picking_obj = self.pool.get('stock.picking')
        res = {}
        for picking_type_id in ids:
            #get last 10 pickings of this type
            picking_ids = picking_obj.search(cr, uid, [('picking_type_id', '=', picking_type_id), ('state', '=', 'done')], order='date_done desc', limit=10, context=context)
            tristates = []
            for picking in picking_obj.browse(cr, uid, picking_ids, context=context):
                if picking.date_done > picking.date:
                    tristates.insert(0, {'tooltip': picking.name or '' + ": " + _('Late'), 'value': -1})
                elif picking.backorder_id:
                    tristates.insert(0, {'tooltip': picking.name or '' + ": " + _('Backorder exists'), 'value': 0})
                else:
                    tristates.insert(0, {'tooltip': picking.name or '' + ": " + _('OK'), 'value': 1})
            res[picking_type_id] = json.dumps(tristates)
        return res

    def _get_picking_count(self, cr, uid, ids, field_names, arg, context=None):
        obj = self.pool.get('stock.picking')
        domains = {
            'count_picking_draft': [('state', '=', 'draft')],
            'count_picking_waiting': [('state', 'in', ('confirmed', 'waiting'))],
            'count_picking_ready': [('state', 'in', ('assigned', 'partially_available'))],
            'count_picking': [('state', 'in', ('assigned', 'waiting', 'confirmed', 'partially_available'))],
            'count_picking_late': [('min_date', '<', time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)), ('state', 'in', ('assigned', 'waiting', 'confirmed', 'partially_available'))],
            'count_picking_backorders': [('backorder_id', '!=', False), ('state', 'in', ('confirmed', 'assigned', 'waiting', 'partially_available'))],
        }
        result = {}
        for field in domains:
            data = obj.read_group(cr, uid, domains[field] +
                [('state', 'not in', ('done', 'cancel')), ('picking_type_id', 'in', ids)],
                ['picking_type_id'], ['picking_type_id'], context=context)
            count = dict(map(lambda x: (x['picking_type_id'] and x['picking_type_id'][0], x['picking_type_id_count']), data))
            for tid in ids:
                result.setdefault(tid, {})[field] = count.get(tid, 0)
        for tid in ids:
            if result[tid]['count_picking']:
                result[tid]['rate_picking_late'] = result[tid]['count_picking_late'] * 100 / result[tid]['count_picking']
                result[tid]['rate_picking_backorders'] = result[tid]['count_picking_backorders'] * 100 / result[tid]['count_picking']
            else:
                result[tid]['rate_picking_late'] = 0
                result[tid]['rate_picking_backorders'] = 0
        return result

    def _get_action(self, cr, uid, ids, action, context=None):
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        result = mod_obj.xmlid_to_res_id(cr, uid, action, raise_if_not_found=True)
        result = act_obj.read(cr, uid, [result], context=context)[0]
        if ids:
            picking_type = self.browse(cr, uid, ids[0], context=context)
            result['display_name'] = picking_type.display_name
        return result

    def get_action_picking_tree_late(self, cr, uid, ids, context=None):
        return self._get_action(cr, uid, ids, 'stock.action_picking_tree_late', context=context)

    def get_action_picking_tree_backorder(self, cr, uid, ids, context=None):
        return self._get_action(cr, uid, ids, 'stock.action_picking_tree_backorder', context=context)

    def get_action_picking_tree_waiting(self, cr, uid, ids, context=None):
        return self._get_action(cr, uid, ids, 'stock.action_picking_tree_waiting', context=context)

    def get_action_picking_tree_ready(self, cr, uid, ids, context=None):
        return self._get_action(cr, uid, ids, 'stock.action_picking_tree_ready', context=context)

    def get_stock_picking_action_picking_type(self, cr, uid, ids, context=None):
        return self._get_action(cr, uid, ids, 'stock.stock_picking_action_picking_type', context=context)


    def onchange_picking_code(self, cr, uid, ids, picking_code=False):
        if not picking_code:
            return False
        
        obj_data = self.pool.get('ir.model.data')
        stock_loc = obj_data.xmlid_to_res_id(cr, uid, 'stock.stock_location_stock')
        
        result = {
            'default_location_src_id': stock_loc,
            'default_location_dest_id': stock_loc,
        }
        if picking_code == 'incoming':
            result['default_location_src_id'] = obj_data.xmlid_to_res_id(cr, uid, 'stock.stock_location_suppliers')
        elif picking_code == 'outgoing':
            result['default_location_dest_id'] = obj_data.xmlid_to_res_id(cr, uid, 'stock.stock_location_customers')
        return {'value': result}

    def _get_name(self, cr, uid, ids, field_names, arg, context=None):
        return dict(self.name_get(cr, uid, ids, context=context))

    def name_get(self, cr, uid, ids, context=None):
        """Overides orm name_get method to display 'Warehouse_name: PickingType_name' """
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]
        res = []
        if not ids:
            return res
        for record in self.browse(cr, uid, ids, context=context):
            name = record.name
            if record.warehouse_id:
                name = record.warehouse_id.name + ': ' +name
            if context.get('special_shortened_wh_name'):
                if record.warehouse_id:
                    name = record.warehouse_id.name
                else:
                    name = _('Customer') + ' (' + record.name + ')'
            res.append((record.id, name))
        return res

    def _default_warehouse(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context)
        res = self.pool.get('stock.warehouse').search(cr, uid, [('company_id', '=', user.company_id.id)], limit=1, context=context)
        return res and res[0] or False

    _columns = {
        'name': fields.char('Picking Type Name', translate=True, required=True),
        'complete_name': fields.function(_get_name, type='char', string='Name'),
        'color': fields.integer('Color'),
        'sequence': fields.integer('Sequence', help="Used to order the 'All Operations' kanban view"),
        'sequence_id': fields.many2one('ir.sequence', 'Reference Sequence', required=True),
        'default_location_src_id': fields.many2one('stock.location', 'Default Source Location', help="This is the default source location when you create a picking manually with this picking type. It is possible however to change it or that the routes put another location. If it is empty, it will check for the supplier location on the partner. "),
        'default_location_dest_id': fields.many2one('stock.location', 'Default Destination Location', help="This is the default destination location when you create a picking manually with this picking type. It is possible however to change it or that the routes put another location. If it is empty, it will check for the customer location on the partner. "),
        'code': fields.selection([('incoming', 'Suppliers'), ('outgoing', 'Customers'), ('internal', 'Internal')], 'Type of Operation', required=True),
        'return_picking_type_id': fields.many2one('stock.picking.type', 'Picking Type for Returns'),
        'show_entire_packs': fields.boolean('Allow moving packs', help="If checked, this shows the packs to be moved as a whole in the Operations tab all the time, even if there was no entire pack reserved."),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse', ondelete='cascade'),
        'active': fields.boolean('Active'),
        'use_create_lots': fields.boolean('Create New Lots', help="If this is checked only, it will suppose you want to create new Serial Numbers / Lots, so you can provide them in a text field. "),
        'use_existing_lots': fields.boolean('Use Existing Lots', help="If this is checked, you will be able to choose the Serial Number / Lots. You can also decide to not put lots in this picking type.  This means it will create stock with no lot or not put a restriction on the lot taken. "),

        # Statistics for the kanban view
        'last_done_picking': fields.function(_get_tristate_values,
            type='char',
            string='Last 10 Done Pickings'),

        'count_picking_draft': fields.function(_get_picking_count,
            type='integer', multi='_get_picking_count'),
        'count_picking_ready': fields.function(_get_picking_count,
            type='integer', multi='_get_picking_count'),
        'count_picking': fields.function(_get_picking_count,
            type='integer', multi='_get_picking_count'),
        'count_picking_waiting': fields.function(_get_picking_count,
            type='integer', multi='_get_picking_count'),
        'count_picking_late': fields.function(_get_picking_count,
            type='integer', multi='_get_picking_count'),
        'count_picking_backorders': fields.function(_get_picking_count,
            type='integer', multi='_get_picking_count'),

        'rate_picking_late': fields.function(_get_picking_count,
            type='integer', multi='_get_picking_count'),
        'rate_picking_backorders': fields.function(_get_picking_count,
            type='integer', multi='_get_picking_count'),

        # Barcode nomenclature
        'barcode_nomenclature_id':  fields.many2one('barcode.nomenclature','Barcode Nomenclature', help='A barcode nomenclature'),
    }

    _defaults = {
        'warehouse_id': _default_warehouse,
        'active': True,
        'use_existing_lots': True,
        'use_create_lots': True,
    }

class barcode_rule(models.Model):
    _inherit = 'barcode.rule'

    def _get_type_selection(self):
        types = sets.Set(super(barcode_rule,self)._get_type_selection()) 
        types.update([
            ('weight','Weighted Product'),
            ('location','Location'),
            ('lot','Lot'),
            ('package','Package')
        ])
        return list(types)


class StockPackOperation(models.Model):
    _inherit = 'stock.pack.operation'

    @api.onchange('pack_lot_ids')
    def _onchange_packlots(self):
        self.qty_done = sum([x.qty for x in self.pack_lot_ids])
