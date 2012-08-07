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

from osv import osv, fields
from tools.translate import _
import netsvc
import time
import decimal_precision as dp

# Procurement
# ------------------------------------------------------------------
#
# Produce, Buy or Find products and place a move
#     then wizard for picking lists & move
#

class mrp_property_group(osv.osv):
    """
    Group of mrp properties.
    """
    _name = 'mrp.property.group'
    _description = 'Property Group'
    _columns = {
        'name': fields.char('Property Group', size=64, required=True),
        'description': fields.text('Description'),
    }
mrp_property_group()

class mrp_property(osv.osv):
    """
    Properties of mrp.
    """
    _name = 'mrp.property'
    _description = 'Property'
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'composition': fields.selection([('min','min'),('max','max'),('plus','plus')], 'Properties composition', required=True, help="Not used in computations, for information purpose only."),
        'group_id': fields.many2one('mrp.property.group', 'Property Group', required=True),
        'description': fields.text('Description'),
    }
    _defaults = {
        'composition': lambda *a: 'min',
    }
mrp_property()

class StockMove(osv.osv):
    _inherit = 'stock.move'
    _columns= {
        'procurements': fields.one2many('procurement.order', 'move_id', 'Procurements'),
    }

    def copy(self, cr, uid, id, default=None, context=None):
        default = default or {}
        default['procurements'] = []
        return super(StockMove, self).copy(cr, uid, id, default, context=context)

StockMove()

