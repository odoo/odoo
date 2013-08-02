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

from datetime import date, datetime
from dateutil import relativedelta

import time
from operator import itemgetter
from itertools import groupby

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import netsvc
from openerp import tools
from openerp.tools import float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from openerp import SUPERUSER_ID
import openerp.addons.decimal_precision as dp
from openerp.tools.float_utils import float_compare
import logging
_logger = logging.getLogger(__name__)

#----------------------------------------------------------
# Incoterms
#----------------------------------------------------------
class stock_incoterms(osv.osv):
    _name = "stock.incoterms"
    _description = "Incoterms"
    _columns = {
        'name': fields.char('Name', size=64, required=True, help="Incoterms are series of sales terms. They are used to divide transaction costs and responsibilities between buyer and seller and reflect state-of-the-art transportation practices."),
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
            parent = m.location_id
            while parent:
                res[m.id] = parent.name + ' / ' + res[m.id]
                parent = parent.location_id
        return res

    def _get_sublocations(self, cr, uid, ids, context=None):
        """ return all sublocations of the given stock locations (included) """
        return self.search(cr, uid, [('id', 'child_of', ids)], context=context)

    _columns = {
        'name': fields.char('Location Name', size=64, required=True, translate=True),
        'active': fields.boolean('Active', help="By unchecking the active field, you may hide a location without deleting it."),
        'usage': fields.selection([('supplier', 'Supplier Location'), ('view', 'View'), ('internal', 'Internal Location'), ('customer', 'Customer Location'), ('inventory', 'Inventory'), ('procurement', 'Procurement'), ('production', 'Production'), ('transit', 'Transit Location for Inter-Companies Transfers')], 'Location Type', required=True,
                 help="""* Supplier Location: Virtual location representing the source location for products coming from your suppliers
                       \n* View: Virtual location used to create a hierarchical structures for your warehouse, aggregating its child locations ; can't directly contain products
                       \n* Internal Location: Physical locations inside your own warehouses,
                       \n* Customer Location: Virtual location representing the destination location for products sent to your customers
                       \n* Inventory: Virtual location serving as counterpart for inventory operations used to correct stock levels (Physical inventories)
                       \n* Procurement: Virtual location serving as temporary counterpart for procurement operations when the source (supplier or production) is not known yet. This location should be empty when the procurement scheduler has finished running.
                       \n* Production: Virtual counterpart location for production operations: this location consumes the raw material and produces finished products
                      """, select = True),

        'complete_name': fields.function(_complete_name, type='char', string="Location Name",
                            store={'stock.location': (_get_sublocations, ['name', 'location_id'], 10)}),
        'location_id': fields.many2one('stock.location', 'Parent Location', select=True, ondelete='cascade'),
        'child_ids': fields.one2many('stock.location', 'location_id', 'Contains'),

        'partner_id': fields.many2one('res.partner', 'Owner', help="Owner of the location if not internal"),

        'comment': fields.text('Additional Information'),
        'posx': fields.integer('Corridor (X)', help="Optional localization details, for information purpose only"),
        'posy': fields.integer('Shelves (Y)', help="Optional localization details, for information purpose only"),
        'posz': fields.integer('Height (Z)', help="Optional localization details, for information purpose only"),

        'parent_left': fields.integer('Left Parent', select=1),
        'parent_right': fields.integer('Right Parent', select=1),

        'company_id': fields.many2one('res.company', 'Company', select=1, help='Let this field empty if this location is shared between all companies'),
        'scrap_location': fields.boolean('Scrap Location', help='Check this box to allow using this location to put scrapped/damaged goods.'),
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
    def get_removal_strategy(self, cr, uid, location, product, context=None):
        return None

#----------------------------------------------------------
# Quants
#----------------------------------------------------------

class stock_quant(osv.osv):
    """
    Quants are the smallest unit of stock physical instances
    """
    _name = "stock.quant"
    _description = "Quants"
    _columns = {
        'name': fields.char('Identifier'),
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'location_id': fields.many2one('stock.location', 'Location', required=True),
        'qty': fields.float('Quantity', required=True, help="Quantity of products in this quant, in the default unit of measure of the product"),
        'package_id': fields.many2one('stock.quant.package', string='Package', help="The package containing this quant"),
        'reservation_id': fields.many2one('stock.move', 'Reserved for Move', help="Is this quant reserved for a stock.move?"),
        'lot_id': fields.many2one('stock.production.lot', 'Lot'),
        'cost': fields.float('Unit Cost'),

        'create_date': fields.datetime('Creation Date'),
        'in_date': fields.datetime('Incoming Date'),

        'history_ids': fields.many2many('stock.move', 'stock_quant_move_rel', 'quant_id', 'move_id', 'Moves', help='Moves that operate(d) on this quant'),
        'company_id': fields.many2one('res.company', 'Company', help="The company to which the quants belong", required=True),

        # Used for negative quants to reconcile after compensated by a new positive one
        'propagated_from_id': fields.many2one('stock.quant', 'Linked Quant', help='The negative quant this is coming from'),
    }

    _defaults = {
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'stock.quant', context=c),
    }

    def _check_qorder(self, word):
        """
        Needs to pass True to allow "expression order" in search
        """
        return True

    def quants_reserve(self, cr, uid, quants, move, context=None):
        toreserve = []
        for quant,qty in quants:
            if not quant: continue
            self._quant_split(cr, uid, quant, qty, context=context)
            toreserve.append(quant.id)
        return self.write(cr, uid, toreserve, {'reservation_id': move.id}, context=context)

    # add location_dest_id in parameters (False=use the destination of the move)
    def quants_move(self, cr, uid, quants, move, context=None):
        for quant, qty in quants:
            self.move_single_quant(cr, uid, quant, qty, move, context=context)

    def check_preferred_location(self, cr, uid, move, context=None):
        return move.location_dest_id

    def move_single_quant(self, cr, uid, quant, qty, move, context=None):
        if not quant:
            quant = self._quant_create(cr, uid, qty, move, context=context)
        else:
            self._quant_split(cr, uid, quant, qty, context=context)
        # FP Note: improve this using preferred locations
        location_to = move.location_dest_id
        location_to = self.check_preferred_location(cr, uid, move, context=context)
        self.write(cr, uid, [quant.id], {
            'location_id': location_to.id,
            'reservation_id': move.move_dest_id and move.move_dest_id.id or False,
            'history_ids': [(4, move.id)]
        })
        quant.refresh()
        self._quant_reconcile_negative(cr, uid, quant, context=context)
        return quant

    def quants_get(self, cr, uid, location, product, qty, domain=None, prefered_order=False, reservedcontext=None, context=None):
        """
        Use the removal strategies of product to search for the correct quants
        If you inherit, put the super at the end of your method.

        :location: browse record of the parent location in which the quants have to be found
        :product: browse record of the product to find
        :qty in UoM of product
        :lot_id NOT USED YET !
        """
        result = []
        domain = domain or [('qty','>',0.0)]
        if location:
            removal_strategy = self.pool.get('stock.location').get_removal_strategy(cr, uid, location, product, context=context) or 'fifo'
            if removal_strategy=='fifo':
                result += self._quants_get_fifo(cr, uid, location, product, qty, domain, prefered_order=prefered_order, context=context)
            elif removal_strategy=='lifo':
                result += self._quants_get_lifo(cr, uid, location, product, qty, domain, prefered_order=prefered_order, context=context)
            else:
                raise osv.except_osv(_('Error!'), _('Removal strategy %s not implemented.' % (removal_strategy,)))
        return result

    #
    # Create a quant in the destination location
    # Create a negative quant in the source location if it's an internal location
    # Reconcile a positive quant with a negative is possible
    #
    def _quant_create(self, cr, uid, qty, move, context=None):
        # FP Note: TODO: compute the right price according to the move, with currency convert
        # QTY is normally already converted to main product's UoM
        price_unit = move.price_unit
        vals = {
            'product_id': move.product_id.id,
            'location_id': move.location_dest_id.id,
            'qty': qty,
            'cost': price_unit,
            'history_ids': [(4, move.id)],
            'in_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'company_id': move.company_id.id,
        }

        negative_quant_id = False
        if move.location_id.usage == 'internal':
            #if we were trying to move something from an internal location and reach here (quant creation),
            #it means that a negative quant has to be created as well.
            negative_vals = vals.copy()
            negative_vals['location_id'] = move.location_id.id
            negative_vals['qty'] = -qty
            negative_vals['cost'] = price_unit
            negative_quant_id = self.create(cr, uid, negative_vals, context=context)

        #create the quant
        vals.update({'propagated_from_id': negative_quant_id})
        quant_id = self.create(cr, uid, vals, context=context)
        return self.browse(cr, uid, quant_id, context=context)

    def _quant_split(self, cr, uid, quant, qty, context=None):
        context = context or {}
        if (quant.qty > 0 and quant.qty <= qty) or (quant.qty <= 0 and quant.qty >= qty):
            return False
        new_quant = self.copy(cr, uid, quant.id, default={'qty': quant.qty - qty}, context=context)
        self.write(cr, uid, quant.id, {'qty': qty}, context=context)
        quant.refresh()
        return self.browse(cr, uid, new_quant, context=context)

    def _get_latest_move(self, cr, uid, quant, context=None):
        move = False
        for m in quant.history_ids:
            if not move or m.date > move.date:
                move = m
        return move

    def _quant_reconcile_negative(self, cr, uid, quant, context=None):
        """
            When new quant arrive in a location, try to reconcile it with
            negative quants. If it's possible, apply the cost of the new
            quant to the conter-part of the negative quant.
        """
        if quant.location_id.usage != 'internal':
            return False
        quants = self.quants_get(cr, uid, quant.location_id, quant.product_id, quant.qty, [('qty', '<', '0')], context=context)
        result = False
        for quant_neg, qty in quants:
            if not quant_neg:
                continue
            result = True
            to_solve_quant = self.search(cr, uid, [('propagated_from_id', '=', quant_neg.id), ('id', '!=', quant.id)], context=context)
            if not to_solve_quant:
                continue
            to_solve_quant = self.browse(cr, uid, to_solve_quant[0], context=context)
            move = self._get_latest_move(cr, uid, to_solve_quant, context=context)
            self._quant_split(cr, uid, quant, qty, context=context)
            remaining_to_solve_quant = self._quant_split(cr, uid, to_solve_quant, qty, context=context)
            remaining_neg_quant = self._quant_split(cr, uid, quant_neg, -qty, context=context)
            #if the reconciliation was not complete, we need to link together the remaining parts
            if remaining_to_solve_quant and remaining_neg_quant:
                self.write(cr, uid, remaining_to_solve_quant.id, {'propagated_from_id': remaining_neg_quant.id}, context=context)
            #delete the reconciled quants, as it is replaced by the solving quant
            self.unlink(cr, SUPERUSER_ID, [quant_neg.id, to_solve_quant.id], context=context)
            #call move_single_quant to ensure recursivity if necessary and do the stock valuation
            self.move_single_quant(cr, uid, quant, qty, move, context=context)
        return result

    def _price_update(self, cr, uid, quant, newprice, context=None):
        self.write(cr, uid, [quant.id], {'cost': newprice}, context=context)

    def quants_unreserve(self, cr, uid, move, context=None):
        cr.execute('update stock_quant set reservation_id=NULL where reservation_id=%s', (move.id,))
        return True

    #
    # Implementation of removal strategies
    # If it can not reserve, it will return a tuple (None, qty)
    #
    def _quants_get_order(self, cr, uid, location, product, quantity, domain=[], orderby='in_date', context=None):
        domain += location and [('location_id', 'child_of', location.id)] or []
        domain += [('product_id','=',product.id)] + domain
        res = []
        offset = 0
        while quantity > 0:
            quants = self.search(cr, uid, domain, order=orderby, limit=10, offset=offset, context=context)
            if not quants:
                res.append((None, quantity))
                break
            for quant in self.browse(cr, uid, quants, context=context):
                if quantity >= abs(quant.qty):
                    res += [(quant, abs(quant.qty))]
                    quantity -= abs(quant.qty)
                elif quantity != 0:
                    res += [(quant, quantity)]
                    quantity = 0
                    break
            offset += 10
        return res

    def _quants_get_fifo(self, cr, uid, location, product, quantity, domain=[], prefered_order=False,context=None):
        order = 'in_date'
        if prefered_order:
            order = prefered_order + ', in_date'
        return self._quants_get_order(cr, uid, location, product, quantity, domain, order, context=context)

    def _quants_get_lifo(self, cr, uid, location, product, quantity, domain=[], prefered_order=False, context=None):
        order = 'in_date desc'
        if prefered_order:
            order = prefered_order + ', in_date desc'
        return self._quants_get_order(cr, uid, location, product, quantity, domain, order, context=context)

    # Return the company owning the location if any
    def _location_owner(self, cr, uid, quant, location, context=None):
        return location and (location.usage == 'internal') and location.company_id or False

    def _check_location(self, cr, uid, ids, context=None):
        for record in self.browse(cr, uid, ids, context=context):
            if record.location_id.usage == 'view':
                raise osv.except_osv(_('Error'), _('You cannot move product %s to a location of type view %s.')% (record.product_id.name, record.location_id.name))
        return True

    _constraints = [
        (_check_location, 'You cannot move products to a location of the type view.', ['location_id'])
    ]


#----------------------------------------------------------
# Stock Picking
#----------------------------------------------------------

class stock_picking(osv.osv):
    _name = "stock.picking"
    _inherit = ['mail.thread']
    _description = "Picking List"
    _order = "id desc"
    def get_min_max_date(self, cr, uid, ids, field_name, arg, context=None):
        """ Finds minimum and maximum dates for picking.
        @return: Dictionary of values
        """
        res = {}
        for id in ids:
            res[id] = {'min_date': False, 'max_date': False}
        if not ids:
            return res
        cr.execute("""select
                picking_id,
                min(date_expected),
                max(date_expected)
            from
                stock_move
            where
                picking_id IN %s
            group by
                picking_id""",(tuple(ids),))
        for pick, dt1, dt2 in cr.fetchall():
            res[pick]['min_date'] = dt1
            res[pick]['max_date'] = dt2
        return res

    def create(self, cr, user, vals, context=None):
        context = context or {}
        if ('name' not in vals) or (vals.get('name') in ('/', False)):
            ptype_id = vals.get('picking_type_id', context.get('default_picking_type_id', False))
            sequence_id = self.pool.get('stock.picking.type').browse(cr, user, ptype_id, context=context).sequence_id.id
            vals['name'] = self.pool.get('ir.sequence').get_id(cr, user, sequence_id, 'id', context=context)
        return super(stock_picking, self).create(cr, user, vals, context)

    # The state of a picking depends on the state of its related stock.move
    # draft: the picking has no line or any one of the lines is draft
    # done, draft, cancel: all lines are done / draft / cancel
    # confirmed, auto, assigned depends on move_type (all at once or direct)
    def _state_get(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for pick in self.browse(cr, uid, ids, context=context):
            if (not pick.move_lines) or any([x.state == 'draft' for x in pick.move_lines]):
                res[pick.id] = 'draft'
                continue
            if all([x.state == 'cancel' for x in pick.move_lines]):
                res[pick.id] = 'cancel'
                continue
            if all([x.state in ('cancel','done') for x in pick.move_lines]):
                res[pick.id] = 'done'
                continue

            order = {'confirmed':0, 'auto':1, 'assigned':2}
            order_inv = dict(zip(order.values(),order.keys()))
            lst = [order[x.state] for x in pick.move_lines if x.state not in ('cancel','done')]
            if pick.move_lines == 'one':
                res[pick.id] = order_inv[min(lst)]
            else:
                res[pick.id] = order_inv[max(lst)]
        return res

    def _get_pickings(self, cr, uid, ids, context=None):
        res = set()
        for move in self.browse(cr, uid, ids, context=context):
            if move.picking_id:
                res.add(move.picking_id.id)
        return list(res)

    def _get_pack_operation_exist(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for pick in self.browse(cr, uid, ids, context=context):
            res[pick.id] = False
            if pick.pack_operation_ids:
                res[pick.id] = True
        return res

    _columns = {
        'name': fields.char('Reference', size=64, select=True, states={'done':[('readonly', True)], 'cancel':[('readonly',True)]}),
        'origin': fields.char('Source Document', size=64, states={'done':[('readonly', True)], 'cancel':[('readonly',True)]}, help="Reference of the document", select=True),
        'backorder_id': fields.many2one('stock.picking', 'Back Order of', states={'done':[('readonly', True)], 'cancel':[('readonly',True)]}, help="If this shipment was split, then this field links to the shipment which contains the already processed part.", select=True),
        'note': fields.text('Notes', states={'done':[('readonly', True)], 'cancel':[('readonly',True)]}),
        'move_type': fields.selection([('direct', 'Partial'), ('one', 'All at once')], 'Delivery Method', required=True, states={'done':[('readonly', True)], 'cancel':[('readonly',True)]}, help="It specifies goods to be deliver partially or all at once"),
        'state': fields.function(_state_get, type="selection", store = {
            'stock.picking': (lambda self, cr, uid, ids, ctx: ids, ['move_type', 'move_lines'], 20),
            'stock.move': (_get_pickings, ['state', 'picking_id'], 20)}, selection = [
            ('draft', 'Draft'),
            ('cancel', 'Cancelled'),
            ('auto', 'Waiting Another Operation'),
            ('confirmed', 'Waiting Availability'),
            ('assigned', 'Ready to Transfer'),
            ('done', 'Transferred'),
            ], string='Status', readonly=True, select=True, track_visibility='onchange', help="""
            * Draft: not confirmed yet and will not be scheduled until confirmed\n
            * Waiting Another Operation: waiting for another move to proceed before it becomes automatically available (e.g. in Make-To-Order flows)\n
            * Waiting Availability: still waiting for the availability of products\n
            * Ready to Transfer: products reserved, simply waiting for confirmation.\n
            * Transferred: has been processed, can't be modified or cancelled anymore\n
            * Cancelled: has been cancelled, can't be confirmed anymore"""
        ),
        'min_date': fields.function(get_min_max_date, multi="min_max_date",
                 store={'stock.move': (_get_pickings, ['state'], 20)}, type='datetime', string='Scheduled Time', select=1, help="Scheduled time for the shipment to be processed"),
        'max_date': fields.function(get_min_max_date, multi="min_max_date",
                 store={'stock.move': (_get_pickings, ['state'], 20)}, type='datetime', string='Max. Expected Date', select=2),
        'date': fields.datetime('Creation Date', help="Creation date, usually the time of the order.", select=True, states={'done':[('readonly', True)], 'cancel':[('readonly',True)]}),
        'date_done': fields.datetime('Date of Transfer', help="Date of Completion", states={'done':[('readonly', True)], 'cancel':[('readonly',True)]}),
        'move_lines': fields.one2many('stock.move', 'picking_id', 'Internal Moves', states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}),
        'partner_id': fields.many2one('res.partner', 'Partner', states={'done':[('readonly', True)], 'cancel':[('readonly',True)]}),
        'company_id': fields.many2one('res.company', 'Company', required=True, select=True, states={'done':[('readonly', True)], 'cancel':[('readonly',True)]}),
        'pack_operation_ids': fields.one2many('stock.pack.operation', 'picking_id', string='Related Packing Operations'),
        'pack_operation_exist': fields.function(_get_pack_operation_exist, type='boolean', string='Pack Operation Exists?', help='technical field for attrs in view'),
        'picking_type_id': fields.many2one('stock.picking.type', 'Picking Type', required=True),

        # Used to search on pickings
        'product_id': fields.related('move_lines', 'product_id', type='many2one', relation='product.product', string='Product'),#?
        'location_id': fields.related('move_lines', 'location_id', type='many2one', relation='stock.location', string='Location', readonly=True),
        'location_dest_id': fields.related('move_lines', 'location_dest_id', type='many2one', relation='stock.location', string='Destination Location', readonly=True),
        'group_id': fields.related('move_lines', 'group_id', type='many2one', relation='procurement.group', string='Procurement Group', readonly=True),
    }
    _defaults = {
        'name': lambda self, cr, uid, context: '/',
        'state': 'draft',
        'move_type': 'one',
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'stock.picking', context=c)
    }
    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)', 'Reference must be unique per company!'),
    ]

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default = default.copy()
        picking_obj = self.browse(cr, uid, id, context=context)
        move_obj = self.pool.get('stock.move')
        if ('name' not in default) or (picking_obj.name == '/'):
            default['name'] = '/'
            default['origin'] = ''
            default['backorder_id'] = False
        return super(stock_picking, self).copy(cr, uid, id, default, context)

    def action_confirm(self, cr, uid, ids, context=None):
        todo = []
        for picking in self.browse(cr, uid, ids, context=context):
            for r in picking.move_lines:
                if r.state == 'draft':
                    todo.append(r.id)
        if len(todo):
            self.pool.get('stock.move').action_confirm(cr, uid, todo, context=context)
        return True

    def action_assign(self, cr, uid, ids, *args):
        """ Changes state of picking to available if all moves are confirmed.
        @return: True
        """
        for pick in self.browse(cr, uid, ids):
            if pick.state == 'draft':
                self.action_confirm(cr, uid, [pick.id])
            move_ids = [x.id for x in pick.move_lines if x.state == 'confirmed']
            if not move_ids:
                raise osv.except_osv(_('Warning!'),_('No product available.'))
            self.pool.get('stock.move').action_assign(cr, uid, move_ids)
        return True

    def force_assign(self, cr, uid, ids, *args):
        """ Changes state of picking to available if moves are confirmed or waiting.
        @return: True
        """
        for pick in self.browse(cr, uid, ids):
            move_ids = [x.id for x in pick.move_lines if x.state in ['confirmed','waiting']]
            self.pool.get('stock.move').force_assign(cr, uid, move_ids)
        return True

    def cancel_assign(self, cr, uid, ids, *args):
        """ Cancels picking and moves.
        @return: True
        """
        for pick in self.browse(cr, uid, ids):
            move_ids = [x.id for x in pick.move_lines]
            self.pool.get('stock.move').cancel_assign(cr, uid, move_ids)
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
                    self.pool.get('stock.move').action_confirm(cr, uid, [move.id],
                        context=context)
                    todo.append(move.id)
                elif move.state in ('assigned','confirmed'):
                    todo.append(move.id)
            if len(todo):
                self.pool.get('stock.move').action_done(cr, uid, todo, context=context)
        return True

    def unlink(self, cr, uid, ids, context=None):
        move_obj = self.pool.get('stock.move')
        context = context or {}
        for pick in self.browse(cr, uid, ids, context=context):
            ids2 = [move.id for move in pick.move_lines]
            move_obj.action_cancel(cr, uid, ids2, context=context)
            move_obj.unlink(cr, uid, ids2, context=context)
        return super(stock_picking, self).unlink(cr, uid, ids, context=context)

    # Methods for partial pickings


    def _create_backorder(self, cr, uid, picking, context=None):
        """
            Move all non-done lines into a new backorder picking
        """
        backorder_id = self.copy(cr, uid, picking.id, {
            'name': '/',
            'move_lines': [],
            'pack_operation_ids': [],
            'backorder_id': picking.id,
        })
        back_order_name = self.browse(cr, uid, backorder_id, context=context).name
        self.message_post(cr, uid, picking.id, body=_("Back order <em>%s</em> <b>created</b>.") % (back_order_name), context=context)
        notdone_move_ids = [x.id for x in picking.move_lines if x.state not in ('done','cancel')]
        self.pool.get('stock.move').write(cr, uid, notdone_move_ids, {'picking_id': backorder_id}, context=context)
        return backorder_id

    def do_prepare_partial(self, cr, uid, picking_ids, context=None):
        context = context or {}
        pack_operation_obj = self.pool.get('stock.pack.operation')
        for picking in self.browse(cr, uid, picking_ids, context=context):
            for move in picking.move_lines:
                if move.state <> 'assigned': continue
                remaining_qty = move.product_qty
                for quant in move.reserved_quant_ids:
                    qty = min(quant.qty, move.product_qty)
                    remaining_qty -= qty
                    pack_operation_obj.create(cr, uid, {
                        'picking_id': picking.id,
                        'product_qty': qty,
                        'quant_id': quant.id,
                        'product_id': quant.product_id.id,
                        'product_uom_id': quant.product_id.uom_id.id,
                        'cost': quant.cost,
                    }, context=context)
                if remaining_qty > 0:
                    pack_operation_obj.create(cr, uid, {
                        'picking_id': picking.id,
                        'product_qty': remaining_qty,
                        'product_id': move.product_id.id,
                        'product_uom_id': move.product_id.uom_id.id,
                        'cost': move.product_id.standard_price,
                    }, context=context)

    def _do_partial_product_move(self, cr, uid, picking, product, qty, quant=False, context=None):
        moves = []
        stock_move_obj = self.pool.get('stock.move')
        for move in picking.move_lines:
            if move.state in ('cancel','done'): continue
            if move.product_id.id == product.id:
                todo = min(move.product_qty, qty)
                partial_datas = {
                    'product_qty': todo,
                    'product_uom_id': product.uom_id.id,
                    'reserved_quant_ids': quant and [(4, quant.id)] or [],
                }
                newmove_id = stock_move_obj.split(cr, uid, move, todo, context=context)
                stock_move_obj.action_done(cr, uid, [newmove_id], context=context)

                # TODO: To be removed after new API implementation
                move.refresh()
                moves.append(move)

                qty -= todo
                if qty<=0: break
        if qty>0:
            move_id = stock_move_obj.create(cr, uid, {
                'name': product.name,
                'product_id': product.id,
                'product_uom_qty': qty,
                'product_uom': product.uom_id.id,
                'location_id': picking.location_id.id,
                'location_dest_id': picking.location_dest_id.id,
                'picking_id': picking.id,
                'reserved_quant_ids': quant and [(4,quant.id)] or [],
                'picking_type_id': picking.picking_type_id.id
            }, context=context)
            stock_move_obj.action_done(cr, uid, [move_id], context=context)
            move = stock_move_obj.browse(cr, uid, move_id, context=context)
            moves.append(move)
        return moves

    def do_partial(self, cr, uid, picking_ids, context=None):
        """
            If no pack operation, we close the whole move
            Otherwise, do the pack operations
        """
        #TODO: this variable should be in argument
        quant_obj = self.pool.get('stock.quant')
        for picking in self.browse(cr, uid, picking_ids, context=context):
            if not picking.pack_operation_ids:
                self.action_done(cr, uid, [picking.id], context=context)
                continue
            for op in picking.pack_operation_ids:
                if op.package_id:
                    for quant in quant_package_obj.quants_get(cr, uid, op.package_id, context=context):
                        self._do_partial_product_move(cr, uid, picking, quant.product_id, quant.qty, quant, context=context)
                    op.package_id.write(cr, uid, {
                        'parent_id': op.result_package_id.id
                    }, context=context)
                elif op.product_id:
                    moves = self._do_partial_product_move(cr, uid, picking, op.product_id, op.product_qty, op.quant_id, context=context)
                    quants = []
                    for m in moves:
                        for quant in m.quant_ids:
                            quants.append(quant.id)
                    quant_obj.write(cr, uid, quants, {
                        'package_id': op.result_package_id.id
                    }, context=context)

            self._create_backorder(cr, uid, picking, context=context)
        return True

    # Methods for the barcode UI

    def _get_picking_for_packing_ui(self, cr, uid, context=None):
        res = self.search(cr, uid, [('state', '=', 'assigned')], limit=1, context=context)
        return res and res[0] or False  # TODO: what to do if nothing is left to do?

    def action_done_from_packing_ui(self, cr, uid, picking_id, only_split_lines=False, context=None):
        self.do_partial(cr, uid, picking_id, only_split_lines, context=context)
        #return id of next picking to work on
        return self._get_picking_for_packing_ui(cr, uid, context=context)

    def action_pack(self, cr, uid, picking_ids, context=None):
        stock_operation_obj = self.pool.get('stock.pack.operation')
        package_obj = self.pool.get('stock.quant.package')
        for picking_id in picking_ids:
            operation_ids = stock_operation_obj.search(cr, uid, [('picking_id', '=', picking_id), ('result_package_id', '=', False)], context=context)
            if operation_ids:
                package_id = package_obj.create(cr, uid, {}, context=context)
                stock_operation_obj.write(cr, uid, operation_ids, {'result_package_id': package_id}, context=context)
        return True

    def _deal_with_quants(self, cr, uid, picking_id, quant_ids, context=None):
        stock_operation_obj = self.pool.get('stock.pack.operation')
        todo_on_moves = []
        todo_on_operations = []
        for quant in self.pool.get('stock.quant').browse(cr, uid, quant_ids, context=context):
            tmp_moves, tmp_operations = stock_operation_obj._search_and_increment(cr, uid, picking_id, ('quant_id', '=', quant.id), context=context)
            todo_on_moves += tmp_moves
            todo_on_operations += tmp_operations
        return todo_on_moves, todo_on_operations

    def get_barcode_and_return_todo_stuff(self, cr, uid, picking_id, barcode_str, context=None):
        '''This function is called each time there barcode scanner reads an input'''
        #TODO: better error messages handling => why not real raised errors
        quant_obj = self.pool.get('stock.quant')
        package_obj = self.pool.get('stock.quant.package')
        product_obj = self.pool.get('product.product')
        stock_operation_obj = self.pool.get('stock.pack.operation')
        error_msg = ''
        todo_on_moves = []
        todo_on_operations = []
        #check if the barcode correspond to a product
        matching_product_ids = product_obj.search(cr, uid, [('ean13', '=', barcode_str)], context=context)
        if matching_product_ids:
            todo_on_moves, todo_on_operations = stock_operation_obj._search_and_increment(cr, uid, picking_id, ('product_id', '=', matching_product_ids[0]), context=context)

        #check if the barcode correspond to a quant
        matching_quant_ids = quant_obj.search(cr, uid, [('name', '=', barcode_str)], context=context)  # TODO need the location clause
        if matching_quant_ids:
            todo_on_moves, todo_on_operations = self._deal_with_quants(cr, uid, picking_id, [matching_quant_ids[0]], context=context)

        #check if the barcode correspond to a package
        matching_package_ids = package_obj.search(cr, uid, [('name', '=', barcode_str)], context=context)
        if matching_package_ids:
            included_package_ids = package_obj.search(cr, uid, [('parent_id', 'child_of', matching_package_ids[0])], context=context)
            included_quant_ids = quant_obj.search(cr, uid, [('package_id', 'in', included_package_ids)], context=context)
            todo_on_moves, todo_on_operations = self._deal_with_quants(cr, uid, picking_id, included_quant_ids, context=context)
        #write remaining qty on stock.move, to ease the treatment server side
        for todo in todo_on_moves:
            if todo[0] == 1:
                self.pool.get('stock.move').write(cr, uid, todo[1], todo[2], context=context)
            elif todo[0] == 0:
                self.pool.get('stock.move').create(cr, uid, todo[2], context=context)
        return {'warnings': error_msg, 'moves_to_update': todo_on_moves, 'operations_to_update': todo_on_operations}


