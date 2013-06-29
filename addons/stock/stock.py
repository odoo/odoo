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

from datetime import datetime
from dateutil.relativedelta import relativedelta
import time
from operator import itemgetter
from itertools import groupby

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import netsvc
from openerp import tools
from openerp.tools import float_compare, DEFAULT_SERVER_DATETIME_FORMAT
import openerp.addons.decimal_precision as dp
import logging
_logger = logging.getLogger(__name__)

#----------------------------------------------------------
# Incoterms
#----------------------------------------------------------
class stock_incoterms(osv.osv):
    _name = "stock.incoterms"
    _description = "Incoterms"
    _columns = {
        'name': fields.char('Name', size=64, required=True, help="Incoterms are series of sales terms.They are used to divide transaction costs and responsibilities between buyer and seller and reflect state-of-the-art transportation practices."),
        'code': fields.char('Code', size=3, required=True, help="Code for Incoterms"),
        'active': fields.boolean('Active', help="By unchecking the active field, you may hide an INCOTERM without deleting it."),
    }
    _defaults = {
        'active': True,
    }

class stock_journal(osv.osv):
    _name = "stock.journal"
    _description = "Inventory Journal"
    _columns = {
        'name': fields.char('Stock Journal', size=32, required=True),
        'user_id': fields.many2one('res.users', 'Responsible'),
    }
    _defaults = {
        'user_id': lambda s, c, u, ctx: u
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

        'complete_name': fields.function(_complete_name, type='char', size=256, string="Location Name",
                            store={'stock.location': (_get_sublocations, ['name', 'location_id'], 10)}),

        'location_id': fields.many2one('stock.location', 'Parent Location', select=True, ondelete='cascade'),
        'child_ids': fields.one2many('stock.location', 'location_id', 'Contains'),

        'partner_id': fields.many2one('res.partner', 'Owner',help="Owner of the location if not internal"),

        'comment': fields.text('Additional Information'),
        'posx': fields.integer('Corridor (X)',help="Optional localization details, for information purpose only"),
        'posy': fields.integer('Shelves (Y)', help="Optional localization details, for information purpose only"),
        'posz': fields.integer('Height (Z)', help="Optional localization details, for information purpose only"),

        'parent_left': fields.integer('Left Parent', select=1),
        'parent_right': fields.integer('Right Parent', select=1),

        'company_id': fields.many2one('res.company', 'Company', select=1, help='Let this field empty if this location is shared between all companies'),
        'scrap_location': fields.boolean('Scrap Location', help='Check this box to allow using this location to put scrapped/damaged goods.'),
        'valuation_in_account_id': fields.many2one('account.account', 'Stock Valuation Account (Incoming)', domain = [('type','=','other')],
                                                   help="Used for real-time inventory valuation. When set on a virtual location (non internal type), "
                                                        "this account will be used to hold the value of products being moved from an internal location "
                                                        "into this location, instead of the generic Stock Output Account set on the product. "
                                                        "This has no effect for internal locations."),
        'valuation_out_account_id': fields.many2one('account.account', 'Stock Valuation Account (Outgoing)', domain = [('type','=','other')],
                                                   help="Used for real-time inventory valuation. When set on a virtual location (non internal type), "
                                                        "this account will be used to hold the value of products being moved out of this location "
                                                        "and into an internal location, instead of the generic Stock Output Account set on the product. "
                                                        "This has no effect for internal locations."),
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
    def get_removal_strategy(self, cr, uid, id, product_id, context=None):
        product = self.pool.get("product.product").browse(cr, uid, product_id, context=context)
        categ = product.categ_id
        while (not categ.removal_strategy_id) and categ.parent_id:
            categ = categ.parent_id
        return categ.removal_strategy_id or None

class stock_quant(osv.osv):
    """
    Quants are the smallest unit of stock physical instances
    """
    _name = "stock.quant"
    _description = "Quants"
    _columns = {
        'name': fields.char('Identifier', help='serial... '),  # TODO improve me
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'location_id': fields.many2one('stock.location', 'Location', required=True),
        'qty': fields.float('Quantity', required=True, help="Quantity of products in this quant, in the default unit of measure of the product"),
        'package_id': fields.many2one('stock.quant.package', help="The package containing this quant"), 
        'reservation_id': fields.many2one('stock.move', 'Reserved for Move', help="Is this quant reserved for a stock.move?"), 
        'prodlot_id': fields.many2one('stock.production.lot', 'Lot'), 
        'cost': fields.float('Unit Cost'), 

        'create_date': fields.datetime('Creation Date'), 
        'in_date': fields.datetime('Incoming Date'), 

        'history_ids': fields.many2many('stock.move', 'stock_quant_move_rel', 'quant_id', 'move_id', 'Moves', help='Moves that operate(d) on this quant'),
        'company_id': fields.many2one('res.company', 'Company', help="The company to which the quants belong"),

        # Used for negative quants to reconcile after compensated by a new positive one
        'propagated_from_id': fields.many2one('stock.quant', 'Linked Quant', help = 'The negative quant this is coming from'), 
        'propagated_to_ids': fields.one2many('stock.quant', 'propagated_from_id', 'Linked Quants', help = 'The negative quant this is coming from'), 
    }

    def quants_reserve(self, cr, uid, quants, move_id, context=None):
        toreserve = []
        for quant,qty in quants:
            if not quant: continue
            self._quant_split(cr, uid, quant, qty, context=context)
            toreserve.append(quant.id)
        return self.write(cr, uid, toreserve, {'reservation_id': move.id}, context=context)

    def quants_move(self, cr, uid, quants, move_id, context=None):
        for quant,qty in quants:
            if not quant:
                quant = self._quant_create(cr, uid, qty, move_id, context=context)
            else:
                self._quant_split(cr, uid, quant, qty, context=context)
            self._quant_reconcile_negative(cr, uid, quant, context=context)
            self.write(cr, uid, [quant.id], {
                'location_id': move.location_dest_id.id,
                'reservation_id': move.move_dest_id and move.move_dest_id.id or False, 
                'history_ids': [(4, move.id)]
            })

    # FP Note: TODO: implement domain preference that tries to retrieve first with this domain
    def quants_get(self, cr, uid, location_id, product_id, qty, domain=[('qty','>',0.0)], domain_preference=[], context=None):
        """
        Use the removal strategies of product to search for the correct quants

        :location_id: child_of this location_id
        :product_id: id of product
        :qty in UoM of product
        :prodlot_id NOT USED YET !
        """
        removal_strategy = self.pool.get('stock.location').get_removal_strategy(cr, uid, location_id, product_id, context=context) or 'fifo'
        if removal_strategy=='fifo':
            result = self._quants_get_fifo(cr, uid, location_id, product_id, qty, domain, context=context)
        elif removal_strategy=='lifo':
            result = self._quants_get_lifo(cr, uid, location_id, product_id, qty, domain, context=context)
        else:
            raise osv.except_osv(_('Error!'),_('Removal strategy %s not implemented.' % (removal_strategy,)))
        return result


    #
    # Create a quant in the destination location
    # Create a negative quant in the source location if it's an internal location
    # Reconcile a positive quant with a negative is possible
    # 
    def _quant_create(self, cr, uid, qty, move, context=None):
        vals = {
            'product_id': move.product_id.id, 
            'location_id': move.location_dest_id.id, 
            'qty': product_uom_qty, 
            'history_ids': [(4, move.id)], 
            'in_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'prodlot_id': move.prodlot_id.id, 
            'company_id': move.company_id.id, 
        }
        quant_id = self.create(cr, uid, vals, context=context)
        if move.location_id.type == 'internal':
            vals['location_id'] = move.location_id.id
            vals['qty'] = -product_uom_qty
            new_quant_id = self.create(cr, uid, vals, context=context)
            self.write(cr, uid, [quant_id], {'propagated_from_id': new_quant_id}, context=context)
        obj = self.browse(cr, uid, quant_id, context=context)
        self._price_update(cr, uid, obj, product_uom_price, context=context)
        return obj

    def _quand_split(self, cr, uid, quant, qty, context=None):
        context=context or {}
        if quant.qty<=qty:
            return False
        new_quant = self.copy(cr, uid, quant.id, default={'qty': quant.qty-qty}, context=context)
        self.write(cr, uid, quant.id, {'qty': qty}, context=context)
        quant.refresh()
        return new_quant

    def _quant_reconcile_negative(self, cr, uid, quant, context=None):
        '''
        This function will reconcile the negative quants with the amount provided and give them this price
        :param ids : Negative quants to reconcile with
        :param move
        :param qty: in product uom as incoming quantity or as quantity from the quant to be reconciled
        :param price: in product uom as price to be put on propagated quants 
        :param history_moves_to_transfer: when moving, we need to pass the history_ids of the quant that will be cancelled with the negative quant (list of browse records)
        :return: amount that stays open + propagated quants from the reconciled quants which get a price, ... now
        '''
        if quant.location_id <> 'internal': return False
        quants = self.quants_get(cr, uid, quant.location_id, quant.product_id.id, quant.qty, [('qty','<','0')], context=context)
        for quant, qty in quants:
            if not quant: continue

            # FP Note: to implement
            #self.split(...)
            #self.write(cr, uid, quant.id, {
            #    'propagated_from_id': False,
            #    'history_ids': [(4, x.id) for x in history_moves_to_transfer]}, context=context)
            #self.unlink(cr, uid, [quant.id], context=context)
            #self._price_update(cr, uid, quant.id, quant.price)
            #     ''cost': price,

        return res

    # FP Note: this is where we should post accounting entries
    def _price_update(cr, uid, quant, newprice, context=None):
        self.write(cr, uid, [quant.id], {'price': newprice}, context=context)

    #
    # Implementation of removal strategies
    #
    def _quants_get_order(self, cr, uid, location_id, product_id, quantity, domain=[], orderby='in_date', context=None):
        domain = [('location_id', 'child_of', location_id), ('product_id','=',product_id), 
                  ('reservation_id', '=', False)] + domain
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
                else:
                    res += [(quant, quantity)]
                    quantity = 0
            offset += 10
        return res

    def _quants_get_fifo(self, cr, uid, location_id, product_id, quantity, domain=[], context=None):
        return self._quants_get_order(cr, uid, location_id, product_id, quantity,
            domain, 'in_date', context=context)

    def _quants_get_lifo(self, cr, uid, location_id, product_id, quantity, domain=[], context=None):
        return self._quants_get_order(cr, uid, location_id, product_id, quantity,
            domain, 'in_date desc', context=context)


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
        if ('name' not in vals) or (vals.get('name') in ('/', False)):
            vals['name'] = self.pool.get('ir.sequence').get(cr, user, self._name)
        return super(stock_picking, self).create(cr, user, vals, context)

    _columns = {
        'name': fields.char('Reference', size=64, select=True, states={'done':[('readonly', True)], 'cancel':[('readonly',True)]}),
        'origin': fields.char('Source Document', size=64, states={'done':[('readonly', True)], 'cancel':[('readonly',True)]}, help="Reference of the document", select=True),
        'backorder_id': fields.many2one('stock.picking', 'Back Order of', states={'done':[('readonly', True)], 'cancel':[('readonly',True)]}, help="If this shipment was split, then this field links to the shipment which contains the already processed part.", select=True),
        'type': fields.selection([('out', 'Sending Goods'), ('in', 'Getting Goods'), ('internal', 'Internal')], 'Shipping Type', required=True, select=True, help="Shipping type specify, goods coming in or going out."),
        'note': fields.text('Notes', states={'done':[('readonly', True)], 'cancel':[('readonly',True)]}),
        'stock_journal_id': fields.many2one('stock.journal','Stock Journal', select=True, states={'done':[('readonly', True)], 'cancel':[('readonly',True)]}),
        'move_type': fields.selection([('direct', 'Partial'), ('one', 'All at once')], 'Delivery Method', required=True, states={'done':[('readonly', True)], 'cancel':[('readonly',True)]}, help="It specifies goods to be deliver partially or all at once"),
        'state': fields.selection([
            ('draft', 'Draft'),
            ('cancel', 'Cancelled'),
            ('auto', 'Waiting Another Operation'),
            ('confirmed', 'Waiting Availability'),
            ('assigned', 'Ready to Transfer'),
            ('done', 'Transferred'),
            ], 'Status', readonly=True, select=True, track_visibility='onchange', help="""
            * Draft: not confirmed yet and will not be scheduled until confirmed\n
            * Waiting Another Operation: waiting for another move to proceed before it becomes automatically available (e.g. in Make-To-Order flows)\n
            * Waiting Availability: still waiting for the availability of products\n
            * Ready to Transfer: products reserved, simply waiting for confirmation.\n
            * Transferred: has been processed, can't be modified or cancelled anymore\n
            * Cancelled: has been cancelled, can't be confirmed anymore"""
        ),
        'min_date': fields.function(get_min_max_date, multi="min_max_date",
                 store=True, type='datetime', string='Scheduled Time', select=1, help="Scheduled time for the shipment to be processed"),
        'date': fields.datetime('Creation Date', help="Creation date, usually the time of the order.", select=True, states={'done':[('readonly', True)], 'cancel':[('readonly',True)]}),
        'date_done': fields.datetime('Date of Transfer', help="Date of Completion", states={'done':[('readonly', True)], 'cancel':[('readonly',True)]}),
        'max_date': fields.function(get_min_max_date, multi="min_max_date",
                 store=True, type='datetime', string='Max. Expected Date', select=2),
        'move_lines': fields.one2many('stock.move', 'picking_id', 'Internal Moves', states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}),
        'auto_picking': fields.boolean('Auto-Picking', states={'done':[('readonly', True)], 'cancel':[('readonly',True)]}),
        'partner_id': fields.many2one('res.partner', 'Partner', states={'done':[('readonly', True)], 'cancel':[('readonly',True)]}),
        'invoice_state': fields.selection([
            ("invoiced", "Invoiced"),
            ("2binvoiced", "To Be Invoiced"),
            ("none", "Not Applicable")], "Invoice Control",
            select=True, required=True, readonly=True, track_visibility='onchange', states={'draft': [('readonly', False)]}),
        'company_id': fields.many2one('res.company', 'Company', required=True, select=True, states={'done':[('readonly', True)], 'cancel':[('readonly',True)]}),
        'pack_operation_ids': fields.one2many('stock.pack.operation', 'picking_id', string='Related Packing Operations'),

        # Used to search a product on pickings
        'product_id': fields.related('move_lines', 'product_id', type='many2one', relation='product.product', string='Product'),
    }
    _defaults = {
        'name': lambda self, cr, uid, context: '/',
        'state': 'draft',
        'move_type': 'direct',
        'type': 'internal',
        'invoice_state': 'none',
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'stock.picking', context=c)
    }
    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)', 'Reference must be unique per Company!'),
    ]
    def action_process(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        """Open the partial picking wizard"""
        context.update({
            'active_model': self._name,
            'active_ids': ids,
            'active_id': len(ids) and ids[0] or False
        })
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.partial.picking',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context,
            'nodestroy': True,
        }

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
        if 'invoice_state' not in default and picking_obj.invoice_state == 'invoiced':
            default['invoice_state'] = '2binvoiced'
        return super(stock_picking, self).copy(cr, uid, id, default, context)

    def fields_view_get(self, cr, uid, view_id=None, view_type=False, context=None, toolbar=False, submenu=False):
        if view_type == 'form' and not view_id:
            mod_obj = self.pool.get('ir.model.data')
            if self._name == "stock.picking.in":
                model, view_id = mod_obj.get_object_reference(cr, uid, 'stock', 'view_picking_in_form')
            if self._name == "stock.picking.out":
                model, view_id = mod_obj.get_object_reference(cr, uid, 'stock', 'view_picking_out_form')
        return super(stock_picking, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)

    def action_confirm(self, cr, uid, ids, context=None):
        """ Confirms picking.
        @return: True
        """
        self.write(cr, uid, ids, {'state': 'confirmed'})
        pickings = self.browse(cr, uid, ids, context=context)
        todo = []
        for picking in pickings:
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
                self.signal_button_confirm(cr, uid, [pick.id])
            move_ids = [x.id for x in pick.move_lines if x.state == 'confirmed']
            if not move_ids:
                raise osv.except_osv(_('Warning!'),_('Not enough stock, unable to reserve the products.'))
            self.pool.get('stock.move').action_assign(cr, uid, move_ids)
        return True

    def force_assign(self, cr, uid, ids, *args):
        """ Changes state of picking to available if moves are confirmed or waiting.
        @return: True
        """
        wf_service = netsvc.LocalService("workflow")
        for pick in self.browse(cr, uid, ids):
            move_ids = [x.id for x in pick.move_lines if x.state in ['confirmed','waiting']]
            self.pool.get('stock.move').force_assign(cr, uid, move_ids)
            wf_service.trg_write(uid, 'stock.picking', pick.id, cr)
        return True

    def draft_force_assign(self, cr, uid, ids, *args):
        """ Confirms picking directly from draft state.
        @return: True
        """
        return self.signal_button_confirm(cr, uid, ids)

    def draft_validate(self, cr, uid, ids, context=None):
        """ Validates picking directly from draft state.
        @return: True
        """
        wf_service = netsvc.LocalService("workflow")
        self.draft_force_assign(cr, uid, ids)
        return self.action_process(cr, uid, ids, context=context)

    def cancel_assign(self, cr, uid, ids, *args):
        """ Cancels picking and moves.
        @return: True
        """
        wf_service = netsvc.LocalService("workflow")
        for pick in self.browse(cr, uid, ids):
            move_ids = [x.id for x in pick.move_lines]
            self.pool.get('stock.move').cancel_assign(cr, uid, move_ids)
            wf_service.trg_write(uid, 'stock.picking', pick.id, cr)
        return True

    def action_assign_wkf(self, cr, uid, ids, context=None):
        """ Changes picking state to assigned.
        @return: True
        """
        self.write(cr, uid, ids, {'state': 'assigned'})
        return True

    def test_finished(self, cr, uid, ids):
        """ Tests whether the move is in done or cancel state or not.
        @return: True or False
        """
        move_ids = self.pool.get('stock.move').search(cr, uid, [('picking_id', 'in', ids)])
        for move in self.pool.get('stock.move').browse(cr, uid, move_ids):
            if move.state not in ('done', 'cancel'):
                return False
        return True

    def test_assigned(self, cr, uid, ids):
        """ Tests whether the move is in assigned state or not.
        @return: True or False
        """
        #TOFIX: assignment of move lines should be call before testing assigment otherwise picking never gone in assign state
        ok = True
        for pick in self.browse(cr, uid, ids):
            mt = pick.move_type
            # incomming shipments are always set as available if they aren't chained
            if pick.type == 'in':
                if all([x.state != 'waiting' for x in pick.move_lines]):
                    return True
            for move in pick.move_lines:
                if (move.state in ('confirmed', 'draft')) and (mt == 'one'):
                    return False
                if (mt == 'direct') and (move.state == 'assigned') and (move.product_qty):
                    return True
                ok = ok and (move.state in ('cancel', 'done', 'assigned'))
        return ok

    def action_cancel(self, cr, uid, ids, context=None):
        """ Changes picking state to cancel.
        @return: True
        """
        for pick in self.browse(cr, uid, ids, context=context):
            ids2 = [move.id for move in pick.move_lines]
            self.pool.get('stock.move').action_cancel(cr, uid, ids2, context)
        self.write(cr, uid, ids, {'state': 'cancel', 'invoice_state': 'none'})
        return True

    #
    # TODO: change and create a move if not parents
    #
    def action_done(self, cr, uid, ids, context=None):
        """Changes picking state to done.
        
        This method is called at the end of the workflow by the activity "done".
        @return: True
        """
        self.write(cr, uid, ids, {'state': 'done', 'date_done': time.strftime('%Y-%m-%d %H:%M:%S')})
        return True

    def action_move(self, cr, uid, ids, context=None):
        """Process the Stock Moves of the Picking
        
        This method is called by the workflow by the activity "move".
        Normally that happens when the signal button_done is received (button 
        "Done" pressed on a Picking view). 
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

    def get_currency_id(self, cr, uid, picking):
        return False

    def _get_partner_to_invoice(self, cr, uid, picking, context=None):
        """ Gets the partner that will be invoiced
            Note that this function is inherited in the sale and purchase modules
            @param picking: object of the picking for which we are selecting the partner to invoice
            @return: object of the partner to invoice
        """
        return picking.partner_id and picking.partner_id.id

    def _get_comment_invoice(self, cr, uid, picking):
        """
        @return: comment string for invoice
        """
        return picking.note or ''

    def _get_price_unit_invoice(self, cr, uid, move_line, type, context=None):
        """ Gets price unit for invoice
        @param move_line: Stock move lines
        @param type: Type of invoice
        @return: The price unit for the move line
        """
        if context is None:
            context = {}

        if type in ('in_invoice', 'in_refund'):
            # Take the user company and pricetype
            context['currency_id'] = move_line.company_id.currency_id.id
            amount_unit = move_line.product_id.price_get('standard_price', context=context)[move_line.product_id.id]
            return amount_unit
        else:
            return move_line.product_id.list_price

    def _get_discount_invoice(self, cr, uid, move_line):
        '''Return the discount for the move line'''
        return 0.0

    def _get_taxes_invoice(self, cr, uid, move_line, type):
        """ Gets taxes on invoice
        @param move_line: Stock move lines
        @param type: Type of invoice
        @return: Taxes Ids for the move line
        """
        if type in ('in_invoice', 'in_refund'):
            taxes = move_line.product_id.supplier_taxes_id
        else:
            taxes = move_line.product_id.taxes_id

        if move_line.picking_id and move_line.picking_id.partner_id and move_line.picking_id.partner_id.id:
            return self.pool.get('account.fiscal.position').map_tax(
                cr,
                uid,
                move_line.picking_id.partner_id.property_account_position,
                taxes
            )
        else:
            return map(lambda x: x.id, taxes)

    def _get_account_analytic_invoice(self, cr, uid, picking, move_line):
        return False

    def _invoice_line_hook(self, cr, uid, move_line, invoice_line_id):
        '''Call after the creation of the invoice line'''
        return

    def _invoice_hook(self, cr, uid, picking, invoice_id):
        '''Call after the creation of the invoice'''
        return

    def _get_invoice_type(self, pick):
        src_usage = dest_usage = None
        inv_type = None
        if pick.invoice_state == '2binvoiced':
            if pick.move_lines:
                src_usage = pick.move_lines[0].location_id.usage
                dest_usage = pick.move_lines[0].location_dest_id.usage
            if pick.type == 'out' and dest_usage == 'supplier':
                inv_type = 'in_refund'
            elif pick.type == 'out' and dest_usage == 'customer':
                inv_type = 'out_invoice'
            elif pick.type == 'in' and src_usage == 'supplier':
                inv_type = 'in_invoice'
            elif pick.type == 'in' and src_usage == 'customer':
                inv_type = 'out_refund'
            else:
                inv_type = 'out_invoice'
        return inv_type

    def _prepare_invoice_group(self, cr, uid, picking, partner, invoice, context=None):
        """ Builds the dict for grouped invoices
            @param picking: picking object
            @param partner: object of the partner to invoice (not used here, but may be usefull if this function is inherited)
            @param invoice: object of the invoice that we are updating
            @return: dict that will be used to update the invoice
        """
        comment = self._get_comment_invoice(cr, uid, picking)
        return {
            'name': (invoice.name or '') + ', ' + (picking.name or ''),
            'origin': (invoice.origin or '') + ', ' + (picking.name or '') + (picking.origin and (':' + picking.origin) or ''),
            'comment': (comment and (invoice.comment and invoice.comment + "\n" + comment or comment)) or (invoice.comment and invoice.comment or ''),
            'date_invoice': context.get('date_inv', False),
            'user_id': uid,
        }

    def _prepare_invoice(self, cr, uid, picking, partner, inv_type, journal_id, context=None):
        """ Builds the dict containing the values for the invoice
            @param picking: picking object
            @param partner: object of the partner to invoice
            @param inv_type: type of the invoice ('out_invoice', 'in_invoice', ...)
            @param journal_id: ID of the accounting journal
            @return: dict that will be used to create the invoice object
        """
        if isinstance(partner, int):
            partner = self.pool.get('res.partner').browse(cr, uid, partner, context=context)
        if inv_type in ('out_invoice', 'out_refund'):
            account_id = partner.property_account_receivable.id
            payment_term = partner.property_payment_term.id or False
        else:
            account_id = partner.property_account_payable.id
            payment_term = partner.property_supplier_payment_term.id or False
        comment = self._get_comment_invoice(cr, uid, picking)
        invoice_vals = {
            'name': picking.name,
            'origin': (picking.name or '') + (picking.origin and (':' + picking.origin) or ''),
            'type': inv_type,
            'account_id': account_id,
            'partner_id': partner.id,
            'comment': comment,
            'payment_term': payment_term,
            'fiscal_position': partner.property_account_position.id,
            'date_invoice': context.get('date_inv', False),
            'company_id': picking.company_id.id,
            'user_id': uid,
        }
        cur_id = self.get_currency_id(cr, uid, picking)
        if cur_id:
            invoice_vals['currency_id'] = cur_id
        if journal_id:
            invoice_vals['journal_id'] = journal_id
        return invoice_vals

    def _prepare_invoice_line(self, cr, uid, group, picking, move_line, invoice_id,
        invoice_vals, context=None):
        """ Builds the dict containing the values for the invoice line
            @param group: True or False
            @param picking: picking object
            @param: move_line: move_line object
            @param: invoice_id: ID of the related invoice
            @param: invoice_vals: dict used to created the invoice
            @return: dict that will be used to create the invoice line
        """
        if group:
            name = (picking.name or '') + '-' + move_line.name
        else:
            name = move_line.name
        origin = move_line.picking_id.name or ''
        if move_line.picking_id.origin:
            origin += ':' + move_line.picking_id.origin

        if invoice_vals['type'] in ('out_invoice', 'out_refund'):
            account_id = move_line.product_id.property_account_income.id
            if not account_id:
                account_id = move_line.product_id.categ_id.\
                        property_account_income_categ.id
        else:
            account_id = move_line.product_id.property_account_expense.id
            if not account_id:
                account_id = move_line.product_id.categ_id.\
                        property_account_expense_categ.id
        if invoice_vals['fiscal_position']:
            fp_obj = self.pool.get('account.fiscal.position')
            fiscal_position = fp_obj.browse(cr, uid, invoice_vals['fiscal_position'], context=context)
            account_id = fp_obj.map_account(cr, uid, fiscal_position, account_id)
        # set UoS if it's a sale and the picking doesn't have one
        uos_id = move_line.product_uos and move_line.product_uos.id or False
        if not uos_id and invoice_vals['type'] in ('out_invoice', 'out_refund'):
            uos_id = move_line.product_uom.id

        return {
            'name': name,
            'origin': origin,
            'invoice_id': invoice_id,
            'uos_id': uos_id,
            'product_id': move_line.product_id.id,
            'account_id': account_id,
            'price_unit': self._get_price_unit_invoice(cr, uid, move_line, invoice_vals['type']),
            'discount': self._get_discount_invoice(cr, uid, move_line),
            'quantity': move_line.product_uos_qty or move_line.product_qty,
            'invoice_line_tax_id': [(6, 0, self._get_taxes_invoice(cr, uid, move_line, invoice_vals['type']))],
            'account_analytic_id': self._get_account_analytic_invoice(cr, uid, picking, move_line),
        }

    def action_invoice_create(self, cr, uid, ids, journal_id=False,
            group=False, type='out_invoice', context=None):
        """ Creates invoice based on the invoice state selected for picking.
        @param journal_id: Id of journal
        @param group: Whether to create a group invoice or not
        @param type: Type invoice to be created
        @return: Ids of created invoices for the pickings
        """
        if context is None:
            context = {}

        invoice_obj = self.pool.get('account.invoice')
        invoice_line_obj = self.pool.get('account.invoice.line')
        partner_obj = self.pool.get('res.partner')
        invoices_group = {}
        res = {}
        inv_type = type
        for picking in self.browse(cr, uid, ids, context=context):
            if picking.invoice_state != '2binvoiced':
                continue
            partner = self._get_partner_to_invoice(cr, uid, picking, context=context)
            if isinstance(partner, int):
                partner = partner_obj.browse(cr, uid, [partner], context=context)[0]
            if not partner:
                raise osv.except_osv(_('Error, no partner!'),
                    _('Please put a partner on the picking list if you want to generate invoice.'))

            if not inv_type:
                inv_type = self._get_invoice_type(picking)

            if group and partner.id in invoices_group:
                invoice_id = invoices_group[partner.id]
                invoice = invoice_obj.browse(cr, uid, invoice_id)
                invoice_vals_group = self._prepare_invoice_group(cr, uid, picking, partner, invoice, context=context)
                invoice_obj.write(cr, uid, [invoice_id], invoice_vals_group, context=context)
            else:
                invoice_vals = self._prepare_invoice(cr, uid, picking, partner, inv_type, journal_id, context=context)
                invoice_id = invoice_obj.create(cr, uid, invoice_vals, context=context)
                invoices_group[partner.id] = invoice_id
            res[picking.id] = invoice_id
            for move_line in picking.move_lines:
                if move_line.state == 'cancel':
                    continue
                if move_line.scrapped:
                    # do no invoice scrapped products
                    continue
                vals = self._prepare_invoice_line(cr, uid, group, picking, move_line,
                                invoice_id, invoice_vals, context=context)
                if vals:
                    invoice_line_id = invoice_line_obj.create(cr, uid, vals, context=context)
                    self._invoice_line_hook(cr, uid, move_line, invoice_line_id)

            invoice_obj.button_compute(cr, uid, [invoice_id], context=context,
                    set_total=(inv_type in ('in_invoice', 'in_refund')))
            self.write(cr, uid, [picking.id], {
                'invoice_state': 'invoiced',
                }, context=context)
            self._invoice_hook(cr, uid, picking, invoice_id)
        self.write(cr, uid, res.keys(), {
            'invoice_state': 'invoiced',
            }, context=context)
        return res

    def test_done(self, cr, uid, ids, context=None):
        """ Test whether the move lines are done or not.
        @return: True or False
        """
        ok = False
        for pick in self.browse(cr, uid, ids, context=context):
            if not pick.move_lines:
                return True
            for move in pick.move_lines:
                if move.state not in ('cancel','done'):
                    return False
                if move.state=='done':
                    ok = True
        return ok

    def test_cancel(self, cr, uid, ids, context=None):
        """ Test whether the move lines are canceled or not.
        @return: True or False
        """
        for pick in self.browse(cr, uid, ids, context=context):
            for move in pick.move_lines:
                if move.state not in ('cancel',):
                    return False
        return True

    def unlink(self, cr, uid, ids, context=None):
        move_obj = self.pool.get('stock.move')
        if context is None:
            context = {}
        for pick in self.browse(cr, uid, ids, context=context):
            if pick.state in ['done','cancel']:
                raise osv.except_osv(_('Error!'), _('You cannot remove the picking which is in %s state!')%(pick.state,))
            else:
                ids2 = [move.id for move in pick.move_lines]
                ctx = context.copy()
                ctx.update({'call_unlink':True})
                if pick.state != 'draft':
                    #Cancelling the move in order to affect Virtual stock of product
                    move_obj.action_cancel(cr, uid, ids2, ctx)
                #Removing the move
                move_obj.unlink(cr, uid, ids2, ctx)

        return super(stock_picking, self).unlink(cr, uid, ids, context=context)




    # FP Note: review all methods aboce this line for stock.picking

    #TODO move this in another class?
    def get_done_reserved_quants(self, cr, uid, picking_id, move, context=None):
        stock_operation_obj = self.pool.get('stock.pack.operation')
        quant_obj = self.pool.get('stock.quant')
        possible_quants = [x.id for x in move.reserved_quant_ids]
        operation_ids = stock_operation_obj.find_packaging_op_from_product(cr, uid, move.product_id, picking_id, context=context)
        todo_later = []
        possible_quants = [quant.id for quant in move.reserved_quant_ids]
        done_reserved_quants = set()
        for op in stock_operation_obj.browse(cr, uid, operation_ids, context=context):
            if op.product_id:
                #TODO: document me
                todo_later += [op.id]
            elif op.quant_id:
                #split for partial and take care of reserved quants
                quant_tuples = quant_obj._get_quant_tuples(cr, uid, [op.quant_id.id], op.product_qty, context=context)
                quant_obj.real_split_quants(cr, uid, quant_tuples, context=context)
                done_reserved_quants = done_reserved_quants.union(set([qt[O] for qt in quant_tuples]))
            elif op.package_id:
                #moving a package never splits quants but we need to take care of the reserved_quant_ids
                all_children_quants = self.pool.get('stock.quant.package').quants_get(cr, uid, op.package_id, context=context)
                done_reserved_quants = done_reserved_quants.union(set(all_chilren_quants))

        #finish the partial split by operation that leaves the choice of quant to move
        for op in stock_operation_obj.browse(cr, uid, todo_later, context=context):
            quant_tuples = quant_obj._get_quant_tuples(cr, uid, possible_quants, op.product_qty, context=context)
            quant_obj.real_split_quants(cr, uid, quant_tuples, context=context)
            done_reserved_quants = done_reserved_quants.union(set([qt[O] for qt in quant_tuples]))

        return done_reserved_quants

    #TODO move this in another class?
    def make_packaging(self, cr, uid, picking_id, move, possible_quants, context=None):
        stock_operation_obj = self.pool.get('stock.pack.operation')
        quant_obj = self.pool.get('stock.quant')
        operation_ids = stock_operation_obj.find_packaging_op_from_product(cr, uid, move.product_id, picking_id, context=context)
        for op in stock_operation_obj.browse(cr, uid, operation_ids, context=context):
            if not op.result_package_id:
                continue
            if op.product_id:
                quant_tuples = quant_obj._get_quant_tuples(cr, uid, possible_quants, op.product_qty, context=context)
                quant_obj.real_split_quants(cr, uid, quant_tuples, context=context)
                quant_obj.write(cr, uid, [qt[O] for qt in quant_tuples], {'package_id': op.result_package_id.id}, context=context)
            elif op.quant_id:
                quant_tuples = quant_obj._get_quant_tuples(cr, uid, [op.quant_id.id], op.product_qty, context=context)
                quant_obj.real_split_quants(cr, uid, quant_tuples, context=context)
                quant_obj.write(cr, uid, [qt[O] for qt in quant_tuples], {'package_id': op.result_package_id.id}, context=context)
            elif op.package_id:
                #pack existing packs
                self.pool.get('stock.quant.package').write(cr, uid, op.package_id.id, {'parent_id': op.result_package_id.id}, context=context)

    def do_partial(self, cr, uid, ids, partial_datas, context=None):
        """ Makes partial picking and moves done.
        @param partial_datas : Dictionary containing details of partial picking
                          like partner_id, partner_id, delivery_date,
                          delivery moves with product_id, product_qty, uom
        @return: Dictionary of values
        """
        if context is None:
            context = {}
        else:
            context = dict(context)
        res = {}
        move_obj = self.pool.get('stock.move')
        product_obj = self.pool.get('product.product')
        currency_obj = self.pool.get('res.currency')
        uom_obj = self.pool.get('product.uom')
        sequence_obj = self.pool.get('ir.sequence')
        wf_service = netsvc.LocalService("workflow")
        for pick in self.browse(cr, uid, ids, context=context):
            new_picking = None
            complete, too_many, too_few = [], [], []
            move_product_qty, prodlot_ids, partial_qty, product_uoms = {}, {}, {}, {}

            
            for move in pick.move_lines:
                if move.state in ('done', 'cancel'):
                    continue
                partial_data = partial_datas.get('move%s'%(move.id), {})
                product_qty = partial_data.get('product_qty',0.0)
                move_product_qty[move.id] = product_qty
                product_uom = partial_data.get('product_uom',False)
                product_price = partial_data.get('product_price',0.0)
                prodlot_id = partial_data.get('prodlot_id')
                prodlot_ids[move.id] = prodlot_id
                product_uoms[move.id] = product_uom
                partial_qty[move.id] = uom_obj._compute_qty(cr, uid, product_uoms[move.id], product_qty, move.product_uom.id)
                if move.product_qty == partial_qty[move.id]:
                    complete.append(move)
                elif move.product_qty > partial_qty[move.id]:
                    too_few.append(move)
                else:
                    too_many.append(move)


            for move in too_few:
                #create a backorder stock move with the remaining quantity
                product_qty = move_product_qty[move.id]
                if not new_picking:
                    #a backorder picking doesn't exist yet, create a new one
                    new_picking_name = pick.name
                    self.write(cr, uid, [pick.id], 
                               {'name': sequence_obj.get(cr, uid,
                                            'stock.picking.%s'%(pick.type)),
                               })
                    new_picking = self.copy(cr, uid, pick.id,
                            {
                                'name': new_picking_name,
                                'move_lines' : [],
                                'state':'draft',
                            })
                    #modify the existing picking (this trick is needed to keep the eventual workflows pointing on the first picking)
                    unlink_operation_order = [(2, op.id) for op in pick.pack_operation_ids]
                    self.write(cr, uid, [pick.id], 
                               {
                                'pack_operation_ids': unlink_operation_order
                               })
                done_reserved_quants = set()
                if product_qty != 0:
                    #take care of partial picking in reserved quants
                    done_reserved_quants = self.get_done_reserved_quants(cr, uid, pick.id, move, context=context)
                    #copy the stock move
                    new_picking_record = self.browse(cr, uid, new_picking, context=context)

                    defaults = {
                            'product_qty' : product_qty,
                            'product_uos_qty': product_qty, #TODO: put correct uos_qty
                            'picking_id' : new_picking,
                            'state': 'assigned',
                            'move_dest_id': False,
                            'price_unit': product_price,
                            'product_uom': product_uoms[move.id],
                            'reserved_quant_ids': list(done_reserved_quants)
                    }
                    prodlot_id = prodlot_ids[move.id]
                    if prodlot_id:
                        defaults.update(prodlot_id=prodlot_id)
                    backorder_move_id = move_obj.copy(cr, uid, move.id, defaults)
                    self.make_packaging(cr, uid, pick.id, move_obj.browse(cr, uid, backorder_move_id, context=context), list(done_reserved_quants), context=context)
                #modify the existing stock move    
                possible_quants = [x.id for x in move.reserved_quant_ids]
                move_obj.write(cr, uid, [move.id],
                        {
                            'product_qty': move.product_qty - partial_qty[move.id],
                            'product_uos_qty': move.product_qty - partial_qty[move.id], #TODO: put correct uos_qty
                            'prodlot_id': False,
                            'tracking_id': False,
                            'reserved_quant_ids': list(set(possible_quants) - done_reserved_quants),
                        })

            if new_picking:
                move_obj.write(cr, uid, [c.id for c in complete], {'picking_id': new_picking})
            for move in complete:
                defaults = {'product_uom': product_uoms[move.id], 'product_qty': move_product_qty[move.id]}
                if prodlot_ids.get(move.id):
                    defaults.update({'prodlot_id': prodlot_ids[move.id]})
                move_obj.write(cr, uid, [move.id], defaults)


                #take care of packaging for completed moves
                possible_quants = [x.id for x in move.reserved_quant_ids]

                self.make_packaging(cr, uid, new_picking, move, possible_quants, context=context)



            for move in too_many:
                product_qty = move_product_qty[move.id]
                defaults = {
                    'product_qty' : product_qty,
                    'product_uos_qty': product_qty, #TODO: put correct uos_qty
                    'product_uom': product_uoms[move.id]
                }
                prodlot_id = prodlot_ids.get(move.id)
                if prodlot_ids.get(move.id):
                    defaults.update(prodlot_id=prodlot_id)
                if new_picking:
                    defaults.update(picking_id=new_picking)
                move_obj.write(cr, uid, [move.id], defaults)

                possible_quants = [x.id for x in move.reserved_quant_ids]
                self.make_packaging(cr, uid, new_picking, move, possible_quants, context=context)
            # At first we confirm the new picking (if necessary)
            if new_picking:
                self.signal_button_confirm(cr, uid, [new_picking])
                # Then we finish the good picking
                self.write(cr, uid, [pick.id], {'backorder_id': new_picking})
                self.action_move(cr, uid, [new_picking], context=context)
                self.signal_button_done(cr, uid, [new_picking])
                wf_service.trg_write(uid, 'stock.picking', pick.id, cr)
                delivered_pack_id = new_picking
                back_order_name = self.browse(cr, uid, delivered_pack_id, context=context).name
                self.message_post(cr, uid, ids, body=_("Back order <em>%s</em> has been <b>created</b>.") % (back_order_name), context=context)
            else:
                self.action_move(cr, uid, [pick.id], context=context)
                self.signal_button_done(cr, uid, [pick.id])
                delivered_pack_id = pick.id

            delivered_pack = self.browse(cr, uid, delivered_pack_id, context=context)
            res[pick.id] = {'delivered_picking': delivered_pack.id}

        return res
    
    # views associated to each picking type
    _VIEW_LIST = {
        'out': 'view_picking_out_form',
        'in': 'view_picking_in_form',
        'internal': 'view_picking_form',
    }
    def _get_view_id(self, cr, uid, type):
        """Get the view id suiting the given type
        
        @param type: the picking type as a string
        @return: view i, or False if no view found
        """
        res = self.pool.get('ir.model.data').get_object_reference(cr, uid, 
            'stock', self._VIEW_LIST.get(type, 'view_picking_form'))            
        return res and res[1] or False

    def _get_picking_for_packing_ui(self, cr, uid, context=None):
        res = self.search(cr, uid, [('state', '=', 'assigned')], limit=1, context=context)
        return res and res[0] or False  # TODO: what to do if nothing is left to do?

    def action_done_from_packing_ui(self, cr, uid, picking_id, context=None):
        if context is None:
            context = {}
        #create partial picking wizard that handles the split of stock moves and the backorder if needed
        ctx = context.copy()
        ctx['active_ids'] = [picking_id]
        ctx['active_model'] = 'stock.picking'
        partial_picking_obj = self.pool.get('stock.partial.picking')
        partial_wizard_id = partial_picking_obj.create(cr, uid, {}, context=ctx)
        partial_wizard_result = partial_picking_obj.do_partial(cr, uid, [partial_wizard_id], context=context)

        #todo_picking_id = picking_id if picking was total, it's the backorder if the picking was partial
        #todo_picking_id = partial_wizard_result[picking_id]['delivered_picking']





#all stuff below should be removed except the parent packaging /!\
#        all_done_quants = []
#        for move in self.browse(cr, uid, todo_picking_id, context=context).move_lines:
#            all_done_quants += [quant.id for quant in move.reserved_quant_ids]
#
#        for operation in self.browse(cr, uid, todo_picking_id, context=context).pack_operation_ids:
#            if operation.result_package_id:
#                if operation.package_id:
#                    if operation.package_id.parent_id:
#                        # decide what to do ?
#                        pass
#                    #pack existing packs
#                    self.pool.get('stock.quant.package').write(cr, uid, operation.package_id.id, {'parent_id': operation.result_package_id.id}, context=context)
#                elif operation.product_id:
#                    #self.split_and_assign_quants(
#                    pass
#
#
#
#
#                if self.pool.get('stock.pack.operation').search(cr, uid, [('picking_id', '=', todo_picking_id), ('result_package_id', '!=', False)]
#                    pass
#        #def split_and_assign_quants(self, cr, uid, quant_tuples, move, context=None):
#        #fill all the packages with assigned operations
#        for operation in self.browse(cr, uid, todo_picking_id, context=context).pack_operation_ids:
#            if operation.result_package_id:
#                if operation.package_id:
#                    #pack existing packs
#                    self.pool.get('stock.quant.package').write(cr, uid, operation.package_id.id, {'parent_id': operation.result_package_id.id}, context=context)
#                elif operation.quant_id:
#                    if operation.quant_id.parent_id:
#                        # decide what to do
#                        pass
#                    #assign_pack may split the quant and write the package on it (above test should be in that method instead)
#                    self.pool.get('stock.quant').assign_pack(cr, uid, operation.quant_id.id, operation.product_qty, operation.result_package_id.id, context=context)
#                elif operation.product_id:
#                    pass 
#        #don't call action_done of picking because it will make all moves don, but make a partial delivery
#        line_ids = []
#        for move in self.browse(cr, uid, picking_id, context=context).move_lines:
#            line += [{
#                'product_id': move.product_id.id,
#                'quantity': move.product_qty - move.remaining_qty,
#                'product_uom': move.product_uom_id.id,
#
#            }]
#
#        #self.action_done(cr, uid, picking_id, context=context)

        #return id of next picking to work on
        return self._get_picking_for_packing_ui(cr, uid, context=context)

    def action_pack(self, cr, uid, picking_id, context=None):
        #put all the operations of the picking that aren't yet assigned to a package to this new one
        stock_operation_obj = self.pool.get('stock.pack.operation')
        package_obj = self.pool.get('stock.quant.package')
        #create a new empty stock.quant.package
        package_id = package_obj.create(cr, uid, {}, context=context)
        #put all the operations of the picking that aren't yet assigned to a package to this new one
        operation_ids = stock_operation_obj.search(cr, uid, [('picking_id', '=', picking_id), ('result_package_id', '=', False)], context=context)
        stock_operation_obj.write(cr, uid, operation_ids, {'result_package_id': package_id}, context=context)
        pass
        #return {'warnings': '', 'stock_move_to_update': [{}], 'package_to_update': [{}]}

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
        matching_product_ids = product_obj.search(cr, uid, ['|', ('code','=',barcode_str), ('ean13', '=', barcode_str)], context=context)
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
    }
    _defaults = {
        'name': lambda x, y, z, c: x.pool.get('ir.sequence').get(y, z, 'stock.lot.serial'),
        'product_id': lambda x, y, z, c: c.get('product_id', False),
    }
    _sql_constraints = [
        ('name_ref_uniq', 'unique (name, ref)', 'The combination of Serial Number and internal reference must be unique !'),
    ]
    def action_traceability(self, cr, uid, ids, context=None):
        """ It traces the information of a product
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: List of IDs selected
        @param context: A standard dictionary
        @return: A dictionary of values
        """
        value=self.pool.get('action.traceability').action_traceability(cr,uid,ids,context)
        return value


# ----------------------------------------------------
# Move
# ----------------------------------------------------

class stock_move(osv.osv):
    _name = "stock.move"
    _description = "Stock Move"
    _order = 'date_expected desc, id'
    _log_create = False

    def action_partial_move(self, cr, uid, ids, context=None):
        if context is None: context = {}
        if context.get('active_model') != self._name:
            context.update(active_ids=ids, active_model=self._name)
        partial_id = self.pool.get("stock.partial.move").create(
            cr, uid, {}, context=context)
        return {
            'name':_("Products to Process"),
            'view_mode': 'form',
            'view_id': False,
            'view_type': 'form',
            'res_model': 'stock.partial.move',
            'res_id': partial_id,
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'domain': '[]',
            'context': context
        }

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
    #         if not move.prodlot_id and \
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
    #
    # def _check_product_lot(self, cr, uid, ids, context=None):
    #     """ Checks whether move is done or not and production lot is assigned to that move.
    #     @return: True or False
    #     """
    #     for move in self.browse(cr, uid, ids, context=context):
    #         if move.prodlot_id and move.state == 'done' and (move.prodlot_id.product_id.id != move.product_id.id):
    #             return False
    #     return True

    _columns = {
        'name': fields.char('Description', required=True, select=True),
        'priority': fields.selection([('0', 'Not urgent'), ('1', 'Urgent')], 'Priority'),
        'create_date': fields.datetime('Creation Date', readonly=True, select=True),
        'date': fields.datetime('Date', required=True, select=True, help="Move date: scheduled date until move is done, then date of actual move processing", states={'done': [('readonly', True)]}),
        'date_expected': fields.datetime('Scheduled Date', states={'done': [('readonly', True)]},required=True, select=True, help="Scheduled date for the processing of this move"),
        'product_id': fields.many2one('product.product', 'Product', required=True, select=True, domain=[('type','<>','service')],states={'done': [('readonly', True)]}),
        'product_qty': fields.float('Quantity', digits_compute=dp.get_precision('Product Unit of Measure'),
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

        'auto_validate': fields.boolean('Auto Validate'),

        'move_dest_id': fields.many2one('stock.move', 'Destination Move', help="Optional: next stock move when chaining them", select=True),
        'move_orig_ids': fields.one2many('stock.move', 'move_dest_id', 'Original Move', help="Optional: next stock move when chaining them", select=True),

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

        # used for colors in tree views:
        'scrapped': fields.related('location_dest_id','scrap_location',type='boolean',relation='stock.location',string='Scrapped', readonly=True),
        'type': fields.related('picking_id', 'type', type='selection', selection=[('out', 'Sending Goods'), ('in', 'Getting Goods'), ('internal', 'Internal')], string='Shipping Type'),

        'quant_ids': fields.many2many('stock.quant',  'stock_quant_move_rel', 'move_id', 'quant_id', 'Quants'),
        'reserved_quant_ids': fields.one2many('stock.quant', 'reservation_id', 'Reserved quants'),

        # FP Note: this should be a function field
        'remaining_qty': fields.float('Remaining Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), states={'done': [('readonly', True)]}),  # to be used in pick/pack new interface  # TODO change this in a functional field to ease the handling
    }

    def _check_location(self, cr, uid, ids, context=None):
        for record in self.browse(cr, uid, ids, context=context):
            if (record.state=='done') and (record.location_id.usage == 'view'):
                raise osv.except_osv(_('Error'), _('You cannot move product %s from a location of type view %s.')% (record.product_id.name, record.location_id.name))
            if (record.state=='done') and (record.location_dest_id.usage == 'view' ):
                raise osv.except_osv(_('Error'), _('You cannot move product %s to a location of type view %s.')% (record.product_id.name, record.location_dest_id.name))
        return True

    _constraints = [
        (_check_location, 'You cannot move products from or to a location of the type view.',
            ['location_id','location_dest_id'])
    ]

    def _default_location_destination(self, cr, uid, context=None):
        """ Gets default address of partner for destination location
        @return: Address id or False
        """
        mod_obj = self.pool.get('ir.model.data')
        picking_type = context.get('picking_type')
        location_id = False
        if context is None:
            context = {}
        if context.get('move_line', []):
            if context['move_line'][0]:
                if isinstance(context['move_line'][0], (tuple, list)):
                    location_id = context['move_line'][0][2] and context['move_line'][0][2].get('location_dest_id',False)
                else:
                    move_list = self.pool.get('stock.move').read(cr, uid, context['move_line'][0], ['location_dest_id'])
                    location_id = move_list and move_list['location_dest_id'][0] or False
        elif context.get('address_out_id', False):
            property_out = self.pool.get('res.partner').browse(cr, uid, context['address_out_id'], context).property_stock_customer
            location_id = property_out and property_out.id or False
        else:
            location_xml_id = False
            if picking_type in ('in', 'internal'):
                location_xml_id = 'stock_location_stock'
            elif picking_type == 'out':
                location_xml_id = 'stock_location_customers'
            if location_xml_id:
                location_model, location_id = mod_obj.get_object_reference(cr, uid, 'stock', location_xml_id)
                if location_id:
                    location_company = self.pool.get("stock.location").browse(cr, uid, location_id, context=context).company_id
                    user_company = self.pool.get("res.users").browse(cr, uid, uid, context=context).company_id.id
                    if location_company and location_company.id != user_company:
                        location_id = False
        return location_id

    def _default_location_source(self, cr, uid, context=None):
        """ Gets default address of partner for source location
        @return: Address id or False
        """
        mod_obj = self.pool.get('ir.model.data')
        picking_type = context.get('picking_type')
        location_id = False

        if context is None:
            context = {}
        if context.get('move_line', []):
            try:
                location_id = context['move_line'][0][2]['location_id']
            except:
                pass
        elif context.get('address_in_id', False):
            part_obj_add = self.pool.get('res.partner').browse(cr, uid, context['address_in_id'], context=context)
            if part_obj_add:
                location_id = part_obj_add.property_stock_supplier.id
        else:
            location_xml_id = False
            if picking_type == 'in':
                location_xml_id = 'stock_location_suppliers'
            elif picking_type in ('out', 'internal'):
                location_xml_id = 'stock_location_stock'
            if location_xml_id:
                location_model, location_id = mod_obj.get_object_reference(cr, uid, 'stock', location_xml_id)
                if location_id:
                    location_company = self.pool.get("stock.location").browse(cr, uid, location_id, context=context).company_id
                    user_company = self.pool.get("res.users").browse(cr, uid, uid, context=context).company_id.id
                    if location_company and location_company.id != user_company:
                        location_id = False
        return location_id

    def _default_destination_address(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        return user.company_id.partner_id.id

    def _default_move_type(self, cr, uid, context=None):
        """ Gets default type of move
        @return: type
        """
        context = context or {}
        return context.get('picking_type', 'internal')

    _defaults = {
        'location_id': _default_location_source,
        'location_dest_id': _default_location_destination,
        'partner_id': _default_destination_address,
        'type': _default_move_type,
        'state': 'draft',
        'priority': '1',
        'product_qty': 1.0,
        'scrapped' :  False,
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'stock.move', context=c),
        'date_expected': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
    }

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
        self._update_picking(cr, uid, ids, vals, context=context)
        return result

    # update picking as the move changed
    def _update_picking(self, cr, uid, ids, vals, context=None):
        # FP Note: test if this would do the trick
        #for id in ids:
        #    wf_service.trg_trigger(uid, 'stock.move', id, cr)
        if ('state' in vals) or ('picking_id' in vals):
            wf_service = netsvc.LocalService('workflow')
            done = {}
            for move in self.browse(cr, uid, ids, context):
                if move.picking_id and (move.picking_id.id not in done):
                    wf_service.trg_write(uid, 'stock.picking', move.picking_id.id, cr)
                    done[move.picking_id.id] = True
        return True

    def _auto_init(self, cursor, context=None):
        res = super(stock_move, self)._auto_init(cursor, context=context)
        cursor.execute('SELECT indexname \
                FROM pg_indexes \
                WHERE indexname = \'stock_move_location_id_location_dest_id_product_id_state\'')
        if not cursor.fetchone():
            cursor.execute('CREATE INDEX stock_move_location_id_location_dest_id_product_id_state \
                    ON stock_move (product_id, state, location_id, location_dest_id)')
        return res

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
                  'product_qty': 0.00
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
            result['product_qty'] = product_uos_qty / uos_coeff['uos_coeff']
        else:
            result['product_qty'] = product_uos_qty
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
            'product_qty': 1.00,
            'product_uos_qty' : self.pool.get('stock.move').onchange_quantity(cr, uid, ids, prod_id, 1.00, product.uom_id.id, uos_id)['value']['product_uos_qty'],
            'prodlot_id' : False,
        }
        if not ids:
            result['name'] = product.partner_ref
        if loc_id:
            result['location_id'] = loc_id
        if loc_dest_id:
            result['location_dest_id'] = loc_dest_id
        return {'value': result}

    def onchange_move_type(self, cr, uid, ids, type, context=None):
        """ On change of move type gives sorce and destination location.
        @param type: Move Type
        @return: Dictionary of values
        """
        mod_obj = self.pool.get('ir.model.data')
        location_source_id = 'stock_location_stock'
        location_dest_id = 'stock_location_stock'
        if type == 'in':
            location_source_id = 'stock_location_suppliers'
            location_dest_id = 'stock_location_stock'
        elif type == 'out':
            location_source_id = 'stock_location_stock'
            location_dest_id = 'stock_location_customers'
        source_location = mod_obj.get_object_reference(cr, uid, 'stock', location_source_id)
        dest_location = mod_obj.get_object_reference(cr, uid, 'stock', location_dest_id)
        #Check companies
        user_company = self.pool.get("res.users").browse(cr, uid, uid, context=context).company_id.id
        if source_location:
            location_company = self.pool.get("stock.location").browse(cr, uid, source_location[1], context=context).company_id
            if location_company and location_company.id != user_company:
                source_location = False
        if dest_location:
            location_company = self.pool.get("stock.location").browse(cr, uid, dest_location[1], context=context).company_id
            if location_company and location_company.id != user_company:
                dest_location = False
        return {'value':{'location_id': source_location and source_location[1] or False, 'location_dest_id': dest_location and dest_location[1] or False}}

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
                if m.state not in ('done','cancel'):
                    state = 'waiting'
            states[state].append(move.id)

        if not move.picking_id:
            # TODO: Put the move in the right picking according to groups
            pass

        for state, write_ids in states.items():
            if len(write_ids):
                self.write(cr, uid, write_ids, {'state': state})
        return True

    def force_assign(self, cr, uid, ids, context=None):
        """ Changes the state to assigned.
        @return: True
        """
        self.action_assign(cr, uid, ids, context=context)
        return self.write(cr, uid, ids, {'state': 'assigned'})

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
                if move.move_orig_ids:
                    for m2 in move.move_orig_ids:
                        for q in m2.quant_ids:
                            dp.append(q.id)
                quants = quant_obj.quants_get(cr, uid, move.location_id.id, move.product_id.id, qty, domain_preference=dp and [('id', 'in', dp)], context=context)
                quant_obj.quants_reserve(cr, uid, quants, move.id, context=context)
        self.write(cr, uid, done, {'state': 'assigned'})

    # FP Note: remove this line
    check_assign = action_assign

    #
    # Cancel move => cancel others move and pickings
    #
    def action_cancel(self, cr, uid, ids, context=None):
        """ Cancels the moves and if all moves are cancelled it cancels the picking.
        @return: True
        """
        context = context or {}
        for move in self.browse(cr, uid, ids, context=context):
            # FP Note: should we create a MTS procurement here?
            if move.move_dest_id:
                if move.cancel_cascade:
                    self.action_cancel(cr, uid, [move.move_dest_id.id], context=context)
                elif move.move_dest_id.state == 'waiting':
                    self.write(cr, uid, [move.move_dest_id.id], {'state': 'confirmed'})
        return self.write(cr, uid, ids, {'state': 'cancel', 'move_dest_id': False})

    # FP Note: all accounting valuation stuff must be on the quant
    def _get_accounting_data_for_valuation(self, cr, uid, move, context=None):
        """
        Return the accounts and journal to use to post Journal Entries for the real-time
        valuation of the move.

        :param context: context dictionary that can explicitly mention the company to consider via the 'force_company' key
        :raise: osv.except_osv() is any mandatory account or journal is not defined.
        """
        product_obj=self.pool.get('product.product')
        accounts = product_obj.get_product_accounts(cr, uid, move.product_id.id, context)
        if move.location_id.valuation_out_account_id:
            acc_src = move.location_id.valuation_out_account_id.id
        else:
            acc_src = accounts['stock_account_input']

        if move.location_dest_id.valuation_in_account_id:
            acc_dest = move.location_dest_id.valuation_in_account_id.id
        else:
            acc_dest = accounts['stock_account_output']

        acc_valuation = accounts.get('property_stock_valuation_account_id', False)
        journal_id = accounts['stock_journal']

        if acc_dest == acc_valuation:
            raise osv.except_osv(_('Error!'),  _('Cannot create Journal Entry, Output Account of this product and Valuation account on category of this product are same.'))

        if acc_src == acc_valuation:
            raise osv.except_osv(_('Error!'),  _('Cannot create Journal Entry, Input Account of this product and Valuation account on category of this product are same.'))

        if not acc_src:
            raise osv.except_osv(_('Error!'),  _('Please define stock input account for this product or its category: "%s" (id: %d)') % \
                                    (move.product_id.name, move.product_id.id,))
        if not acc_dest:
            raise osv.except_osv(_('Error!'),  _('Please define stock output account for this product or its category: "%s" (id: %d)') % \
                                    (move.product_id.name, move.product_id.id,))
        if not journal_id:
            raise osv.except_osv(_('Error!'), _('Please define journal on the product category: "%s" (id: %d)') % \
                                    (move.product_id.categ_id.name, move.product_id.categ_id.id,))
        if not acc_valuation:
            raise osv.except_osv(_('Error!'), _('Please define inventory valuation account on the product category: "%s" (id: %d)') % \
                                    (move.product_id.categ_id.name, move.product_id.categ_id.id,))
        return journal_id, acc_src, acc_dest, acc_valuation


    #We can use a preliminary type
    def get_reference_amount(self, cr, uid, move, qty, context=None):
        # if product is set to average price and a specific value was entered in the picking wizard,
        # we use it

        # by default the reference currency is that of the move's company
        reference_currency_id = move.company_id.currency_id.id
        
        #I use 
        if move.product_id.cost_method != 'standard' and move.price_unit:
            reference_amount = move.product_qty * move.price_unit #Using move.price_qty instead of qty to have correct amount
            reference_currency_id = move.price_currency_id.id or reference_currency_id

        # Otherwise we default to the company's valuation price type, considering that the values of the
        # valuation field are expressed in the default currency of the move's company.
        else:
            if context is None:
                context = {}
            currency_ctx = dict(context, currency_id = move.company_id.currency_id.id)
            amount_unit = move.product_id.price_get('standard_price', context=currency_ctx)[move.product_id.id]
            reference_amount = amount_unit * qty
        
        return reference_amount, reference_currency_id


    def _get_reference_accounting_values_for_valuation(self, cr, uid, move, context=None):
        """
        Return the reference amount and reference currency representing the inventory valuation for this move.
        These reference values should possibly be converted before being posted in Journals to adapt to the primary
        and secondary currencies of the relevant accounts.
        """
        product_uom_obj = self.pool.get('product.uom')

        default_uom = move.product_id.uom_id.id
        qty = product_uom_obj._compute_qty(cr, uid, move.product_uom.id, move.product_qty, default_uom)
        
        reference_amount, reference_currency_id = self.get_reference_amount(cr, uid, move, qty, context=context)
        return reference_amount, reference_currency_id


        


    def _create_product_valuation_moves(self, cr, uid, move, matches, context=None):
        """
        Generate the appropriate accounting moves if the product being moved is subject
        to real_time valuation tracking, and the source or the destination location is internal (not both)
        This means an in or out move. 
        
        Depending on the matches it will create the necessary moves
        """
        ctx = context.copy()
        ctx['force_company'] = move.company_id.id
        valuation = self.pool.get("product.product").browse(cr, uid, move.product_id.id, context=ctx).valuation
        move_obj = self.pool.get('account.move')
        if valuation == 'real_time':
            if context is None:
                context = {}
            company_ctx = dict(context,force_company=move.company_id.id)
            journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation(cr, uid, move, context=company_ctx)
            reference_amount, reference_currency_id = self._get_reference_accounting_values_for_valuation(cr, uid, move, context=company_ctx)
            account_moves = []
            # Outgoing moves (or cross-company output part)
            if move.location_id.company_id \
                and (move.location_id.usage == 'internal' and move.location_dest_id.usage != 'internal'):
                #returning goods to supplier
                if move.location_dest_id.usage == 'supplier':
                    account_moves += [(journal_id, self._create_account_move_line(cr, uid, move, matches, acc_valuation, acc_src, reference_amount, reference_currency_id, 'out', context=company_ctx))]
                else:
                    account_moves += [(journal_id, self._create_account_move_line(cr, uid, move, matches, acc_valuation, acc_dest, reference_amount, reference_currency_id, 'out', context=company_ctx))]

            # Incoming moves (or cross-company input part)
            if move.location_dest_id.company_id \
                and (move.location_id.usage != 'internal' and move.location_dest_id.usage == 'internal'):
                #goods return from customer
                if move.location_id.usage == 'customer':
                    account_moves += [(journal_id, self._create_account_move_line(cr, uid, move, matches, acc_dest, acc_valuation, reference_amount, reference_currency_id, 'in', context=company_ctx))]
                else:
                    account_moves += [(journal_id, self._create_account_move_line(cr, uid, move, matches, acc_src, acc_valuation, reference_amount, reference_currency_id, 'in', context=company_ctx))]
                if matches and move.product_id.cost_method in ('fifo', 'lifo'):
                    outs = {}
                    match_obj = self.pool.get("stock.move.matching")
                    for match in match_obj.browse(cr, uid, matches, context=context):
                        if match.move_out_id.id in outs:
                            outs[match.move_out_id.id] += [match.id]
                        else:
                            outs[match.move_out_id.id] = [match.id]
                    #When in stock was negative, you will get matches for the in also:
                    account_moves_neg = []
                    for out_mov in self.browse(cr, uid, outs.keys(), context=context):
                        journal_id_out, acc_src_out, acc_dest_out, acc_valuation_out = self._get_accounting_data_for_valuation(cr, uid, out_mov, context=company_ctx)
                        reference_amount_out, reference_currency_id_out = self._get_reference_accounting_values_for_valuation(cr, uid, out_mov, context=company_ctx)
                        if out_mov.location_dest_id.usage == 'supplier':
                            # Is not the way it should be with acc_valuation
                            account_moves_neg += [(journal_id_out, self._create_account_move_line(cr, uid, out_mov, outs[out_mov.id], acc_valuation_out, acc_src_out, reference_amount_out, reference_currency_id_out, 'out', context=company_ctx))]
                        else:
                            account_moves_neg += [(journal_id_out, self._create_account_move_line(cr, uid, out_mov, outs[out_mov.id], acc_valuation_out, acc_dest_out, reference_amount_out, reference_currency_id_out, 'out', context=company_ctx))]
                    #Create account moves for outs which made stock go negative
                    for j_id, move_lines in account_moves_neg:
                        move_obj.create(cr, uid,
                                        {'journal_id': j_id, 
                                         'line_id': move_lines, 
                                         'ref': out_mov.picking_id and out_mov.picking_id.name,
                                         })
            for j_id, move_lines in account_moves:
                move_obj.create(cr, uid,
                        {
                         'journal_id': j_id,
                         'line_id': move_lines,
                         'ref': move.picking_id and move.picking_id.name})

    def _get_quants_from_pack(self, cr, uid, ids, context=None):
        """
        Suppose for the moment we don't have any packaging
        """
        res = {}
        for move in self.browse(cr, uid, ids, context=context):
            #Split according to pack wizard if necessary
            res[move.id] = [x.id for x in move.reserved_quant_ids]
        return res


    def check_total_qty(self, cr, uid, ids, context=None):
        """
        This will check if the necessary quants for the moves have been reserved. 
        If not, it will retry to find the quants. 
        If it can not find it, it will have to create a negative quant
        
        """
        quant_obj = self.pool.get("stock.quant")
        uom_obj = self.pool.get("product.uom")
        for move in self.browse(cr, uid, ids, context=context):
            product_qty = 0.0
            for quant in move.reserved_quant_ids:
                product_qty += quant.qty
            qty_from_move = uom_obj._compute_qty(cr, uid, move.product_uom.id, move.product_qty, move.product_id.uom_id.id)
            #Check if the entire quantity has been transformed in to quants
            if qty_from_move > product_qty:
                quant_tuples = quant_obj.quants_get(cr, uid, move.location_id.id, move.product_id.id, qty_from_move - product_qty, prodlot_id = move.prodlot_id.id, context=context)
                print quant_tuples
                create_neg_quant = True
                if quant_tuples: 
                    quant_obj.split_and_assign_quants(cr, uid, quant_tuples, move, context=context)
                    product_qty = 0.0
                    #Reread move:
                    move = self.browse(cr, uid, move.id, context=context)
                    for quant in move.reserved_quant_ids:
                        product_qty += quant.qty
                    if qty_from_move <= product_qty:
                        create_neg_quant = False
                if create_neg_quant: 
                    #To solve this, we should create a negative quant at destination and a positive quant at the source
                    vals_neg = {
                        'product_id': move.product_id.id, 
                        'location_id': move.location_id.id, 
                        'qty': -(qty_from_move - product_qty),
                        'in_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            }
                    quant_id_neg = quant_obj.create(cr, uid, vals_neg, context=context)
                    vals_pos = {
                        'product_id': move.product_id.id, 
                        'location_id': move.location_dest_id.id, 
                        'qty': qty_from_move - product_qty,
                        'history_ids': [(4, move.id)], 
                        'propagated_from_id': quant_id_neg, 
                        'in_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            }
                    quant_id_pos = quant_obj.create(cr, uid, vals_pos, context=context)

        return True

    def action_done(self, cr, uid, ids, context=None):
        """ Makes the move done and if all moves are done, it will finish the picking.
        @return:
        """
        picking_ids = []
        move_ids = []
        wf_service = netsvc.LocalService("workflow")
        if context is None:
            context = {}

        todo = []
        for move in self.browse(cr, uid, ids, context=context):
            if move.state=="draft":
                todo.append(move.id)
        if todo:
            self.action_confirm(cr, uid, todo, context=context)
            todo = []

        uom_obj = self.pool.get("product.uom")
        quant_obj = self.pool.get("stock.quant")
        #Do price calc on move
        quants = {}
        for move in self.browse(cr, uid, ids, context=context):
            quants[move.id] = []
            if (move.location_id.usage in ['supplier', 'inventory']):
                #Create quants
                reconciled_quants = self.pool.get("stock.quant").create_quants(cr, uid, move, context=context)
                quants[move.id] += reconciled_quants
            else:
                #move quants should resolve negative quants in destination
                self.check_total_qty(cr, uid, ids, context=context)
                move = self.browse(cr, uid, move.id, context=context)
                reconciled_quants = self.pool.get("stock.quant").move_quants(cr, uid, [x.id for x in move.reserved_quant_ids], move, context=context)
                quants[move.id] += reconciled_quants
                
        #Do price calculation on move -> Should pass reconciled Quants -> is a dictionary 
        matchresults = self.price_calculation(cr, uid, ids, quants, context=context)
        
        for move in self.browse(cr, uid, ids, context=context):
            if move.state in ['done','cancel']:
                continue
            move_ids.append(move.id)

            if move.picking_id:
                picking_ids.append(move.picking_id.id)
            if move.move_dest_id.id and (move.state != 'done'):
                # Downstream move should only be triggered if this move is the last pending upstream move
                other_upstream_move_ids = self.search(cr, uid, [('id','!=',move.id),('state','not in',['done','cancel']),
                                            ('move_dest_id','=',move.move_dest_id.id)], context=context)
                if not other_upstream_move_ids:
                    if move.move_dest_id.state in ('waiting', 'confirmed'):
                        self.force_assign(cr, uid, [move.move_dest_id.id], context=context)
                        #We can take over used quants in this move to be propagated to next move
                        #TODO should take into account split quantities?
                        quants = quant_obj.search(cr, uid, [('history_ids', 'in', move.id), ('location_id', '=', move.location_dest_id.id), ('reservation_id', '=', False)], context=context)
                        if quants: 
                            print "PROPAGATE QUANTS: ", quants
                            quant_obj.write(cr, uid, quants, {'reservation_id':move.move_dest_id.id}, context=context)
                        if move.move_dest_id.picking_id:
                            wf_service.trg_write(uid, 'stock.picking', move.move_dest_id.picking_id.id, cr)
                        if move.move_dest_id.auto_validate:
                            self.action_done(cr, uid, [move.move_dest_id.id], context=context)

            self._create_product_valuation_moves(cr, uid, move, move.id in matchresults and matchresults[move.id] or [], context=context)
            if move.state not in ('confirmed','done','assigned'):
                todo.append(move.id)

        if todo:
            self.action_confirm(cr, uid, todo, context=context)

        self.write(cr, uid, move_ids, {'state': 'done', 'date': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)}, context=context)
        for id in move_ids:
             wf_service.trg_trigger(uid, 'stock.move', id, cr)

        for pick_id in picking_ids:
            wf_service.trg_write(uid, 'stock.picking', pick_id, cr)

        ids = self.pool.get("stock.quant").search(cr, uid, [])
        for x in  self.pool.get("stock.quant").browse(cr, uid, ids):
            print (x.id, x.product_id.id, x.qty, x.price_unit, x.location_id.name, x.in_date)
            print "     ", [(y.id, y.product_qty, y.price_unit) for y in x.history_ids]
        return True

    def _create_account_move_line(self, cr, uid, move, matches, src_account_id, dest_account_id, reference_amount, reference_currency_id, type='', context=None):
        """
        Generate the account.move.line values to post to track the stock valuation difference due to the
        processing of the given stock move.
        """
        move_list = []
        # Consists of access rights 
        # TODO Check if amount_currency is not needed
        match_obj = self.pool.get("stock.move.matching")
        if type == 'out' and move.product_id.cost_method in ['real']:
            for match in match_obj.browse(cr, uid, matches, context=context):
                move_list += [(match.qty, match.qty * match.price_unit_out)]
        elif type == 'in' and move.product_id.cost_method in ['real']:
            move_list = [(move.product_qty, reference_amount)]
        else:
            move_list = [(move.product_qty, reference_amount)]

        res = []
        for item in move_list:
            # prepare default values considering that the destination accounts have the reference_currency_id as their main currency
            partner_id = (move.picking_id.partner_id and self.pool.get('res.partner')._find_accounting_partner(move.picking_id.partner_id).id) or False
            debit_line_vals = {
                        'name': move.name,
                        'product_id': move.product_id and move.product_id.id or False,
                        'quantity': item[0],
                        'product_uom_id': move.product_uom.id, 
                        'ref': move.picking_id and move.picking_id.name or False,
                        'date': time.strftime('%Y-%m-%d'),
                        'partner_id': partner_id,
                        'debit': item[1],
                        'account_id': dest_account_id,
            }
            credit_line_vals = {
                        'name': move.name,
                        'product_id': move.product_id and move.product_id.id or False,
                        'quantity': item[0],
                        'product_uom_id': move.product_uom.id, 
                        'ref': move.picking_id and move.picking_id.name or False,
                        'date': time.strftime('%Y-%m-%d'),
                        'partner_id': partner_id,
                        'credit': item[1],
                        'account_id': src_account_id,
            }
            res += [(0, 0, debit_line_vals), (0, 0, credit_line_vals)]
        return res


    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        ctx = context.copy()
        for move in self.browse(cr, uid, ids, context=context):
            if move.state != 'draft' and not ctx.get('call_unlink', False):
                raise osv.except_osv(_('User Error!'), _('You can only delete draft moves.'))
        return super(stock_move, self).unlink(
            cr, uid, ids, context=ctx)

    # _create_lot function is not used anywhere
    def _create_lot(self, cr, uid, ids, product_id):
        """ Creates production lot
        @return: Production lot id
        """
        prodlot_obj = self.pool.get('stock.production.lot')
        prodlot_id = prodlot_obj.create(cr, uid, {'product_id': product_id})
        return prodlot_id

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
                'prodlot_id': move.prodlot_id.id,
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

    # action_split function is not used anywhere
    # FIXME: deprecate this method
    def action_split(self, cr, uid, ids, quantity, split_by_qty=1, with_lot=True, context=None):
        """ Split Stock Move lines into production lot which specified split by quantity.
        @param cr: the database cursor
        @param uid: the user id
        @param ids: ids of stock move object to be splited
        @param split_by_qty : specify split by qty
        @param with_lot : if true, prodcution lot will assign for split line otherwise not.
        @param context: context arguments
        @return: Splited move lines
        """

        if context is None:
            context = {}
        if quantity <= 0:
            raise osv.except_osv(_('Warning!'), _('Please provide proper quantity.'))

        res = []

        for move in self.browse(cr, uid, ids, context=context):
            if split_by_qty <= 0 or quantity == 0:
                return res

            uos_qty = split_by_qty / move.product_qty * move.product_uos_qty

            quantity_rest = quantity % split_by_qty
            uos_qty_rest = split_by_qty / move.product_qty * move.product_uos_qty

            update_val = {
                'product_qty': split_by_qty,
                'product_uos_qty': uos_qty,
            }
            for idx in range(int(quantity//split_by_qty)):
                if not idx and move.product_qty<=quantity:
                    current_move = move.id
                else:
                    current_move = self.copy(cr, uid, move.id, {'state': move.state})
                res.append(current_move)
                if with_lot:
                    update_val['prodlot_id'] = self._create_lot(cr, uid, [current_move], move.product_id.id)

                self.write(cr, uid, [current_move], update_val)


            if quantity_rest > 0:
                idx = int(quantity//split_by_qty)
                update_val['product_qty'] = quantity_rest
                update_val['product_uos_qty'] = uos_qty_rest
                if not idx and move.product_qty<=quantity:
                    current_move = move.id
                else:
                    current_move = self.copy(cr, uid, move.id, {'state': move.state})

                res.append(current_move)


                if with_lot:
                    update_val['prodlot_id'] = self._create_lot(cr, uid, [current_move], move.product_id.id)

                self.write(cr, uid, [current_move], update_val)
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


    def _generate_negative_stock_matchings(self, cr, uid, ids, product, quants, context=None):
        """
        This method generates the stock move matches for out moves of product with qty remaining
        according to the in move
        force_company should be in context already
        | ids : id of in move
        | product: browse record of product
        Returns: 
        | List of matches
        """
        assert len(ids) == 1, _("Only generate negative stock matchings one by one")
        move = self.browse(cr, uid, ids, context=context)[0]
        cost_method = product.cost_method
        matching_obj = self.pool.get("stock.move.matching")
        product_obj = self.pool.get("product.product")
        uom_obj = self.pool.get("product.uom")
        res = []
#         
#         #Search for the most recent out moves
#         moves = self.search(cr, uid, [('company_id', '=', move.company_id.id), ('state','=', 'done'), ('location_id.usage','=','internal'), ('location_dest_id.usage', '!=', 'internal'), 
#                                           ('product_id', '=', move.product_id.id), ('qty_remaining', '>', 0.0)], order='date, id', context=context)
#         qty_to_go = move.product_qty
#         for out_mov in self.browse(cr, uid, moves, context=context):
#             if qty_to_go <= 0.0:
#                 break
#             out_qty_converted =  uom_obj._compute_qty(cr, uid, out_mov.product_uom.id, out_mov.qty_remaining, move.product_uom.id, round=False)
#             qty = 0.0
#             if out_qty_converted <= qty_to_go:
#                 qty = out_qty_converted
#             elif qty_to_go > 0.0: 
#                 qty = qty_to_go
#             revert_qty = (qty / out_qty_converted) * out_mov.qty_remaining
#             matchvals = {'move_in_id': move.id, 'qty': revert_qty, 
#                          'move_out_id': out_mov.id}
#             match_id = matching_obj.create(cr, uid, matchvals, context=context)
#             res.append(match_id)
#             qty_to_go -= qty
            #Need to re-calculate total price of every out_move if FIFO/LIFO
            #Search out moves from quants
            
        quant_obj = self.pool.get("stock.quant")
        if cost_method in ['real']:
            quants_dict = quant_obj.get_out_moves_from_quants(cr, uid, quants, context=context)
            for out_mov in self.browse(cr, uid, quants_dict.keys(), context=context):
                quants_from_move = quant_obj.search(cr, uid, [('history_ids', 'in', out_mov.id), ('propagated_from_id', '=', False)], context=context)
                out_qty_converted =  uom_obj._compute_qty(cr, uid, out_mov.product_uom.id, out_mov.product_qty, move.product_uom.id, round=False)
                amount = 0.0
                total_price = 0.0
                for qua in quant_obj.browse(cr, uid, quants_from_move, context=context):
                    amount += qua.qty
                    total_price += qua.qty * qua.price_unit
                if amount > 0.0:
                    self.write(cr, uid, [out_mov.id], {'price_unit': total_price / amount}, context=context)
                    if amount >= out_qty_converted:
                        product_obj.write(cr, uid, [product.id], {'standard_price': total_price / amount}, context=context)
        return res

    def price_calculation(self, cr, uid, ids, quants, context=None):
        '''
        This method puts the right price on the stock move, 
        adapts the price on the product when necessary
        and creates the necessary stock move matchings
        :param quants: are quants to be reconciled and needs to be done when IN move reconciles out move
        
        It returns a list of tuples with (move_id, match_id) 
        which is used for generating the accounting entries when FIFO/LIFO
        '''
        product_obj = self.pool.get('product.product')
        currency_obj = self.pool.get('res.currency')
        matching_obj = self.pool.get('stock.move.matching')
        uom_obj = self.pool.get('product.uom')
        quant_obj = self.pool.get('stock.quant')
        
        product_avail = {}
        res = {}
        for move in self.browse(cr, uid, ids, context=context):
            # Initialize variables
            res[move.id] = []
            move_qty = move.product_qty
            move_uom = move.product_uom.id
            company_id = move.company_id.id
            ctx = context.copy()
            user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
            ctx['force_company'] = move.company_id.id
            product = product_obj.browse(cr, uid, move.product_id.id, context=ctx)
            cost_method = product.cost_method
            product_uom_qty = uom_obj._compute_qty(cr, uid, move_uom, move_qty, product.uom_id.id, round=False)
            if not product.id in product_avail:
                product_avail[product.id] = product.qty_available
            
            # Check if out -> do stock move matchings and if fifo/lifo -> update price
            # only update the cost price on the product form on stock moves of type == 'out' because if a valuation has to be made without PO, 
            # for inventories for example we want to use the last value used for an outgoing move
            if move.location_id.usage == 'internal' and move.location_dest_id.usage != 'internal':
                fifo = (cost_method != 'lifo')
                #Ok -> do calculation based on quants
                price_amount = 0.0
                amount = 0.0
                #if move.id in quants???
                #search quants_move which are the quants associated with this move, which are not propagated quants
                quants_move = quant_obj.search(cr, uid, [('history_ids', 'in', move.id), ('propagated_from_id', '=', False)], context=context)
                for quant in quant_obj.browse(cr, uid, quants_move, context=context):
                    price_amount += quant.qty * quant.price_unit
                    amount += quant.qty
                
#                 tuples = product_obj.get_stock_matchings_fifolifo(cr, uid, [product.id], move_qty, fifo, 
#                                                                   move_uom, move.company_id.currency_id.id, context=ctx) #TODO Would be better to use price_currency_id for migration?
#                 price_amount = 0.0
#                 amount = 0.0
#                 #Write stock matchings
#                 for match in tuples: 
#                     matchvals = {'move_in_id': match[0], 'qty': match[1], 
#                                  'move_out_id': move.id}
#                     match_id = matching_obj.create(cr, uid, matchvals, context=context)
#                     res[move.id].append(match_id)
#                     price_amount += match[1] * match[2]
#                     amount += match[1]
                #Write price on out move
                if product_avail[product.id] >= product_uom_qty and product.cost_method in ['real']:
                    if amount > 0:
                        self.write(cr, uid, move.id, {'price_unit': price_amount / move_qty}, context=context) #Should be converted
                        product_obj.write(cr, uid, product.id, {'standard_price': price_amount / amount}, context=ctx) 
                    else:
                        pass
#                         raise osv.except_osv(_('Error'), _("Something went wrong finding quants ")  + str(self.search(cr, uid, [('company_id','=', company_id), ('qty_remaining', '>', 0), ('state', '=', 'done'), 
#                                              ('location_id.usage', '!=', 'internal'), ('location_dest_id.usage', '=', 'internal'), ('product_id', '=', product.id)], 
#                                        order = 'date, id', context=context)) + str(move_qty) + str(move_uom) + str(move.company_id.currency_id.id))
                else:
                    new_price = uom_obj._compute_price(cr, uid, product.uom_id.id, product.standard_price, move_uom)
                    self.write(cr, uid, move.id, {'price_unit': new_price}, context=ctx)
                #Adjust product_avail when not average and move returned from
                if product.cost_method != 'average':
                    product_avail[product.id] -= product_uom_qty
            
            #Check if in => if price 0.0, take standard price / Update price when average price and price on move != standard price
            if move.location_id.usage != 'internal' and move.location_dest_id.usage == 'internal':
                if move.price_unit == 0.0:
                    new_price = uom_obj._compute_price(cr, uid, product.uom_id.id, product.standard_price, move_uom)
                    self.write(cr, uid, move.id, {'price_unit': new_price}, context=ctx)
                elif product.cost_method == 'average':
                    move_product_price = uom_obj._compute_price(cr, uid, move_uom, move.price_unit, product.uom_id.id)
                    if product_avail[product.id] > 0.0:
                        amount_unit = product.standard_price
                        new_std_price = ((amount_unit * product_avail[product.id])\
                                + (move_product_price * product_uom_qty))/(product_avail[product.id] + product_uom_qty)
                    else:
                        new_std_price = move_product_price
                    product_obj.write(cr, uid, [product.id], {'standard_price': new_std_price}, context=ctx)
                # Should create the stock move matchings for previous outs for the negative stock that can be matched with is in
                if product_avail[product.id] < 0.0: #TODO LATER
                    resneg = self._generate_negative_stock_matchings(cr, uid, [move.id], product, quants[move.id], context=ctx)
                    res[move.id] += resneg
                product_avail[product.id] += product_uom_qty
        return res

    # FIXME: needs refactoring, this code is partially duplicated in stock_picking.do_partial()!
    def do_partial(self, cr, uid, ids, partial_datas, context=None):
        """ Makes partial pickings and moves done.
        @param partial_datas: Dictionary containing details of partial picking
                          like partner_id, delivery_date, delivery
                          moves with product_id, product_qty, uom
        """
        res = {}
        picking_obj = self.pool.get('stock.picking')
        product_obj = self.pool.get('product.product')
        currency_obj = self.pool.get('res.currency')
        uom_obj = self.pool.get('product.uom')

        if context is None:
            context = {}

        complete, too_many, too_few = [], [], []
        move_product_qty, prodlot_ids, partial_qty, product_uoms = {}, {}, {}, {}
        

        for move in self.browse(cr, uid, ids, context=context):
            if move.state in ('done', 'cancel'):
                continue
            partial_data = partial_datas.get('move%s'%(move.id), {})
            product_qty = partial_data.get('product_qty',0.0)
            move_product_qty[move.id] = product_qty
            product_uom = partial_data.get('product_uom',False)
            product_price = partial_data.get('product_price',0.0)
            product_currency = partial_data.get('product_currency',False)
            prodlot_id = partial_data.get('prodlot_id')
            prodlot_ids[move.id] = prodlot_id
            product_uoms[move.id] = product_uom
            partial_qty[move.id] = uom_obj._compute_qty(cr, uid, product_uoms[move.id], product_qty, move.product_uom.id)
            if move.product_qty == partial_qty[move.id]:
                complete.append(move)
            elif move.product_qty > partial_qty[move.id]:
                too_few.append(move)
            else:
                too_many.append(move)

        for move in too_few:
            product_qty = move_product_qty[move.id]
            if product_qty != 0:
                defaults = {
                            'product_qty' : product_qty,
                            'product_uos_qty': product_qty,
                            'picking_id' : move.picking_id.id,
                            'state': 'assigned',
                            'move_dest_id': False,
                            'price_unit': product_price,
                            }
                prodlot_id = prodlot_ids[move.id]
                if prodlot_id:
                    defaults.update(prodlot_id=prodlot_id)
                new_move = self.copy(cr, uid, move.id, defaults)
                complete.append(self.browse(cr, uid, new_move))
            self.write(cr, uid, [move.id],
                    {
                        'product_qty': move.product_qty - product_qty,
                        'product_uos_qty': move.product_qty - product_qty,
                        'prodlot_id': False,
                        'tracking_id': False,
                    })


        for move in too_many:
            self.write(cr, uid, [move.id],
                    {
                        'product_qty': move.product_qty,
                        'product_uos_qty': move.product_qty,
                    })
            complete.append(move)

        for move in complete:
            if prodlot_ids.get(move.id):
                self.write(cr, uid, [move.id],{'prodlot_id': prodlot_ids.get(move.id)})
            self.action_done(cr, uid, [move.id], context=context)
            if  move.picking_id.id :
                # TOCHECK : Done picking if all moves are done
                cr.execute("""
                    SELECT move.id FROM stock_picking pick
                    RIGHT JOIN stock_move move ON move.picking_id = pick.id AND move.state = %s
                    WHERE pick.id = %s""",
                            ('done', move.picking_id.id))
                res = cr.fetchall()
                if len(res) == len(move.picking_id.move_lines):
                    picking_obj.action_move(cr, uid, [move.picking_id.id])
                    picking_obj.signal_button_done(cr, uid, [move.picking_id.id])

        return [move.id for move in complete]


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
                product_context.update(uom=line.product_uom.id, to_date=inv.date, date=inv.date, prodlot_id=line.prod_lot_id.id)
                amount = location_obj._product_get(cr, uid, line.location_id.id, [pid], product_context)[pid]
                change = line.product_qty - amount
                lot_id = line.prod_lot_id.id
                if change:
                    location_id = line.product_id.property_stock_inventory.id
                    value = {
                        'name': _('INV:') + (line.inventory_id.name or ''),
                        'product_id': line.product_id.id,
                        'product_uom': line.product_uom.id,
                        'prodlot_id': lot_id,
                        'date': inv.date,
                        'company_id': line.location_id.company_id.id
                    }

                    if change > 0:
                        value.update( {
                            'product_qty': change,
                            'location_id': location_id,
                            'location_dest_id': line.location_id.id,
                        })
                    else:
                        value.update( {
                            'product_qty': -change,
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
        """ Cancels both stock move and inventory
        @return: True
        """
        move_obj = self.pool.get('stock.move')
        account_move_obj = self.pool.get('account.move')
        for inv in self.browse(cr, uid, ids, context=context):
            move_obj.action_cancel(cr, uid, [x.id for x in inv.move_ids], context=context)
            for move in inv.move_ids:
                 account_move_ids = account_move_obj.search(cr, uid, [('name', '=', move.name)])
                 if account_move_ids:
                     account_move_data_l = account_move_obj.read(cr, uid, account_move_ids, ['state'], context=context)
                     for account_move in account_move_data_l:
                         if account_move['state'] == 'posted':
                             raise osv.except_osv(_('User Error!'),
                                                  _('In order to cancel this inventory, you must first unpost related journal entries.'))
                         account_move_obj.unlink(cr, uid, [account_move['id']], context=context)
            self.write(cr, uid, [inv.id], {'state': 'cancel'}, context=context)
        return True


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
        'company_id': fields.related('inventory_id','company_id',type='many2one',relation='res.company',string='Company',store=True, select=True, readonly=True),
        'prod_lot_id': fields.many2one('stock.production.lot', 'Serial Number', domain="[('product_id','=',product_id)]"),
        'state': fields.related('inventory_id','state',type='char',string='Status',readonly=True),
    }

    def _default_stock_location(self, cr, uid, context=None):
        stock_location = self.pool.get('ir.model.data').get_object(cr, uid, 'stock', 'stock_location_stock')
        return stock_location.id

    _defaults = {
        'location_id': _default_stock_location
    }

    def on_change_product_id(self, cr, uid, ids, location_id, product, uom=False, to_date=False):
        """ Changes UoM and name if product_id changes.
        @param location_id: Location id
        @param product: Changed product_id
        @param uom: UoM product
        @return:  Dictionary of changed values
        """
        if not product:
            return {'value': {'product_qty': 0.0, 'product_uom': False, 'prod_lot_id': False}}
        obj_product = self.pool.get('product.product').browse(cr, uid, product)
        uom = uom or obj_product.uom_id.id
        amount = self.pool.get('stock.location')._product_get(cr, uid, location_id, [product], {'uom': uom, 'to_date': to_date, 'compute_child': False})[product]
        result = {'product_qty': amount, 'product_uom': uom, 'prod_lot_id': False}
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
        'lot_input_id': fields.many2one('stock.location', 'Location Input', required=True, domain=[('usage','<>','view')]),
        'lot_stock_id': fields.many2one('stock.location', 'Location Stock', required=True, domain=[('usage','=','internal')]),
        'lot_output_id': fields.many2one('stock.location', 'Location Output', required=True, domain=[('usage','<>','view')]),
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


#----------------------------------------------------------
# "Empty" Classes that are used to vary from the original stock.picking  (that are dedicated to the internal pickings)
#   in order to offer a different usability with different views, labels, available reports/wizards...
#----------------------------------------------------------

# FP Note: do we need all those over rides?
class stock_picking_in(osv.osv):
    _name = "stock.picking.in"
    _inherit = "stock.picking"
    _table = "stock_picking"
    _description = "Incoming Shipments"

    def search(self, cr, user, args, offset=0, limit=None, order=None, context=None, count=False):
        return self.pool.get('stock.picking').search(cr, user, args, offset, limit, order, context, count)

    def read(self, cr, uid, ids, fields=None, context=None, load='_classic_read'):
        return self.pool.get('stock.picking').read(cr, uid, ids, fields=fields, context=context, load=load)

    def check_access_rights(self, cr, uid, operation, raise_exception=True):
        #override in order to redirect the check of acces rights on the stock.picking object
        return self.pool.get('stock.picking').check_access_rights(cr, uid, operation, raise_exception=raise_exception)

    def check_access_rule(self, cr, uid, ids, operation, context=None):
        #override in order to redirect the check of acces rules on the stock.picking object
        return self.pool.get('stock.picking').check_access_rule(cr, uid, ids, operation, context=context)

    def create_workflow(self, cr, uid, ids, context=None):
        # overridden in order to trigger the workflow of stock.picking at the end of create,
        # write and unlink operation instead of its own workflow (which is not existing)
        return self.pool.get('stock.picking').create_workflow(cr, uid, ids, context=context)

    def delete_workflow(self, cr, uid, ids, context=None):
        # overridden in order to trigger the workflow of stock.picking at the end of create,
        # write and unlink operation instead of its own workflow (which is not existing)
        return self.pool.get('stock.picking').delete_workflow(cr, uid, ids, context=context)

    def step_workflow(self, cr, uid, ids, context=None):
        # overridden in order to trigger the workflow of stock.picking at the end of create,
        # write and unlink operation instead of its own workflow (which is not existing)
        return self.pool.get('stock.picking').step_workflow(cr, uid, ids, context=context)

    def signal_workflow(self, cr, uid, ids, signal, context=None):
        # overridden in order to fire the workflow signal on given stock.picking workflow instance
        # instead of its own workflow (which is not existing)
        return self.pool.get('stock.picking').signal_workflow(cr, uid, ids, signal, context=context)

    _columns = {
        'backorder_id': fields.many2one('stock.picking.in', 'Back Order of', states={'done':[('readonly', True)], 'cancel':[('readonly',True)]}, help="If this shipment was split, then this field links to the shipment which contains the already processed part.", select=True),
        'state': fields.selection(
            [('draft', 'Draft'),
            ('auto', 'Waiting Another Operation'),
            ('confirmed', 'Waiting Availability'),
            ('assigned', 'Ready to Receive'),
            ('done', 'Received'),
            ('cancel', 'Cancelled'),],
            'Status', readonly=True, select=True,
            help="""* Draft: not confirmed yet and will not be scheduled until confirmed\n
                 * Waiting Another Operation: waiting for another move to proceed before it becomes automatically available (e.g. in Make-To-Order flows)\n
                 * Waiting Availability: still waiting for the availability of products\n
                 * Ready to Receive: products reserved, simply waiting for confirmation.\n
                 * Received: has been processed, can't be modified or cancelled anymore\n
                 * Cancelled: has been cancelled, can't be confirmed anymore"""),
    }
    _defaults = {
        'type': 'in',
    }

class stock_picking_out(osv.osv):
    _name = "stock.picking.out"
    _inherit = "stock.picking"
    _table = "stock_picking"
    _description = "Delivery Orders"

    def search(self, cr, user, args, offset=0, limit=None, order=None, context=None, count=False):
        return self.pool.get('stock.picking').search(cr, user, args, offset, limit, order, context, count)

    def read(self, cr, uid, ids, fields=None, context=None, load='_classic_read'):
        return self.pool.get('stock.picking').read(cr, uid, ids, fields=fields, context=context, load=load)

    def check_access_rights(self, cr, uid, operation, raise_exception=True):
        #override in order to redirect the check of acces rights on the stock.picking object
        return self.pool.get('stock.picking').check_access_rights(cr, uid, operation, raise_exception=raise_exception)

    def check_access_rule(self, cr, uid, ids, operation, context=None):
        #override in order to redirect the check of acces rules on the stock.picking object
        return self.pool.get('stock.picking').check_access_rule(cr, uid, ids, operation, context=context)

    def create_workflow(self, cr, uid, ids, context=None):
        # overridden in order to trigger the workflow of stock.picking at the end of create,
        # write and unlink operation instead of its own workflow (which is not existing)
        return self.pool.get('stock.picking').create_workflow(cr, uid, ids, context=context)

    def delete_workflow(self, cr, uid, ids, context=None):
        # overridden in order to trigger the workflow of stock.picking at the end of create,
        # write and unlink operation instead of its own workflow (which is not existing)
        return self.pool.get('stock.picking').delete_workflow(cr, uid, ids, context=context)

    def step_workflow(self, cr, uid, ids, context=None):
        # overridden in order to trigger the workflow of stock.picking at the end of create,
        # write and unlink operation instead of its own workflow (which is not existing)
        return self.pool.get('stock.picking').step_workflow(cr, uid, ids, context=context)

    def signal_workflow(self, cr, uid, ids, signal, context=None):
        # overridden in order to fire the workflow signal on given stock.picking workflow instance
        # instead of its own workflow (which is not existing)
        return self.pool.get('stock.picking').signal_workflow(cr, uid, ids, signal, context=context)

    _columns = {
        'backorder_id': fields.many2one('stock.picking.out', 'Back Order of', states={'done':[('readonly', True)], 'cancel':[('readonly',True)]}, help="If this shipment was split, then this field links to the shipment which contains the already processed part.", select=True),
        'state': fields.selection(
            [('draft', 'Draft'),
            ('auto', 'Waiting Another Operation'),
            ('confirmed', 'Waiting Availability'),
            ('assigned', 'Ready to Deliver'),
            ('done', 'Delivered'),
            ('cancel', 'Cancelled'),],
            'Status', readonly=True, select=True,
            help="""* Draft: not confirmed yet and will not be scheduled until confirmed\n
                 * Waiting Another Operation: waiting for another move to proceed before it becomes automatically available (e.g. in Make-To-Order flows)\n
                 * Waiting Availability: still waiting for the availability of products\n
                 * Ready to Deliver: products reserved, simply waiting for confirmation.\n
                 * Delivered: has been processed, can't be modified or cancelled anymore\n
                 * Cancelled: has been cancelled, can't be confirmed anymore"""),
    }
    _defaults = {
        'type': 'out',
    }


# -------------------------
# Packaging related stuff
# -------------------------
class stock_package(osv.osv):
    """
    These are the packages, containing quants and/or others packages
    """
    _name = "stock.quant.package"
    _description = "Physical Packages"
    _columns = {
        'name': fields.char('Package Reference', size=64, select=True),
        'packaging_id': fields.many2one('product.packaging', 'Type of Packaging'),
        'location_id': fields.related('quant_ids', 'location_id', type='many2one', relation='stock.location', string='Location', readonly=True),
        'quant_ids': fields.one2many('stock.quant', 'package_id', 'Bulk Content'),
        'parent_id': fields.many2one('stock.quant.package', 'Container Package', help="The package containing this item"),
        'children_ids': fields.one2many('stock.quant.package', 'parent_id', 'Contained Packages'),

    }
    _defaults = {
        'name': lambda self, cr, uid, context: self.pool.get('ir.sequence').get(cr, uid, 'stock.quant.package') or _('Unknown Pack')
    }
    def _check_location(self, cr, uid, ids, context=None):
        '''checks that all quants in a package are stored in the same location'''
        for pack in self.browse(cr, uid, ids, context=context):
            if not all([quant == pack.quant_ids[0].location_id.id for quant in pack.quant_ids]):
                return False
        return True
    _constraints = [
        (_check_location, 'All quant inside a package should be in the same location', ['location_id']),
    ]

    # FP Note: why not just over ridding the copy method?
    def action_copy(self, cr, uid, ids, context=None):
        stock_operation_obj = self.pool.get('stock.pack.operation')
        #search all the operations of given package
        operation_ids = stock_operation_obj.search(cr, uid, [('result_package_id', 'in', ids)], context=context)
        #create a new empty stock.quant.package
        package_id = self.create(cr, uid, {}, context=context)
        new_ops = []
        #copy all operation and set the newly created package as result_package_id
        for op in operation_ids:
            new_ops += [stock_operation_obj.copy(cr, uid, op, {'result_package_id': package_id, 'quant_ids': []}, context=context)]

    def quants_get(self, cr, uid, package_record, context=None):
        ''' find all the quants in the given package (browse record) recursively'''
        res = []
        for child in package_record.children_ids:
            res += self.quants_get(cr, uid, child, context=context)
        res += [qt.id for qt in package_record.quant_ids]
        return res


class stock_pack_operation(osv.osv):
    _name = "stock.pack.operation"
    _description = "Packing Operation"
    _columns = {
        'picking_id': fields.many2one('stock.picking', 'Stock Picking', help='The stock operation where the packing has been made'),
        'product_id': fields.many2one('product.product', 'Product'),  # 1
        'product_uom': fields.many2one('product.uom', 'Product Unit of Measure'),
        'product_qty': fields.float('Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), required=True),
        'package_id': fields.many2one('stock.quant.package', 'Package'),  # 2
        'quant_id': fields.many2one('stock.quant', 'Quant'),  # 3
        'result_package_id': fields.many2one('stock.quant.package', 'Container Package', help="If set, the operations are packed into this package", required=False, ondelete='cascade'),
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

    def find_packaging_op_from_product(self, cr, uid, product_id, picking_id, context=None):
        #returns all ops that touches this product
        #TOCHECK: don't we need to take only the ops with a result_package_id != False ?
        res = []
        op_ids =  self.search(cr, uid, [('picking_id', '=', picking_id)], context=context)
        for operation in self.browse(cr, uid, op_ids, context=context):
            if operation.product_id and operation.product_id.id == product_id:
                res += [operation.id]
            if operation.quant_id and operation.quant_id.product_id.id == product_id:
                res += [operation.id]
            if operation.package_id:
                all_quants = self.pool.get('stock.quant.package').search(cr, uid, [('parent_id', 'child_of', [operation.package_id.id])], context=context)
                if any([self.pool.get('stock.quant').browse(cr, uid, quant, context=context).product_id.id == product_id for quant in all_quants]):
                    res += [operation.id]
        return res

    def _search_and_increment(self, cr, uid, picking_id, key, context=None):
        '''Search for an operation on an existing key in a picking, if it exists increment the qty (+1) otherwise create it

        :param key: tuple directly reusable in a domain
        context can receive a key 'current_package_id' with the package to consider for this operation
        returns the update to do in stock.move one2many field of picking (adapt remaining quantities) and to the list of package in the classic one2many syntax
                 (0, 0,  { values })    link to a new record that needs to be created with the given values dictionary
                 (1, ID, { values })    update the linked record with id = ID (write *values* on it)
                 (2, ID)                remove and delete the linked record with id = ID (calls unlink on ID, that will delete the object completely, and the link to it as well)
        '''
        stock_move_obj = self.pool.get('stock.move')
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
            todo_on_operations = [(1, operation_id, {'product_qty': qty})]
        else:
            #no existing operation found for the given key and picking => create a new one
            var_name, dummy, value = key
            qty = 1
            values = {
                'picking_id': picking_id,
                var_name: value,
                'product_qty': qty,
                #'product_uom': 1,  # FIXME
            }
            operation_id = self.create(cr, uid, values, context=context)
            values.update({'id': operation_id})
            todo_on_operations = [(0, 0, values)]
        todo_on_moves = []
        product_ids = self._find_product_ids(cr, uid, operation_id, context=context)
        for product_id in product_ids:
            corresponding_move_ids = stock_move_obj.search(cr, uid, [('picking_id', '=', picking_id), ('product_id', '=', product_id)], context=context)
            if corresponding_move_ids:
                corresponding_move = stock_move_obj.browse(cr, uid, corresponding_move_ids[0], context=context)
                todo_on_moves += [(1, corresponding_move.id, {'remaining_qty': corresponding_move.remaining_qty - 1})]
            else:
                #decide what to do
                pass
        return todo_on_moves, todo_on_operations

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