class procurement_order(osv.osv):
    """
    Procurement Orders
    """
    _name = "procurement.order"
    _description = "Procurement"
    _order = 'priority,date_planned desc'
    _inherit = ['mail.thread']
    _log_create = False
    _columns = {
        'name': fields.char('Reason', size=64, required=True, help='Procurement name.'),
        'origin': fields.char('Source Document', size=64,
            help="Reference of the document that created this Procurement.\n"
            "This is automatically completed by OpenERP."),
        'priority': fields.selection([('0','Not urgent'),('1','Normal'),('2','Urgent'),('3','Very Urgent')], 'Priority', required=True, select=True),
        'date_planned': fields.datetime('Scheduled date', required=True, select=True),
        'date_close': fields.datetime('Date Closed'),
        'product_id': fields.many2one('product.product', 'Product', required=True, states={'draft':[('readonly',False)]}, readonly=True),
        'product_qty': fields.float('Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), required=True, states={'draft':[('readonly',False)]}, readonly=True),
        'product_uom': fields.many2one('product.uom', 'Product Unit of Measure', required=True, states={'draft':[('readonly',False)]}, readonly=True),
        'product_uos_qty': fields.float('UoS Quantity', states={'draft':[('readonly',False)]}, readonly=True),
        'product_uos': fields.many2one('product.uom', 'Product UoS', states={'draft':[('readonly',False)]}, readonly=True),
        'move_id': fields.many2one('stock.move', 'Reservation', ondelete='set null'),
        'close_move': fields.boolean('Close Move at end', required=True),
        'location_id': fields.many2one('stock.location', 'Location', required=True, states={'draft':[('readonly',False)]}, readonly=True),
        'procure_method': fields.selection([('make_to_stock','from stock'),('make_to_order','on order')], 'Procurement Method', states={'draft':[('readonly',False)], 'confirmed':[('readonly',False)]},
            readonly=True, required=True, help="If you encode manually a Procurement, you probably want to use" \
            " a make to order method."),

        'note': fields.text('Note'),
        'message': fields.char('Latest error', size=124, help="Exception occurred while computing procurement orders."),
        'state': fields.selection([
            ('draft','Draft'),
            ('cancel','Cancelled'),
            ('confirmed','Confirmed'),
            ('exception','Exception'),
            ('running','Running'),
            ('ready','Ready'),
            ('done','Done'),
            ('waiting','Waiting')], 'Status', required=True,
            help='When a procurement is created the state is set to \'Draft\'.\n If the procurement is confirmed, the state is set to \'Confirmed\'.\
            \nAfter confirming the state is set to \'Running\'.\n If any exception arises in the order then the state is set to \'Exception\'.\n Once the exception is removed the state becomes \'Ready\'.\n It is in \'Waiting\'. state when the procurement is waiting for another one to finish.'),
        'note': fields.text('Note'),
        'company_id': fields.many2one('res.company','Company',required=True),
    }
    _defaults = {
        'state': 'draft',
        'priority': '1',
        'date_planned': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'close_move': 0,
        'procure_method': 'make_to_order',
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'procurement.order', context=c)
    }

    def unlink(self, cr, uid, ids, context=None):
        procurements = self.read(cr, uid, ids, ['state'], context=context)
        unlink_ids = []
        for s in procurements:
            if s['state'] in ['draft','cancel']:
                unlink_ids.append(s['id'])
            else:
                raise osv.except_osv(_('Invalid action !'),
                        _('Cannot delete Procurement Order(s) which are in %s state!') % \
                        s['state'])
        return osv.osv.unlink(self, cr, uid, unlink_ids, context=context)

    def onchange_product_id(self, cr, uid, ids, product_id, context=None):
        """ Finds UoM and UoS of changed product.
        @param product_id: Changed id of product.
        @return: Dictionary of values.
        """
        if product_id:
            w = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
            v = {
                'product_uom': w.uom_id.id,
                'product_uos': w.uos_id and w.uos_id.id or w.uom_id.id
            }
            return {'value': v}
        return {}

    def check_product(self, cr, uid, ids, context=None):
        """ Checks product type.
        @return: True or False
        """
        return all(proc.product_id.type in ('product', 'consu') for proc in self.browse(cr, uid, ids, context=context))

    def check_move_cancel(self, cr, uid, ids, context=None):
        """ Checks if move is cancelled or not.
        @return: True or False.
        """
        return all(procurement.move_id.state == 'cancel' for procurement in self.browse(cr, uid, ids, context=context))

    #This Function is create to avoid  a server side Error Like 'ERROR:tests.mrp:name 'check_move' is not defined'
    def check_move(self, cr, uid, ids, context=None):
        pass

    def check_move_done(self, cr, uid, ids, context=None):
        """ Checks if move is done or not.
        @return: True or False.
        """
        return all(proc.product_id.type == 'service' or (proc.move_id and proc.move_id.state == 'done') \
                    for proc in self.browse(cr, uid, ids, context=context))

    #
    # This method may be overrided by objects that override procurement.order
    # for computing their own purpose
    #
    def _quantity_compute_get(self, cr, uid, proc, context=None):
        """ Finds sold quantity of product.
        @param proc: Current procurement.
        @return: Quantity or False.
        """
        if proc.product_id.type == 'product' and proc.move_id:
            if proc.move_id.product_uos:
                return proc.move_id.product_uos_qty
        return False

    def _uom_compute_get(self, cr, uid, proc, context=None):
        """ Finds UoS if product is Stockable Product.
        @param proc: Current procurement.
        @return: UoS or False.
        """
        if proc.product_id.type == 'product' and proc.move_id:
            if proc.move_id.product_uos:
                return proc.move_id.product_uos.id
        return False

    #
    # Return the quantity of product shipped/produced/served, which may be
    # different from the planned quantity
    #
    def quantity_get(self, cr, uid, id, context=None):
        """ Finds quantity of product used in procurement.
        @return: Quantity of product.
        """
        proc = self.browse(cr, uid, id, context=context)
        result = self._quantity_compute_get(cr, uid, proc, context=context)
        if not result:
            result = proc.product_qty
        return result

    def uom_get(self, cr, uid, id, context=None):
        """ Finds UoM of product used in procurement.
        @return: UoM of product.
        """
        proc = self.browse(cr, uid, id, context=context)
        result = self._uom_compute_get(cr, uid, proc, context=context)
        if not result:
            result = proc.product_uom.id
        return result

    def check_waiting(self, cr, uid, ids, context=None):
        """ Checks state of move.
        @return: True or False
        """
        for procurement in self.browse(cr, uid, ids, context=context):
            if procurement.move_id and procurement.move_id.state == 'auto':
                return True
        return False

    def check_produce_service(self, cr, uid, procurement, context=None):
        return False

    def check_produce_product(self, cr, uid, procurement, context=None):
        """ Finds BoM of a product if not found writes exception message.
        @param procurement: Current procurement.
        @return: True or False.
        """
        return True

    def check_make_to_stock(self, cr, uid, ids, context=None):
        """ Checks product type.
        @return: True or False
        """
        ok = True
        for procurement in self.browse(cr, uid, ids, context=context):
            if procurement.product_id.type == 'service':
                ok = ok and self._check_make_to_stock_service(cr, uid, procurement, context)
            else:
                ok = ok and self._check_make_to_stock_product(cr, uid, procurement, context)
        return ok

    def check_produce(self, cr, uid, ids, context=None):
        """ Checks product type.
        @return: True or False
        """
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        for procurement in self.browse(cr, uid, ids, context=context):
            product = procurement.product_id
            #TOFIX: if product type is 'service' but supply_method is 'buy'.
            if product.supply_method <> 'produce':
                supplier = product.seller_id
                if supplier and user.company_id and user.company_id.partner_id:
                    if supplier.id == user.company_id.partner_id.id:
                        continue
                return False
            if product.type=='service':
                res = self.check_produce_service(cr, uid, procurement, context)
            else:
                res = self.check_produce_product(cr, uid, procurement, context)
            if not res:
                return False
        return True

    def check_buy(self, cr, uid, ids):
        """ Checks product type.
        @return: True or Product Id.
        """
        user = self.pool.get('res.users').browse(cr, uid, uid)
        partner_obj = self.pool.get('res.partner')
        for procurement in self.browse(cr, uid, ids):
            if procurement.product_id.product_tmpl_id.supply_method <> 'buy':
                return False
            if not procurement.product_id.seller_ids:
                message = _('No supplier defined for this product !')
                self.message_append_note(cr, uid, [procurement.id], body=message)
                cr.execute('update procurement_order set message=%s where id=%s', (message, procurement.id))
                return False
            partner = procurement.product_id.seller_id #Taken Main Supplier of Product of Procurement.

            if not partner:
                message = _('No default supplier defined for this product')
                self.message_append_note(cr, uid, [procurement.id], body=message)
                cr.execute('update procurement_order set message=%s where id=%s', (message, procurement.id))
                return False
            if user.company_id and user.company_id.partner_id:
                if partner.id == user.company_id.partner_id.id:
                    return False

            address_id = partner_obj.address_get(cr, uid, [partner.id], ['delivery'])['delivery']
            if not address_id:
                message = _('No address defined for the supplier')
                self.message_append_note(cr, uid, [procurement.id], body=message)
                cr.execute('update procurement_order set message=%s where id=%s', (message, procurement.id))
                return False
        return True

    def test_cancel(self, cr, uid, ids):
        """ Tests whether state of move is cancelled or not.
        @return: True or False
        """
        for record in self.browse(cr, uid, ids):
            if record.move_id and record.move_id.state == 'cancel':
                return True
        return False

    def action_confirm(self, cr, uid, ids, context=None):
        """ Confirms procurement and writes exception message if any.
        @return: True
        """
        move_obj = self.pool.get('stock.move')
        for procurement in self.browse(cr, uid, ids, context=context):
            if procurement.product_qty <= 0.00:
                raise osv.except_osv(_('Insufficient Data!'),
                    _('Please check the quantity in procurement order(s), it should not be 0 or less.'))
            if procurement.product_id.type in ('product', 'consu'):
                if not procurement.move_id:
                    source = procurement.location_id.id
                    if procurement.procure_method == 'make_to_order':
                        source = procurement.product_id.product_tmpl_id.property_stock_procurement.id
                    id = move_obj.create(cr, uid, {
                        'name': procurement.name,
                        'location_id': source,
                        'location_dest_id': procurement.location_id.id,
                        'product_id': procurement.product_id.id,
                        'product_qty': procurement.product_qty,
                        'product_uom': procurement.product_uom.id,
                        'date_expected': procurement.date_planned,
                        'state': 'draft',
                        'company_id': procurement.company_id.id,
                        'auto_validate': True,
                    })
                    move_obj.action_confirm(cr, uid, [id], context=context)
                    self.write(cr, uid, [procurement.id], {'move_id': id, 'close_move': 1})
        self.write(cr, uid, ids, {'state': 'confirmed', 'message': ''})
        self.confirm_send_note(cr, uid, ids, context)
        return True

    def action_move_assigned(self, cr, uid, ids, context=None):
        """ Changes procurement state to Running and writes message.
        @return: True
        """
        message = _('From stock: products assigned.')
        self.write(cr, uid, ids, {'state': 'running',
                'message': message}, context=context)
        self.message_append_note(cr, uid, ids, body=message, context=context)
        self.running_send_note(cr, uid, ids, context=context)
        return True

    def _check_make_to_stock_service(self, cr, uid, procurement, context=None):
        """
           This method may be overrided by objects that override procurement.order
           for computing their own purpose
        @return: True"""
        return True

    def _check_make_to_stock_product(self, cr, uid, procurement, context=None):
        """ Checks procurement move state.
        @param procurement: Current procurement.
        @return: True or move id.
        """
        ok = True
        if procurement.move_id:
            message = False
            id = procurement.move_id.id
            if not (procurement.move_id.state in ('done','assigned','cancel')):
                ok = ok and self.pool.get('stock.move').action_assign(cr, uid, [id])
                order_point_id = self.pool.get('stock.warehouse.orderpoint').search(cr, uid, [('product_id', '=', procurement.product_id.id)], context=context)
                if not order_point_id and not ok:
                     message = _("Not enough stock and no minimum orderpoint rule defined.")
                elif not order_point_id:
                    message = _("No minimum orderpoint rule defined.")
                elif not ok:
                    message = _("Not enough stock.")

                if message:
                    message = _("Procurement '%s' is in exception: ") % (procurement.name) + message
                    cr.execute('update procurement_order set message=%s where id=%s', (message, procurement.id))
                    self.message_append_note(cr, uid, [procurement.id], body=message, context=context)
        return ok

    def action_produce_assign_service(self, cr, uid, ids, context=None):
        """ Changes procurement state to Running.
        @return: True
        """
        for procurement in self.browse(cr, uid, ids, context=context):
            self.write(cr, uid, [procurement.id], {'state': 'running'})
        self.running_send_note(cr, uid, ids, context=None)
        return True

    def action_produce_assign_product(self, cr, uid, ids, context=None):
        """ This is action which call from workflow to assign production order to procurements
        @return: True
        """
        return 0


    def action_po_assign(self, cr, uid, ids, context=None):
        """ This is action which call from workflow to assign purchase order to procurements
        @return: True
        """
        return 0

    def action_cancel(self, cr, uid, ids):
        """ Cancels procurement and writes move state to Assigned.
        @return: True
        """
        todo = []
        todo2 = []
        move_obj = self.pool.get('stock.move')
        for proc in self.browse(cr, uid, ids):
            if proc.close_move and proc.move_id:
                if proc.move_id.state not in ('done', 'cancel'):
                    todo2.append(proc.move_id.id)
            else:
                if proc.move_id and proc.move_id.state == 'waiting':
                    todo.append(proc.move_id.id)
        if len(todo2):
            move_obj.action_cancel(cr, uid, todo2)
        if len(todo):
            move_obj.write(cr, uid, todo, {'state': 'assigned'})
        self.write(cr, uid, ids, {'state': 'cancel'})
        self.cancel_send_note(cr, uid, ids, context=None)
        wf_service = netsvc.LocalService("workflow")
        for id in ids:
            wf_service.trg_trigger(uid, 'procurement.order', id, cr)
        return True

    def action_check_finished(self, cr, uid, ids):
        return self.check_move_done(cr, uid, ids)

    def action_check(self, cr, uid, ids):
        """ Checks procurement move state whether assigned or done.
        @return: True
        """
        ok = False
        for procurement in self.browse(cr, uid, ids):
            if procurement.move_id and procurement.move_id.state == 'assigned' or procurement.move_id.state == 'done':
                self.action_done(cr, uid, [procurement.id])
                ok = True
        return ok

    def action_ready(self, cr, uid, ids):
        """ Changes procurement state to Ready.
        @return: True
        """
        res = self.write(cr, uid, ids, {'state': 'ready'})
        self.ready_send_note(cr, uid, ids, context=None)
        return res

    def action_done(self, cr, uid, ids):
        """ Changes procurement state to Done and writes Closed date.
        @return: True
        """
        move_obj = self.pool.get('stock.move')
        for procurement in self.browse(cr, uid, ids):
            if procurement.move_id:
                if procurement.close_move and (procurement.move_id.state <> 'done'):
                    move_obj.action_done(cr, uid, [procurement.move_id.id])
        res = self.write(cr, uid, ids, {'state': 'done', 'date_close': time.strftime('%Y-%m-%d')})
        self.done_send_note(cr, uid, ids, context=None)
        wf_service = netsvc.LocalService("workflow")
        for id in ids:
            wf_service.trg_trigger(uid, 'procurement.order', id, cr)
        return res

    # ----------------------------------------
    # OpenChatter methods and notifications
    # ----------------------------------------

    def create(self, cr, uid, vals, context=None):
        obj_id = super(procurement_order, self).create(cr, uid, vals, context)
        self.create_send_note(cr, uid, [obj_id], context=context)
        return obj_id

    def create_send_note(self, cr, uid, ids, context=None):
        self.message_append_note(cr, uid, ids, body=_("Procurement has been <b>created</b>."), context=context)

    def confirm_send_note(self, cr, uid, ids, context=None):
        self.message_append_note(cr, uid, ids, body=_("Procurement has been <b>confirmed</b>."), context=context)

    def running_send_note(self, cr, uid, ids, context=None):
        self.message_append_note(cr, uid, ids, body=_("Procurement has been set to <b>running</b>."), context=context)

    def ready_send_note(self, cr, uid, ids, context=None):
        self.message_append_note(cr, uid, ids, body=_("Procurement has been set to <b>ready</b>."), context=context)

    def cancel_send_note(self, cr, uid, ids, context=None):
        self.message_append_note(cr, uid, ids, body=_("Procurement has been <b>cancelled</b>."), context=context)

    def done_send_note(self, cr, uid, ids, context=None):
        self.message_append_note(cr, uid, ids, body=_("Procurement has been <b>done</b>."), context=context)