class stock_production_lot(osv.osv):
    _name = 'stock.production.lot'
    _inherit = ['mail.thread']
    _description = 'Lot/Serial'
    _columns = {
        'name': fields.char('Serial Number', size=64, required=True, help="Unique Serial Number"),
        'ref': fields.char('Internal Reference', size=256, help="Internal reference number in case it differs from the manufacturer's serial number"),
        'product_id': fields.many2one('product.product', 'Product', required=True, domain=[('type', '<>', 'service')]),
        'quant_ids': fields.one2many('stock.quant', 'lot_id', 'Quants'),
        'create_date': fields.datetime('Creation Date'),
        'partner_id': fields.many2one('res.partner', 'Owner'),
    }
    _defaults = {
        'name': lambda x, y, z, c: x.pool.get('ir.sequence').get(y, z, 'stock.lot.serial'),
        'product_id': lambda x, y, z, c: c.get('product_id', False),
    }
    _sql_constraints = [
        ('name_ref_uniq', 'unique (name, ref)', 'The combination of Serial Number and internal reference must be unique !'),
    ]


# ----------------------------------------------------
# Move
# ----------------------------------------------------

class stock_move(osv.osv):
    _name = "stock.move"
    _description = "Stock Move"
    _order = 'date_expected desc, id'
    _log_create = False

    def name_get(self, cr, uid, ids, context=None):
        res = []
        for line in self.browse(cr, uid, ids, context=context):
            name = line.location_id.name+' > '+line.location_dest_id.name
            if line.product_id.code:
                name = line.product_id.code + ': ' + name
            if line.picking_id.origin:
                name = line.picking_id.origin + '/ ' + name
            res.append((line.id, name))
        return res

    # FP Note: put this on quants, with the auto creation algo
    # def _check_tracking(self, cr, uid, ids, context=None):
    #     """ Checks if serial number is assigned to stock move or not.
    #     @return: True or False
    #     """
    #     for move in self.browse(cr, uid, ids, context=context):
    #         if not move.lot_id and \
    #            (move.state == 'done' and \
    #            ( \
    #                (move.product_id.track_production and move.location_id.usage == 'production') or \
    #                (move.product_id.track_production and move.location_dest_id.usage == 'production') or \
    #                (move.product_id.track_incoming and move.location_id.usage == 'supplier') or \
    #                (move.product_id.track_outgoing and move.location_dest_id.usage == 'customer') or \
    #                (move.product_id.track_incoming and move.location_id.usage == 'inventory') \
    #            )):
    #             return False
    #     return True

    def _quantity_normalize(self, cr, uid, ids, name, args, context=None):
        uom_obj = self.pool.get('product.uom')
        res = {}
        for m in self.browse(cr, uid, ids, context=context):
            res[m.id] = uom_obj._compute_qty_obj(cr, uid, m.product_uom, m.product_uom_qty, m.product_id.uom_id)
        return res

    def _get_remaining_qty(self, cr, uid, ids, field_name, args, context=None):
        #TODO: this function assumes that there aren't several stock move in the same picking with the same product. what should we do in that case?
        #TODO take care of the quant on stock moves too
        res = dict.fromkeys(ids, False)
        for move in self.browse(cr, uid, ids, context=context):
            res[move.id] = move.product_qty
            if move.picking_id:
                for op in move.picking_id.pack_operation_ids:
                    if op.product_id == move.product_id or (op.quant_id and op.quant_id.product_id == move.product_id):
                        res[move.id] -= op.product_qty
                    if op.package_id:
                        #find the product qty recursively
                        res[move.id] -= self.pool.get('stock.quant.package')._get_product_total_qty(cr, uid, op.package_id, move.product_id.id, context=context)
        return res

    _columns = {
        'name': fields.char('Description', required=True, select=True),
        'priority': fields.selection([('0', 'Not urgent'), ('1', 'Urgent')], 'Priority'),
        'create_date': fields.datetime('Creation Date', readonly=True, select=True),
        'date': fields.datetime('Date', required=True, select=True, help="Move date: scheduled date until move is done, then date of actual move processing", states={'done': [('readonly', True)]}),
        'date_expected': fields.datetime('Scheduled Date', states={'done': [('readonly', True)]},required=True, select=True, help="Scheduled date for the processing of this move"),
        'product_id': fields.many2one('product.product', 'Product', required=True, select=True, domain=[('type','<>','service')],states={'done': [('readonly', True)]}),
        # TODO: improve store to add dependency on product UoM
        'product_qty': fields.function(_quantity_normalize, type='float', store=True, string='Quantity',
            digits_compute=dp.get_precision('Product Unit of Measure'),
            help='Quantity in the default UoM of the product'),
        'product_uom_qty': fields.float('Quantity', digits_compute=dp.get_precision('Product Unit of Measure'),
            required=True,states={'done': [('readonly', True)]},
            help="This is the quantity of products from an inventory "
                "point of view. For moves in the state 'done', this is the "
                "quantity of products that were actually moved. For other "
                "moves, this is the quantity of product that is planned to "
                "be moved. Lowering this quantity does not generate a "
                "backorder. Changing this quantity on assigned moves affects "
                "the product reservation, and should be done with care."
        ),
        'product_uom': fields.many2one('product.uom', 'Unit of Measure', required=True,states={'done': [('readonly', True)]}),
        'product_uos_qty': fields.float('Quantity (UOS)', digits_compute=dp.get_precision('Product Unit of Measure'), states={'done': [('readonly', True)]}),
        'product_uos': fields.many2one('product.uom', 'Product UOS', states={'done': [('readonly', True)]}),

        'product_packaging': fields.many2one('product.packaging', 'Prefered Packaging', help="It specifies attributes of packaging like type, quantity of packaging,etc."),

        'location_id': fields.many2one('stock.location', 'Source Location', required=True, select=True,states={'done': [('readonly', True)]}, help="Sets a location if you produce at a fixed location. This can be a partner location if you subcontract the manufacturing operations."),
        'location_dest_id': fields.many2one('stock.location', 'Destination Location', required=True,states={'done': [('readonly', True)]}, select=True, help="Location where the system will stock the finished products."),

        # FP Note: should we remove this?
        'partner_id': fields.many2one('res.partner', 'Destination Address ', states={'done': [('readonly', True)]}, help="Optional address where goods are to be delivered, specifically used for allotment"),


        'move_dest_id': fields.many2one('stock.move', 'Destination Move', help="Optional: next stock move when chaining them", select=True),
        'move_orig_ids': fields.one2many('stock.move', 'move_dest_id', 'Original Move', help="Optional: previous stock move when chaining them", select=True),

        'picking_id': fields.many2one('stock.picking', 'Reference', select=True,states={'done': [('readonly', True)]}),
        'note': fields.text('Notes'),
        'state': fields.selection([('draft', 'New'),
                                   ('cancel', 'Cancelled'),
                                   ('waiting', 'Waiting Another Move'),
                                   ('confirmed', 'Waiting Availability'),
                                   ('assigned', 'Available'),
                                   ('done', 'Done'),
                                   ], 'Status', readonly=True, select=True,
                 help= "* New: When the stock move is created and not yet confirmed.\n"\
                       "* Waiting Another Move: This state can be seen when a move is waiting for another one, for example in a chained flow.\n"\
                       "* Waiting Availability: This state is reached when the procurement resolution is not straight forward. It may need the scheduler to run, a component to me manufactured...\n"\
                       "* Available: When products are reserved, it is set to \'Available\'.\n"\
                       "* Done: When the shipment is processed, the state is \'Done\'."),

        'price_unit': fields.float('Unit Price', help="Technical field used to record the product cost set by the user during a picking confirmation (when average price costing method is used)"),  # as it's a technical field, we intentionally don't provide the digits attribute
        'price_currency_id': fields.many2one('res.currency', 'Currency for average price', help="Technical field used to record the currency chosen by the user during a picking confirmation (when average price costing method is used)"),

        'company_id': fields.many2one('res.company', 'Company', required=True, select=True),
        'backorder_id': fields.related('picking_id','backorder_id',type='many2one', relation="stock.picking", string="Back Order of", select=True),
        'origin': fields.related('picking_id','origin',type='char', size=64, relation="stock.picking", string="Source", store=True),
        'procure_method': fields.selection([('make_to_stock','Make to Stock'),('make_to_order','Make to Order')], 'Procurement Method', required=True, help="Make to Stock: When needed, the product is taken from the stock or we wait for replenishment. \nMake to Order: When needed, the product is purchased or produced."),

        # used for colors in tree views:
        'scrapped': fields.related('location_dest_id','scrap_location',type='boolean',relation='stock.location',string='Scrapped', readonly=True),

        'quant_ids': fields.many2many('stock.quant',  'stock_quant_move_rel', 'move_id', 'quant_id', 'Quants'),
        'reserved_quant_ids': fields.one2many('stock.quant', 'reservation_id', 'Reserved quants'),
        'remaining_qty': fields.function(_get_remaining_qty, type='float', string='Remaining Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), states={'done': [('readonly', True)]}),
        'group_id': fields.many2one('procurement.group', 'Procurement Group'),
        'rule_id': fields.many2one('procurement.rule', 'Procurement Rule'),
        'propagate': fields.boolean('Propagate cancel and split', help='If checked, when this move is cancelled, cancel the linked move too'),
        'picking_type_id': fields.many2one('stock.picking.type', 'Picking Type'),
    }

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default = default.copy()
        default['move_orig_ids'] = []
        default['quant_ids'] = []
        default['reserved_quant_ids'] = []
        default['state'] = 'draft'
        return super(stock_move, self).copy(cr, uid, id, default, context)

    def _default_location_destination(self, cr, uid, context=None):
        context = context or {}
        if context.get('default_picking_type_id', False):
            pick_type = self.pool.get('stock.picking.type').browse(cr, uid, context['default_picking_type_id'], context=context)
            return pick_type.default_location_dest_id and pick_type.default_location_dest_id.id or False
        return False

    def _default_location_source(self, cr, uid, context=None):
        context = context or {}
        if context.get('default_picking_type_id', False):
            pick_type = self.pool.get('stock.picking.type').browse(cr, uid, context['default_picking_type_id'], context=context)
            return pick_type.default_location_src_id and pick_type.default_location_src_id.id or False
        return False

    def _default_destination_address(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        return user.company_id.partner_id.id

    _defaults = {
        'location_id': _default_location_source,
        'location_dest_id': _default_location_destination,
        'partner_id': _default_destination_address,
        'state': 'draft',
        'priority': '1',
        'product_qty': 1.0,
        'scrapped': False,
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'stock.move', context=c),
        'date_expected': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'procure_method': 'make_to_stock',
        'propagate': True,
    }

    def _create_procurement(self, cr, uid, move, context=None):
        """
            This will create a procurement order
        """
        proc_obj = self.pool.get("procurement.order")
        origin = _('Procurement from %s created by rule %s') % (move.group_id and move.group_id.name or "", move.rule_id and move.rule_id.name or "")
        return proc_obj.create(cr, uid, {
                'name': _('MTO from rule %s') % move.rule_id and move.rule_id.name or "",
                'origin': origin,
                'company_id': move.company_id and move.company_id.id or False,
                'date_planned': move.date,
                'product_id': move.product_id.id,
                'product_qty': move.product_qty,
                'product_uom': move.product_uom.id,
                'product_uos_qty': (move.product_uos and move.product_uos_qty) or move.product_qty,
                'product_uos': (move.product_uos and move.product_uos.id) or move.product_uom.id,
                'location_id': move.location_id.id,
                'move_dest_id': move.id,
                'group_id': move.group_id and move.group_id.id or False,
            })

    # Check that we do not modify a stock.move which is done
    def write(self, cr, uid, ids, vals, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        frozen_fields = set(['product_qty', 'product_uom', 'product_uos_qty', 'product_uos', 'location_id', 'location_dest_id', 'product_id'])
        for move in self.browse(cr, uid, ids, context=context):
            if move.state == 'done':
                if frozen_fields.intersection(vals):
                    raise osv.except_osv(_('Operation Forbidden!'),
                        _('Quantities, Units of Measure, Products and Locations cannot be modified on stock moves that have already been processed (except by the Administrator).'))
        result = super(stock_move, self).write(cr, uid, ids, vals, context=context)
        return result

    def onchange_quantity(self, cr, uid, ids, product_id, product_qty,
                          product_uom, product_uos):
        """ On change of product quantity finds UoM and UoS quantities
        @param product_id: Product id
        @param product_qty: Changed Quantity of product
        @param product_uom: Unit of measure of product
        @param product_uos: Unit of sale of product
        @return: Dictionary of values
        """
        result = {
            'product_uos_qty': 0.00
        }
        warning = {}

        if (not product_id) or (product_qty <=0.0):
            result['product_qty'] = 0.0
            return {'value': result}

        product_obj = self.pool.get('product.product')
        uos_coeff = product_obj.read(cr, uid, product_id, ['uos_coeff'])

        # Warn if the quantity was decreased
        if ids:
            for move in self.read(cr, uid, ids, ['product_qty']):
                if product_qty < move['product_qty']:
                    warning.update({
                       'title': _('Information'),
                       'message': _("By changing this quantity here, you accept the "
                                "new quantity as complete: OpenERP will not "
                                "automatically generate a back order.") })
                break

        if product_uos and product_uom and (product_uom != product_uos):
            result['product_uos_qty'] = product_qty * uos_coeff['uos_coeff']
        else:
            result['product_uos_qty'] = product_qty

        return {'value': result, 'warning': warning}

    def onchange_uos_quantity(self, cr, uid, ids, product_id, product_uos_qty,
                          product_uos, product_uom):
        """ On change of product quantity finds UoM and UoS quantities
        @param product_id: Product id
        @param product_uos_qty: Changed UoS Quantity of product
        @param product_uom: Unit of measure of product
        @param product_uos: Unit of sale of product
        @return: Dictionary of values
        """
        result = {
            'product_uom_qty': 0.00
        }
        warning = {}

        if (not product_id) or (product_uos_qty <=0.0):
            result['product_uos_qty'] = 0.0
            return {'value': result}

        product_obj = self.pool.get('product.product')
        uos_coeff = product_obj.read(cr, uid, product_id, ['uos_coeff'])

        # Warn if the quantity was decreased
        for move in self.read(cr, uid, ids, ['product_uos_qty']):
            if product_uos_qty < move['product_uos_qty']:
                warning.update({
                   'title': _('Warning: No Back Order'),
                   'message': _("By changing the quantity here, you accept the "
                                "new quantity as complete: OpenERP will not "
                                "automatically generate a Back Order.") })
                break

        if product_uos and product_uom and (product_uom != product_uos):
            result['product_uom_qty'] = product_uos_qty / uos_coeff['uos_coeff']
        else:
            result['product_uom_qty'] = product_uos_qty
        return {'value': result, 'warning': warning}

    def onchange_product_id(self, cr, uid, ids, prod_id=False, loc_id=False,
                            loc_dest_id=False, partner_id=False):
        """ On change of product id, if finds UoM, UoS, quantity and UoS quantity.
        @param prod_id: Changed Product id
        @param loc_id: Source location id
        @param loc_dest_id: Destination location id
        @param partner_id: Address id of partner
        @return: Dictionary of values
        """
        if not prod_id:
            return {}
        lang = False
        if partner_id:
            addr_rec = self.pool.get('res.partner').browse(cr, uid, partner_id)
            if addr_rec:
                lang = addr_rec and addr_rec.lang or False
        ctx = {'lang': lang}

        product = self.pool.get('product.product').browse(cr, uid, [prod_id], context=ctx)[0]
        uos_id  = product.uos_id and product.uos_id.id or False
        result = {
            'product_uom': product.uom_id.id,
            'product_uos': uos_id,
            'product_uom_qty': 1.00,
            'product_uos_qty' : self.pool.get('stock.move').onchange_quantity(cr, uid, ids, prod_id, 1.00, product.uom_id.id, uos_id)['value']['product_uos_qty'],
        }
        if not ids:
            result['name'] = product.partner_ref
        if loc_id:
            result['location_id'] = loc_id
        if loc_dest_id:
            result['location_dest_id'] = loc_dest_id
        return {'value': result}

    def _picking_assign(self, cr, uid, move, context=None):
        if move.picking_id or not move.picking_type_id:
            return False
        context = context or {}
        pick_obj = self.pool.get("stock.picking")
        picks = []
        if move.group_id:
            picks = pick_obj.search(cr, uid, [
                ('group_id', '=', move.group_id.id),
                ('location_id', '=', move.location_id.id),
                ('location_dest_id', '=', move.location_dest_id.id),
                ('state', 'in', ['confirmed', 'auto'])], context=context)
        if picks:
            pick = picks[0]
        else:
            values = {
                'origin': move.origin,
                'company_id': move.company_id and move.company_id.id or False,
                'move_type': move.group_id and move.group_id.move_type or 'one',
                'partner_id': move.partner_id and move.partner_id.id or False,
                'date_done': move.date_expected,
                'state': 'confirmed',
                'group_id': move.group_id and move.group_id.id or False,
                'picking_type_id': move.picking_type_id and move.picking_type_id.id or False,
            }
            pick = pick_obj.create(cr, uid, values, context=context)
        move.write({'picking_id': pick})
        return True

    def onchange_date(self, cr, uid, ids, date, date_expected, context=None):
        """ On change of Scheduled Date gives a Move date.
        @param date_expected: Scheduled Date
        @param date: Move Date
        @return: Move Date
        """
        if not date_expected:
            date_expected = time.strftime('%Y-%m-%d %H:%M:%S')
        return {'value':{'date': date_expected}}

    def action_confirm(self, cr, uid, ids, context=None):
        """ Confirms stock move or put it in waiting if it's linked to another move.
        @return: List of ids.
        """
        states = {
            'confirmed': [],
            'waiting': []
        }
        for move in self.browse(cr, uid, ids, context=context):
            state = 'confirmed'
            for m in move.move_orig_ids:
                if m.state not in ('done', 'cancel'):
                    state = 'waiting'
            states[state].append(move.id)
            self._picking_assign(cr, uid, move, context=context)

        for state, write_ids in states.items():
            if len(write_ids):
                self.write(cr, uid, write_ids, {'state': state})
                if state == 'confirmed':
                    for move in self.browse(cr, uid, write_ids, context=context):
                        if move.procure_method == 'make_to_order':
                            self._create_procurement(cr, uid, move, context=context)
        return True

    def force_assign(self, cr, uid, ids, context=None):
        """ Changes the state to assigned.
        @return: True
        """
        done = self.action_assign(cr, uid, ids, context=context)
        self.write(cr, uid, list(set(ids) - set(done)), {'state': 'assigned'})
        return True


    def cancel_assign(self, cr, uid, ids, context=None):
        """ Changes the state to confirmed.
        @return: True
        """
        return self.write(cr, uid, ids, {'state': 'confirmed'})

    def action_assign(self, cr, uid, ids, context=None):
        """ Checks the product type and accordingly writes the state.
        @return: No. of moves done
        """
        context = context or {}
        quant_obj = self.pool.get("stock.quant")
        uom_obj = self.pool.get("product.uom")
        done = []
        for move in self.browse(cr, uid, ids, context=context):
            if move.state not in ('confirmed', 'waiting'):
                continue
            if move.product_id.type == 'consu':
                done.append(move.id)
                continue
            else:
                qty = uom_obj._compute_qty(cr, uid, move.product_uom.id, move.product_qty, move.product_id.uom_id.id)
                dp = []
                for m2 in move.move_orig_ids:
                    for q in m2.quant_ids:
                        dp.append(str(q.id))
                domain = ['|', ('reservation_id', '=', False), ('reservation_id', '=', move.id)]
                quants = quant_obj.quants_get(cr, uid, move.location_id, move.product_id, qty, domain=domain, prefered_order = dp and ('id not in ('+','.join(dp)+')') or False, context=context)
                #Will only reserve physical quants, no negative
                quant_obj.quants_reserve(cr, uid, quants, move, context=context)
                # the total quantity is provided by existing quants
                if all(map(lambda x:x[0], quants)):
                    done.append(move.id)
        self.write(cr, uid, done, {'state': 'assigned'})
        return done


    #
    # Cancel move => cancel others move and pickings
    #
    def action_cancel(self, cr, uid, ids, context=None):
        """ Cancels the moves and if all moves are cancelled it cancels the picking.
        @return: True
        """
        context = context or {}
        for move in self.browse(cr, uid, ids, context=context):
            if move.move_dest_id:
                if move.propagate:
                    self.action_cancel(cr, uid, [move.move_dest_id.id], context=context)
                elif move.move_dest_id.state == 'waiting':
                    self.write(cr, uid, [move.move_dest_id.id], {'state': 'confirmed'})
        return self.write(cr, uid, ids, {'state': 'cancel', 'move_dest_id': False})

    #def _get_quants_from_pack(self, cr, uid, ids, context=None):
    #    """
    #    Suppose for the moment we don't have any packaging
    #    """
    #    res = {}
    #    for move in self.browse(cr, uid, ids, context=context):
    #        #Split according to pack wizard if necessary
    #        res[move.id] = [x.id for x in move.reserved_quant_ids]
    #    return res

    def action_done(self, cr, uid, ids, context=None):
        """ Makes the move done and if all moves are done, it will finish the picking.
        If quants are not assigned yet, it should assign them
        Putaway strategies should be applied
        @return:
        """
        context = context or {}
        quant_obj = self.pool.get("stock.quant")
        picking_obj = self.pool.get('stock.picking')

        todo = [move.id for move in self.browse(cr, uid, ids, context=context) if move.state == "draft"]
        if todo:
            self.action_confirm(cr, uid, todo, context=context)

        pickings = set()
        for move in self.browse(cr, uid, ids, context=context):
            if move.picking_id:
                pickings.add(move.picking_id.id)
            qty = move.product_uom_qty

            # for qty, location_id in move_id.prefered_location_ids:
            #    quants = quant_obj.quants_get(cr, uid, move.location_id, move.product_id, qty, context=context)
            #    quant_obj.quants_move(cr, uid, quants, move, location_dest_id, context=context)
            # should replace the above 2 lines
            domain = ['|', ('reservation_id', '=', False), ('reservation_id', '=', move.id)]
            quants = quant_obj.quants_get(cr, uid, move.location_id, move.product_id, qty, domain=domain, prefered_order = 'reservation_id<>'+str(move.id),  context=context)
            #Will move all quants_get and as such create negative quants
            quant_obj.quants_move(cr, uid, quants, move, context=context)
            quant_obj.quants_unreserve(cr, uid, move, context=context)

            #
            #Check moves that were pushed
            if move.move_dest_id.state in ('waiting', 'confirmed'):
                other_upstream_move_ids = self.search(cr, uid, [('id','!=',move.id),('state','not in',['done','cancel']),
                                            ('move_dest_id','=',move.move_dest_id.id)], context=context)
                #If no other moves for the move that got pushed:
                if not other_upstream_move_ids and move.move_dest_id.state in ('waiting', 'confirmed'):
                    self.action_assign(cr, uid, [move.move_dest_id.id], context=context)
        self.write(cr, uid, ids, {'state': 'done', 'date': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)}, context=context)
        return True

    def unlink(self, cr, uid, ids, context=None):
        context = context or {}
        for move in self.browse(cr, uid, ids, context=context):
            if move.state not in ('draft', 'cancel'):
                raise osv.except_osv(_('User Error!'), _('You can only delete draft moves.'))
        return super(stock_move, self).unlink(cr, uid, ids, context=context)

    def action_scrap(self, cr, uid, ids, quantity, location_id, context=None):
        """ Move the scrap/damaged product into scrap location
        @param cr: the database cursor
        @param uid: the user id
        @param ids: ids of stock move object to be scrapped
        @param quantity : specify scrap qty
        @param location_id : specify scrap location
        @param context: context arguments
        @return: Scraped lines
        """
        #quantity should in MOVE UOM
        if quantity <= 0:
            raise osv.except_osv(_('Warning!'), _('Please provide a positive quantity to scrap.'))
        res = []
        for move in self.browse(cr, uid, ids, context=context):
            source_location = move.location_id
            if move.state == 'done':
                source_location = move.location_dest_id
            if source_location.usage != 'internal':
                #restrict to scrap from a virtual location because it's meaningless and it may introduce errors in stock ('creating' new products from nowhere)
                raise osv.except_osv(_('Error!'), _('Forbidden operation: it is not allowed to scrap products from a virtual location.'))
            move_qty = move.product_qty
            uos_qty = quantity / move_qty * move.product_uos_qty
            default_val = {
                'location_id': source_location.id,
                'product_qty': quantity,
                'product_uos_qty': uos_qty,
                'state': move.state,
                'scrapped': True,
                'location_dest_id': location_id,
                'tracking_id': move.tracking_id.id,
                'lot_id': move.lot_id.id,
            }
            new_move = self.copy(cr, uid, move.id, default_val)

            res += [new_move]
            product_obj = self.pool.get('product.product')
            for product in product_obj.browse(cr, uid, [move.product_id.id], context=context):
                if move.picking_id:
                    uom = product.uom_id.name if product.uom_id else ''
                    message = _("%s %s %s has been <b>moved to</b> scrap.") % (quantity, uom, product.name)
                    move.picking_id.message_post(body=message)

        self.action_done(cr, uid, res, context=context)
        return res

    def action_consume(self, cr, uid, ids, quantity, location_id=False, context=None):
        """ Consumed product with specific quatity from specific source location
        @param cr: the database cursor
        @param uid: the user id
        @param ids: ids of stock move object to be consumed
        @param quantity : specify consume quantity
        @param location_id : specify source location
        @param context: context arguments
        @return: Consumed lines
        """
        #quantity should in MOVE UOM
        if context is None:
            context = {}
        if quantity <= 0:
            raise osv.except_osv(_('Warning!'), _('Please provide proper quantity.'))
        res = []
        for move in self.browse(cr, uid, ids, context=context):
            move_qty = move.product_qty
            if move_qty <= 0:
                raise osv.except_osv(_('Error!'), _('Cannot consume a move with negative or zero quantity.'))
            quantity_rest = move.product_qty
            quantity_rest -= quantity
            uos_qty_rest = quantity_rest / move_qty * move.product_uos_qty
            if quantity_rest <= 0:
                quantity_rest = 0
                uos_qty_rest = 0
                quantity = move.product_qty

            uos_qty = quantity / move_qty * move.product_uos_qty
            if quantity_rest > 0:
                default_val = {
                    'product_qty': quantity,
                    'product_uos_qty': uos_qty,
                    'state': move.state,
                    'location_id': location_id or move.location_id.id,
                }
                current_move = self.copy(cr, uid, move.id, default_val)
                res += [current_move]
                update_val = {}
                update_val['product_qty'] = quantity_rest
                update_val['product_uos_qty'] = uos_qty_rest
                self.write(cr, uid, [move.id], update_val)

            else:
                quantity_rest = quantity
                uos_qty_rest =  uos_qty
                res += [move.id]
                update_val = {
                        'product_qty' : quantity_rest,
                        'product_uos_qty' : uos_qty_rest,
                        'location_id': location_id or move.location_id.id,
                }
                self.write(cr, uid, [move.id], update_val)

        self.action_done(cr, uid, res, context=context)
        return res

#    def price_calculation(self, cr, uid, ids, quants, context=None):
#        '''
#        This method puts the right price on the stock move,
#        adapts the price on the product when necessary
#        and creates the necessary stock move matchings
#        :param quants: are quants to be reconciled and needs to be done when IN move reconciles out move
#
#        It returns a list of tuples with (move_id, match_id)
#        which is used for generating the accounting entries when FIFO/LIFO
#        '''
#        product_obj = self.pool.get('product.product')
#        currency_obj = self.pool.get('res.currency')
#        matching_obj = self.pool.get('stock.move.matching')
#        uom_obj = self.pool.get('product.uom')
#        quant_obj = self.pool.get('stock.quant')
#
#        product_avail = {}
#        res = {}
#        for move in self.browse(cr, uid, ids, context=context):
#            # Initialize variables
#            res[move.id] = []
#            move_qty = move.product_qty
#            move_uom = move.product_uom.id
#            company_id = move.company_id.id
#            ctx = context.copy()
#            user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
#            ctx['force_company'] = move.company_id.id
#            product = product_obj.browse(cr, uid, move.product_id.id, context=ctx)
#            cost_method = product.cost_method
#            product_uom_qty = uom_obj._compute_qty(cr, uid, move_uom, move_qty, product.uom_id.id, round=False)
#            if not product.id in product_avail:
#                product_avail[product.id] = product.qty_available
#
#            # Check if out -> do stock move matchings and if fifo/lifo -> update price
#            # only update the cost price on the product form on stock moves of type == 'out' because if a valuation has to be made without PO,
#            # for inventories for example we want to use the last value used for an outgoing move
#            if move.location_id.usage == 'internal' and move.location_dest_id.usage != 'internal':
#                fifo = (cost_method != 'lifo')
#                #Ok -> do calculation based on quants
#                price_amount = 0.0
#                amount = 0.0
#                #if move.id in quants???
#                #search quants_move which are the quants associated with this move, which are not propagated quants
#                quants_move = quant_obj.search(cr, uid, [('history_ids', 'in', move.id), ('propagated_from_id', '=', False)], context=context)
#                for quant in quant_obj.browse(cr, uid, quants_move, context=context):
#                    price_amount += quant.qty * quant.price_unit
#                    amount += quant.qty
#
##                 tuples = product_obj.get_stock_matchings_fifolifo(cr, uid, [product.id], move_qty, fifo,
##                                                                   move_uom, move.company_id.currency_id.id, context=ctx) #TODO Would be better to use price_currency_id for migration?
##                 price_amount = 0.0
##                 amount = 0.0
##                 #Write stock matchings
##                 for match in tuples:
##                     matchvals = {'move_in_id': match[0], 'qty': match[1],
##                                  'move_out_id': move.id}
##                     match_id = matching_obj.create(cr, uid, matchvals, context=context)
##                     res[move.id].append(match_id)
##                     price_amount += match[1] * match[2]
##                     amount += match[1]
#                #Write price on out move
#                if product_avail[product.id] >= product_uom_qty and product.cost_method in ['real']:
#                    if amount > 0:
#                        self.write(cr, uid, move.id, {'price_unit': price_amount / move_qty}, context=context) #Should be converted
#                        product_obj.write(cr, uid, product.id, {'standard_price': price_amount / amount}, context=ctx)
#                    else:
#                        pass
##                         raise osv.except_osv(_('Error'), _("Something went wrong finding quants ")  + str(self.search(cr, uid, [('company_id','=', company_id), ('qty_remaining', '>', 0), ('state', '=', 'done'),
##                                              ('location_id.usage', '!=', 'internal'), ('location_dest_id.usage', '=', 'internal'), ('product_id', '=', product.id)],
##                                        order = 'date, id', context=context)) + str(move_qty) + str(move_uom) + str(move.company_id.currency_id.id))
#                else:
#                    new_price = uom_obj._compute_price(cr, uid, product.uom_id.id, product.standard_price, move_uom)
#                    self.write(cr, uid, move.id, {'price_unit': new_price}, context=ctx)
#                #Adjust product_avail when not average and move returned from
#                if product.cost_method != 'average':
#                    product_avail[product.id] -= product_uom_qty
#
#            #Check if in => if price 0.0, take standard price / Update price when average price and price on move != standard price
#            if move.location_id.usage != 'internal' and move.location_dest_id.usage == 'internal':
#                if move.price_unit == 0.0:
#                    new_price = uom_obj._compute_price(cr, uid, product.uom_id.id, product.standard_price, move_uom)
#                    self.write(cr, uid, move.id, {'price_unit': new_price}, context=ctx)
#                elif product.cost_method == 'average':
#                    move_product_price = uom_obj._compute_price(cr, uid, move_uom, move.price_unit, product.uom_id.id)
#                    if product_avail[product.id] > 0.0:
#                        amount_unit = product.standard_price
#                        new_std_price = ((amount_unit * product_avail[product.id])\
#                                + (move_product_price * product_uom_qty))/(product_avail[product.id] + product_uom_qty)
#                    else:
#                        new_std_price = move_product_price
#                    product_obj.write(cr, uid, [product.id], {'standard_price': new_std_price}, context=ctx)
#                # Should create the stock move matchings for previous outs for the negative stock that can be matched with is in
#                if product_avail[product.id] < 0.0: #TODO LATER
#                    resneg = self._generate_negative_stock_matchings(cr, uid, [move.id], product, quants[move.id], context=ctx)
#                    res[move.id] += resneg
#                product_avail[product.id] += product_uom_qty
#        return res

    def split(self, cr, uid, move, qty, context=None):
        """ Partially (or not) moves  a stock.move.
        @param partial_datas: Dictionary containing details of partial picking
                          like partner_id, delivery_date, delivery
                          moves with product_id, product_qty, uom
        """
        if move.product_qty==qty:
            return move
        if (move.product_qty < qty) or (qty==0):
            return False

        uom_obj = self.pool.get('product.uom')
        context = context or {}

        uom_qty = uom_obj._compute_qty(cr, uid, move.product_id.uom_id.id, qty, move.product_uom.id)
        uos_qty = uom_qty * move.product_uos_qty / move.product_uom_qty

        if move.state in ('done', 'cancel'):
            raise osv.except_osv(_('Error'), _('You cannot split a move done'))

        defaults = {
            'product_uom_qty': uom_qty,
            'product_uos_qty': uos_qty,
            'state': move.state,
            'reserved_quant_ids': []
        }
        new_move = self.copy(cr, uid, move.id, defaults)

        self.write(cr, uid, [move.id], {
            'product_uom_qty': move.product_uom_qty - uom_qty,
            'product_uos_qty': move.product_uos_qty - uos_qty,
            'reserved_quant_ids': []
        }, context=context)
        return new_move

    def get_type_from_usage(self, cr, uid, location, location_dest, context=None):
        '''
            Returns the type to be chosen based on the usages of the locations
        '''
        if location.usage == 'internal' and location_dest.usage in ['supplier', 'customer']:
            return 'out'
        if location.usage in ['supplier', 'customer'] and location_dest.usage == 'internal' :
            return 'in'
        return 'internal'

class stock_inventory(osv.osv):
    _name = "stock.inventory"
    _description = "Inventory"
    _columns = {
        'name': fields.char('Inventory Reference', size=64, required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'date': fields.datetime('Creation Date', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'date_done': fields.datetime('Date done'),
        'inventory_line_id': fields.one2many('stock.inventory.line', 'inventory_id', 'Inventories', readonly=True, states={'draft': [('readonly', False)]}),
        'move_ids': fields.many2many('stock.move', 'stock_inventory_move_rel', 'inventory_id', 'move_id', 'Created Moves'),
        'state': fields.selection( (('draft', 'Draft'), ('cancel','Cancelled'), ('confirm','Confirmed'), ('done', 'Done')), 'Status', readonly=True, select=True),
        'company_id': fields.many2one('res.company', 'Company', required=True, select=True, readonly=True, states={'draft':[('readonly',False)]}),

    }
    _defaults = {
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'state': 'draft',
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'stock.inventory', context=c)
    }

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default = default.copy()
        default.update({'move_ids': [], 'date_done': False})
        return super(stock_inventory, self).copy(cr, uid, id, default, context=context)

    def _inventory_line_hook(self, cr, uid, inventory_line, move_vals):
        """ Creates a stock move from an inventory line
        @param inventory_line:
        @param move_vals:
        @return:
        """
        return self.pool.get('stock.move').create(cr, uid, move_vals)

    def action_done(self, cr, uid, ids, context=None):
        """ Finish the inventory
        @return: True
        """
        if context is None:
            context = {}
        move_obj = self.pool.get('stock.move')
        for inv in self.browse(cr, uid, ids, context=context):
            move_obj.action_done(cr, uid, [x.id for x in inv.move_ids], context=context)
            self.write(cr, uid, [inv.id], {'state':'done', 'date_done': time.strftime('%Y-%m-%d %H:%M:%S')}, context=context)
        return True

    def action_confirm(self, cr, uid, ids, context=None):
        """ Confirm the inventory and writes its finished date
        @return: True
        """
        if context is None:
            context = {}
        # to perform the correct inventory corrections we need analyze stock location by
        # location, never recursively, so we use a special context
        product_context = dict(context, compute_child=False)

        location_obj = self.pool.get('stock.location')
        for inv in self.browse(cr, uid, ids, context=context):
            move_ids = []
            for line in inv.inventory_line_id:
                pid = line.product_id.id
                product_context.update(
                    location=line.location_id.id,
                    lot_id=line.prod_lot_id and line.prod_lot_id.id or False
                )

                qty = self.pool.get('product.product').browse(cr, uid, line.product_id.id, context=product_context).qty_available
                amount = self.pool.get('product.uom')._compute_qty_obj(cr, uid, line.product_id.uom_id, qty, line.product_uom, context=context)
                change = line.product_qty - amount
                lot_id = line.prod_lot_id.id
                if change:
                    location_id = line.product_id.property_stock_inventory.id
                    value = {
                        'name': _('INV:') + (line.inventory_id.name or ''),
                        'product_id': line.product_id.id,
                        'product_uom': line.product_uom.id,
                        'date': inv.date,
                        'company_id': line.location_id.company_id.id,
                    }

                    if change > 0:
                        value.update( {
                            'product_uom_qty': change,
                            'location_id': location_id,
                            'location_dest_id': line.location_id.id,
                        })
                    else:
                        value.update( {
                            'product_uom_qty': -change,
                            'location_id': line.location_id.id,
                            'location_dest_id': location_id,
                        })
                    move_ids.append(self._inventory_line_hook(cr, uid, line, value))
            self.write(cr, uid, [inv.id], {'state': 'confirm', 'move_ids': [(6, 0, move_ids)]})
            self.pool.get('stock.move').action_confirm(cr, uid, move_ids, context=context)
        return True

    def action_cancel_draft(self, cr, uid, ids, context=None):
        """ Cancels the stock move and change inventory state to draft.
        @return: True
        """
        for inv in self.browse(cr, uid, ids, context=context):
            self.pool.get('stock.move').action_cancel(cr, uid, [x.id for x in inv.move_ids], context=context)
            self.write(cr, uid, [inv.id], {'state':'draft'}, context=context)
        return True

    def action_cancel_inventory(self, cr, uid, ids, context=None):
        #TODO test
        self.action_cancel_draft(cr, uid, ids, context=context)


class stock_inventory_line(osv.osv):
    _name = "stock.inventory.line"
    _description = "Inventory Line"
    _rec_name = "inventory_id"
    _columns = {
        'inventory_id': fields.many2one('stock.inventory', 'Inventory', ondelete='cascade', select=True),
        'location_id': fields.many2one('stock.location', 'Location', required=True),
        'product_id': fields.many2one('product.product', 'Product', required=True, select=True),
        'product_uom': fields.many2one('product.uom', 'Product Unit of Measure', required=True),
        'product_qty': fields.float('Quantity', digits_compute=dp.get_precision('Product Unit of Measure')),
        'company_id': fields.related('inventory_id', 'company_id', type='many2one', relation='res.company', string='Company', store=True, select=True, readonly=True),
        'prod_lot_id': fields.many2one('stock.production.lot', 'Serial Number', domain="[('product_id','=',product_id)]"),
        'state': fields.related('inventory_id', 'state', type='char', string='Status', readonly=True),
    }

    def _default_stock_location(self, cr, uid, context=None):
        stock_location = self.pool.get('ir.model.data').get_object(cr, uid, 'stock', 'stock_location_stock')
        return stock_location.id

    _defaults = {
        'location_id': _default_stock_location
    }

    def on_change_product_id(self, cr, uid, ids, location_id, product, uom=False, to_date=False, context=None):
        """ Changes UoM and name if product_id changes.
        @param location_id: Location id
        @param product: Changed product_id
        @param uom: UoM product
        @return:  Dictionary of changed values
        """
        context = context or {}
        if not product:
            return {'value': {'product_qty': 0.0, 'product_uom': False}}
        context['location'] = location_id
        obj_product = self.pool.get('product.product').browse(cr, uid, product, context=context)
        uom = uom or obj_product.uom_id.id
        amount = obj_product.qty_available
        result = {'product_qty': amount, 'product_uom': uom}
        return {'value': result}


#----------------------------------------------------------
# Stock Warehouse
#----------------------------------------------------------
class stock_warehouse(osv.osv):
    _name = "stock.warehouse"
    _description = "Warehouse"
    _columns = {
        'name': fields.char('Name', size=128, required=True, select=True),
        'company_id': fields.many2one('res.company', 'Company', required=True, select=True),
        'partner_id': fields.many2one('res.partner', 'Owner Address'),
        'lot_input_id': fields.many2one('stock.location', 'Location Input', required=True, domain=[('usage', '<>', 'view')]),
        'lot_stock_id': fields.many2one('stock.location', 'Location Stock', required=True, domain=[('usage', '=', 'internal')]),
        'lot_output_id': fields.many2one('stock.location', 'Location Output', required=True, domain=[('usage', '<>', 'view')]),
    }

    def _default_lot_input_stock_id(self, cr, uid, context=None):
        lot_input_stock = self.pool.get('ir.model.data').get_object(cr, uid, 'stock', 'stock_location_stock')
        return lot_input_stock.id

    def _default_lot_output_id(self, cr, uid, context=None):
        lot_output = self.pool.get('ir.model.data').get_object(cr, uid, 'stock', 'stock_location_output')
        return lot_output.id

    _defaults = {
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'stock.inventory', context=c),
        'lot_input_id': _default_lot_input_stock_id,
        'lot_stock_id': _default_lot_input_stock_id,
        'lot_output_id': _default_lot_output_id,
    }


# -------------------------
# Packaging related stuff
# -------------------------

from openerp.report import report_sxw
report_sxw.report_sxw('report.stock.quant.package.barcode', 'stock.quant.package', 'addons/stock/report/picking_barcode.rml')

class stock_package(osv.osv):
    """
    These are the packages, containing quants and/or others packages
    """
    _name = "stock.quant.package"
    _description = "Physical Packages"
    _order = 'name'

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
            if quant.package_id:
                res.add(quant.package_id.id)
        return list(res)

    def _get_packages_to_relocate(self, cr, uid, ids, context=None):
        res = set()
        for pack in self.browse(cr, uid, ids, context=context):
            res.add(pack.id)
            if pack.parent_id:
                res.add(pack.parent_id.id)
        return list(res)

    def _get_package_info(self, cr, uid, ids, name, args, context=None):
        default_company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        res = {}.fromkeys(ids, {'location_id': False, 'company_id': default_company_id})
        for pack in self.browse(cr, uid, ids, context=context):
            if pack.quant_ids:
                res[pack.id]['location_id'] = pack.quant_ids[0].location_id.id
                res[pack.id]['company_id'] = pack.quant_ids[0].company_id.id
            elif pack.children_ids:
                res[pack.id]['location_id'] = pack.children_ids[0].location_id.id
                res[pack.id]['company_id'] = pack.children_ids[0].company_id.id
        return res

    _columns = {
        'name': fields.char('Package Reference', size=64, select=True),
        'complete_name': fields.function(_complete_name, type='char', string="Package Name",),
        'parent_left': fields.integer('Left Parent', select=1),
        'parent_right': fields.integer('Right Parent', select=1),
        'packaging_id': fields.many2one('product.packaging', 'Type of Packaging'),
        'location_id': fields.function(_get_package_info, type='many2one', relation='stock.location', string='Location', multi="package",
                                    store={
                                       'stock.quant': (_get_packages, ['location_id'], 10),
                                       'stock.quant.package': (_get_packages_to_relocate, ['children_ids', 'quant_ids', 'parent_id'], 10),
                                    }, readonly=True),
        'quant_ids': fields.one2many('stock.quant', 'package_id', 'Bulk Content'),
        'parent_id': fields.many2one('stock.quant.package', 'Parent Package', help="The package containing this item"),
        'children_ids': fields.one2many('stock.quant.package', 'parent_id', 'Contained Packages'),
        'company_id': fields.function(_get_package_info, type="many2one", relation='res.company', string='Company', multi="package"),
    }
    _defaults = {
        'name': lambda self, cr, uid, context: self.pool.get('ir.sequence').get(cr, uid, 'stock.quant.package') or _('Unknown Pack')
    }
    def _check_location(self, cr, uid, ids, context=None):
        '''checks that all quants in a package are stored in the same location'''
        quant_obj = self.pool.get('stock.quant')
        for pack in self.browse(cr, uid, ids, context=context):
            parent = pack
            while parent.parent_id:
                parent = parent.parent_id
            quant_ids = self.get_content(cr, uid, [parent.id], context=context)
            quants = quant_obj.browse(cr, uid, quant_ids, context=context)
            location_id = quants and quants[0].location_id.id or False
            if not all([quant.location_id.id == location_id for quant in quants]):
                return False
        return True

    _constraints = [
        (_check_location, 'Everything inside a package should be in the same location', ['location_id']),
    ]

    def action_print(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        datas = {
            'ids': context.get('active_id') and [context.get('active_id')] or ids,
            'model': 'stock.quant.package',
            'form': self.read(cr, uid, ids)[0]
        }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'stock.quant.package.barcode',
            'datas': datas
        }

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


class stock_pack_operation(osv.osv):
    _name = "stock.pack.operation"
    _description = "Packing Operation"
    _columns = {
        'picking_id': fields.many2one('stock.picking', 'Stock Picking', help='The stock operation where the packing has been made', required=True),
        'product_id': fields.many2one('product.product', 'Product', ondelete="CASCADE"),  # 1
        'product_uom_id': fields.many2one('product.uom', 'Product Unit of Measure'),
        'product_qty': fields.float('Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), required=True),
        'package_id': fields.many2one('stock.quant.package', 'Package'),  # 2
        'quant_id': fields.many2one('stock.quant', 'Quant'),  # 3
        'result_package_id': fields.many2one('stock.quant.package', 'Container Package', help="If set, the operations are packed into this package", required=False, ondelete='cascade'),
        'date': fields.datetime('Date', required=True),
        #'lot_id': fields.many2one('stock.production.lot', 'Serial Number', ondelete='CASCADE'),
        #'update_cost': fields.boolean('Need cost update'),
        'cost': fields.float("Cost", help="Unit Cost for this product line"),
        'currency': fields.many2one('res.currency', string="Currency", help="Currency in which Unit cost is expressed", ondelete='CASCADE'),
    }

    _defaults = {
        'date': fields.date.context_today,
    }

    def _find_product_ids(self, cr, uid, operation_id, context=None):
        quant_obj = self.pool.get('stock.quant')
        operation = self.browse(cr, uid, operation_id, context=context)
        if operation.product_id:
            return [operation.product_id.id]
        elif operation.quant_id:
            return [operation.quant_id.product_id.id]
        elif operation.package_id:
            included_package_ids = self.pool.get('stock.quant.package').search(cr, uid, [('parent_id', 'child_of', [operation.package_id.id])], context=context)
            included_quant_ids = quant_obj.search(cr, uid, [('package_id', 'in', included_package_ids)], context=context)
            return [quant.product_id.id for quant in quant_obj.browse(cr, uid, included_quant_ids, context=context)]

    #TODO: this function can be refactored
    def _search_and_increment(self, cr, uid, picking_id, key, context=None):
        '''Search for an operation on an existing key in a picking, if it exists increment the qty (+1) otherwise create it

        :param key: tuple directly reusable in a domain
        context can receive a key 'current_package_id' with the package to consider for this operation
        returns True

        previously: returns the update to do in stock.move one2many field of picking (adapt remaining quantities) and to the list of package in the classic one2many syntax
                 (0, 0,  { values })    link to a new record that needs to be created with the given values dictionary
                 (1, ID, { values })    update the linked record with id = ID (write *values* on it)
                 (2, ID)                remove and delete the linked record with id = ID (calls unlink on ID, that will delete the object completely, and the link to it as well)
        '''
        quant_obj = self.pool.get('stock.quant')
        if context is None:
            context = {}

        #if current_package_id is given in the context, we increase the number of items in this package
        package_clause = [('result_package_id', '=', context.get('current_package_id', False))]
        existing_operation_ids = self.search(cr, uid, [('picking_id', '=', picking_id), key] + package_clause, context=context)
        if existing_operation_ids:
            #existing operation found for the given key and picking => increment its quantity
            operation_id = existing_operation_ids[0]
            qty = self.browse(cr, uid, operation_id, context=context).product_qty + 1
            self.write(cr, uid, operation_id, {'product_qty': qty}, context=context)
        else:
            #no existing operation found for the given key and picking => create a new one
            var_name, dummy, value = key
            uom_id = False
            if var_name == 'product_id':
                uom_id = self.pool.get('product.product').browse(cr, uid, value, context=context).uom_id.id
            elif var_name == 'quant_id':
                quant = quant_obj.browse(cr, uid, value, context=context)
                uom_id = quant.product_id.uom_id.id
            values = {
                'picking_id': picking_id,
                var_name: value,
                'product_qty': 1,
                'product_uom_id': uom_id,
            }
            operation_id = self.create(cr, uid, values, context=context)
            values.update({'id': operation_id})
        return True

class stock_warehouse_orderpoint(osv.osv):
    """
    Defines Minimum stock rules.
    """
    _name = "stock.warehouse.orderpoint"
    _description = "Minimum Inventory Rule"

    def _get_draft_procurements(self, cr, uid, ids, field_name, arg, context=None):
        if context is None:
            context = {}
        result = {}
        procurement_obj = self.pool.get('procurement.order')
        for orderpoint in self.browse(cr, uid, ids, context=context):
            procurement_ids = procurement_obj.search(cr, uid, [('state', '=', 'draft'), ('product_id', '=', orderpoint.product_id.id), ('location_id', '=', orderpoint.location_id.id)])
            result[orderpoint.id] = procurement_ids
        return result

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
        'name': fields.char('Name', size=32, required=True),
        'active': fields.boolean('Active', help="If the active field is set to False, it will allow you to hide the orderpoint without removing it."),
        'logic': fields.selection([('max', 'Order to Max'), ('price', 'Best price (not yet active!)')], 'Reordering Mode', required=True),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse', required=True, ondelete="cascade"),
        'location_id': fields.many2one('stock.location', 'Location', required=True, ondelete="cascade"),
        'product_id': fields.many2one('product.product', 'Product', required=True, ondelete='cascade', domain=[('type', '!=', 'service')]),
        'product_uom': fields.many2one('product.uom', 'Product Unit of Measure', required=True),
        'product_min_qty': fields.float('Minimum Quantity', required=True,
            help="When the virtual stock goes below the Min Quantity specified for this field, OpenERP generates "\
            "a procurement to bring the forecasted quantity to the Max Quantity."),
        'product_max_qty': fields.float('Maximum Quantity', required=True,
            help="When the virtual stock goes below the Min Quantity, OpenERP generates "\
            "a procurement to bring the forecasted quantity to the Quantity specified as Max Quantity."),
        'qty_multiple': fields.integer('Qty Multiple', required=True,
            help="The procurement quantity will be rounded up to this multiple."),
        'procurement_id': fields.many2one('procurement.order', 'Latest procurement', ondelete="set null"),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'procurement_draft_ids': fields.function(_get_draft_procurements, type='many2many', relation="procurement.order", \
                                string="Related Procurement Orders", help="Draft procurement of the product and location of that orderpoint"),
    }
    _defaults = {
        'active': lambda *a: 1,
        'logic': lambda *a: 'max',
        'qty_multiple': lambda *a: 1,
        'name': lambda self, cr, uid, context: self.pool.get('ir.sequence').get(cr, uid, 'stock.orderpoint') or '',
        'product_uom': lambda self, cr, uid, context: context.get('product_uom', False),
        'company_id': lambda self, cr, uid, context: self.pool.get('res.company')._company_default_get(cr, uid, 'stock.warehouse.orderpoint', context=context)
    }
    _sql_constraints = [
        ('qty_multiple_check', 'CHECK( qty_multiple > 0 )', 'Qty Multiple must be greater than zero.'),
    ]
    _constraints = [
        (_check_product_uom, 'You have to select a product unit of measure in the same category than the default unit of measure of the product', ['product_id', 'product_uom']),
    ]

    def default_get(self, cr, uid, fields, context=None):
        res = super(stock_warehouse_orderpoint, self).default_get(cr, uid, fields, context)
        # default 'warehouse_id' and 'location_id'
        if 'warehouse_id' not in res:
            warehouse = self.pool.get('ir.model.data').get_object(cr, uid, 'stock', 'warehouse0', context)
            res['warehouse_id'] = warehouse.id
        if 'location_id' not in res:
            warehouse = self.pool.get('stock.warehouse').browse(cr, uid, res['warehouse_id'], context)
            res['location_id'] = warehouse.lot_stock_id.id
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

    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        default.update({
            'name': self.pool.get('ir.sequence').get(cr, uid, 'stock.orderpoint') or '',
        })
        return super(stock_warehouse_orderpoint, self).copy(cr, uid, id, default, context=context)

class product_template(osv.osv):
    _inherit = "product.template"
    _columns = {
        'type': fields.selection([('product', 'Stockable Product'), ('consu', 'Consumable'), ('service', 'Service')], 'Product Type', required=True, help="Consumable: Will not imply stock management for this product. \nStockable product: Will imply stock management for this product."),
        'supply_method': fields.selection([('produce', 'Manufacture'), ('buy', 'Buy'), ('wait', 'None')], 'Supply Method', required=True, help="Manufacture: When procuring the product, a manufacturing order or a task will be generated, depending on the product type. \nBuy: When procuring the product, a purchase order will be generated."),
    }
    _defaults = {
        'supply_method': 'buy',
    }

class product_product(osv.osv):
    _inherit = "product.product"
    _columns = {
        'orderpoint_ids': fields.one2many('stock.warehouse.orderpoint', 'product_id', 'Minimum Stock Rules'),
    }

class stock_picking_code(osv.osv):
    _name = "stock.picking.code"
    _description = "Will group picking types for kanban view"
    _columns = {
        'name': fields.char("Picking Type", translate=True),
    }

class stock_picking_type(osv.osv):
    _name = "stock.picking.type"
    _description = "The picking type determines the picking view"

    def __get_bar_values(self, cr, uid, obj, domain, read_fields, value_field, groupby_field, context=None):
        """ Generic method to generate data for bar chart values using SparklineBarWidget.
            This method performs obj.read_group(cr, uid, domain, read_fields, groupby_field).

            :param obj: the target model (i.e. crm_lead)
            :param domain: the domain applied to the read_group
            :param list read_fields: the list of fields to read in the read_group
            :param str value_field: the field used to compute the value of the bar slice
            :param str groupby_field: the fields used to group

            :return list section_result: a list of dicts: [
                                                {   'value': (int) bar_column_value,
                                                    'tootip': (str) bar_column_tooltip,
                                                }
                                            ]
        """
        month_begin = date.today().replace(day=1)
        section_result = [{
                            'value': 0,
                            'tooltip': (month_begin + relativedelta.relativedelta(months=-i)).strftime('%B'),
                            } for i in range(10, -1, -1)]
        group_obj = obj.read_group(cr, uid, domain, read_fields, groupby_field, context=context)
        for group in group_obj:
            group_begin_date = datetime.strptime(group['__domain'][0][2], tools.DEFAULT_SERVER_DATE_FORMAT)
            month_delta = relativedelta.relativedelta(month_begin, group_begin_date)
            section_result[10 - (month_delta.months + 1)] = {'value': group.get(value_field, 0), 'tooltip': group_begin_date.strftime('%B')}
        return section_result

    def _get_picking_data(self, cr, uid, ids, field_name, arg, context=None):
        obj = self.pool.get('stock.picking')
        res = dict.fromkeys(ids, False)
        month_begin = date.today().replace(day=1)
        groupby_begin = (month_begin + relativedelta.relativedelta(months=-4)).strftime(tools.DEFAULT_SERVER_DATE_FORMAT)
        groupby_end = (month_begin + relativedelta.relativedelta(months=3)).strftime(tools.DEFAULT_SERVER_DATE_FORMAT)
        for id in ids:
            created_domain = [
                ('picking_type_id', '=', id),
                ('state', 'not in', ['draft', 'cancel']),
                ('date', '>=', groupby_begin),
                ('date', '<', groupby_end),
            ]
            res[id] = self.__get_bar_values(cr, uid, obj, created_domain, ['date'], 'picking_type_id_count', 'date', context=context)
        return res

    def _get_picking_count(self, cr, uid, ids, field_names, arg, context=None):
        obj = self.pool.get('stock.picking')
        domains = {
            'count_picking_waiting': [('state','=','confirmed')],
            'count_picking': [('state','=','assigned')],
            'count_picking_late': [('min_date','<', time.strftime('%Y-%m-%d %H:%M:%S'))],
            'count_picking_backorders': [('backorder_id','<>', False)],
        }
        result = {}
        for field in domains:
            data = obj.read_group(cr, uid, domains[field] +
                [('state', 'not in',('done','cancel','draft')), ('picking_type_id', 'in', ids)],
                ['picking_type_id'], ['picking_type_id'], context=context)
            count = dict(map(lambda x: (x['picking_type_id'] and x['picking_type_id'][0], x['picking_type_id_count']), data))
            for tid in ids:
                result.setdefault(tid, {})[field] = count.get(tid, 0)
        for tid in ids:
            if result[tid]['count_picking']:
                result[tid]['rate_picking_late'] = result[tid]['count_picking_late'] *100 / result[tid]['count_picking']
                result[tid]['rate_picking_backorders'] = result[tid]['count_picking_backorders'] *100 / result[tid]['count_picking']
            else:
                result[tid]['rate_picking_late'] = 0
                result[tid]['rate_picking_backorders'] = 0
        return result

    def _get_picking_history(self, cr, uid, ids, field_names, arg, context=None):
        obj = self.pool.get('stock.picking')
        result = {}
        for id in ids:
            result[id] = {
                'latest_picking_late': [],
                'latest_picking_backorders': []
            }
        for type_id in ids:
            pick_ids = obj.search(cr, uid, [('state', '=','done'), ('picking_type_id','=',type_id)], limit=12, order="date desc", context=context)
            for pick in obj.browse(cr, uid, pick_ids, context=context):
                result[type_id]['latest_picking_late'] = cmp(pick.date[:10], time.strftime('%Y-%m-%d'))
                result[type_id]['latest_picking_backorders'] = bool(pick.backorder_id)
        return result

    _columns = {
        'name': fields.char('name', translate=True),
        'pack': fields.boolean('Pack', 'This picking type needs packing interface'),
        'color': fields.integer('Color Index'),
        'delivery': fields.boolean('Print delivery'),
        'sequence_id': fields.many2one('ir.sequence', 'Sequence', required = True),
        'default_location_src_id': fields.many2one('stock.location', 'Default Source Location'),
        'default_location_dest_id': fields.many2one('stock.location', 'Default Destination Location'),
        'code_id': fields.many2one('stock.picking.code', 'Picking type code', required = True),

        # Statistics for the kanban view
        'weekly_picking': fields.function(_get_picking_data,
            type='string',
            string='Scheduled pickings per week'),

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

        'latest_picking_late': fields.function(_get_picking_history,
            type='string', multi='_get_picking_history'),
        'latest_picking_backorders': fields.function(_get_picking_history,
            type='string', multi='_get_picking_history'),

    }



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