procurement_order()

class StockPicking(osv.osv):
    _inherit = 'stock.picking'

    def test_finished(self, cursor, user, ids):
        wf_service = netsvc.LocalService("workflow")
        res = super(StockPicking, self).test_finished(cursor, user, ids)
        for picking in self.browse(cursor, user, ids):
            for move in picking.move_lines:
                if move.state == 'done' and move.procurements:
                    for procurement in move.procurements:
                        wf_service.trg_validate(user, 'procurement.order',
                            procurement.id, 'button_check', cursor)
        return res

StockPicking()

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
            procurement_ids = procurement_obj.search(cr, uid , [('state', '=', 'draft'), ('product_id', '=', orderpoint.product_id.id), ('location_id', '=', orderpoint.location_id.id)])
            result[orderpoint.id] = procurement_ids
        return result

    _columns = {
        'name': fields.char('Name', size=32, required=True),
        'active': fields.boolean('Active', help="If the active field is set to False, it will allow you to hide the orderpoint without removing it."),
        'logic': fields.selection([('max','Order to Max'),('price','Best price (not yet active!)')], 'Reordering Mode', required=True),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse', required=True, ondelete="cascade"),
        'location_id': fields.many2one('stock.location', 'Location', required=True, ondelete="cascade"),
        'product_id': fields.many2one('product.product', 'Product', required=True, ondelete='cascade', domain=[('type','=','product')]),
        'product_uom': fields.many2one('product.uom', 'Product Unit of Measure', required=True),
        'product_min_qty': fields.float('Minimum Quantity', required=True,
            help="When the virtual stock goes below the Min Quantity specified for this field, OpenERP generates "\
            "a procurement to bring the virtual stock to the Max Quantity."),
        'product_max_qty': fields.float('Maximum Quantity', required=True,
            help="When the virtual stock goes below the Min Quantity, OpenERP generates "\
            "a procurement to bring the virtual stock to the Quantity specified as Max Quantity."),
        'qty_multiple': fields.integer('Qty Multiple', required=True,
            help="The procurement quantity will be rounded up to this multiple."),
        'procurement_id': fields.many2one('procurement.order', 'Latest procurement', ondelete="set null"),
        'company_id': fields.many2one('res.company','Company',required=True),
        'procurement_draft_ids': fields.function(_get_draft_procurements, type='many2many', relation="procurement.order", \
                                string="Related Procurement Orders",help="Draft procurement of the product and location of that orderpoint"),
    }
    _defaults = {
        'active': lambda *a: 1,
        'logic': lambda *a: 'max',
        'qty_multiple': lambda *a: 1,
        'name': lambda x,y,z,c: x.pool.get('ir.sequence').get(y,z,'stock.orderpoint') or '',
        'product_uom': lambda sel, cr, uid, context: context.get('product_uom', False),
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'stock.warehouse.orderpoint', context=c)
    }
    _sql_constraints = [
        ('qty_multiple_check', 'CHECK( qty_multiple > 0 )', 'Qty Multiple must be greater than zero.'),
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
            v = {'product_uom': prod.uom_id.id}
            return {'value': v}
        return {}

    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        default.update({
            'name': self.pool.get('ir.sequence').get(cr, uid, 'stock.orderpoint') or '',
        })
        return super(stock_warehouse_orderpoint, self).copy(cr, uid, id, default, context=context)

stock_warehouse_orderpoint()

class product_product(osv.osv):
    _inherit="product.product"
    _columns = {
        'orderpoint_ids': fields.one2many('stock.warehouse.orderpoint', 'product_id', 'Minimum Stock Rules'),
    }

product_product()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
