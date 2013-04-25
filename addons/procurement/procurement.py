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
from openerp import netsvc
import time
import openerp.addons.decimal_precision as dp

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

    def copy_data(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default['procurements'] = []
        return super(StockMove, self).copy_data(cr, uid, id, default, context=context)

StockMove()

class procurement_order(osv.osv):
    """
    Procurement Orders
    """
    _name = "procurement.order"
    _description = "Procurement"
    _order = 'priority desc,date_planned'
    _inherit = ['mail.thread']
    _log_create = False
    _columns = {
        'name': fields.text('Description', required=True),
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
        'close_move': fields.boolean('Close Move at end'),
        'location_id': fields.many2one('stock.location', 'Location', required=True, states={'draft':[('readonly',False)]}, readonly=True),
        'procure_method': fields.selection([('make_to_stock','Make to Stock'),('make_to_order','Make to Order')], 'Procurement Method', states={'draft':[('readonly',False)], 'confirmed':[('readonly',False)]},
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
            ('waiting','Waiting')], 'Status', required=True, track_visibility='onchange',
            help='When a procurement is created the status is set to \'Draft\'.\n If the procurement is confirmed, the status is set to \'Confirmed\'.\
            \nAfter confirming the status is set to \'Running\'.\n If any exception arises in the order then the status is set to \'Exception\'.\n Once the exception is removed the status becomes \'Ready\'.\n It is in \'Waiting\'. status when the procurement is waiting for another one to finish.'),
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
                raise osv.except_osv(_('Invalid Action!'),
                        _('Cannot delete Procurement Order(s) which are in %s state.') % \
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

    def is_product(self, cr, uid, ids, context=None):
        """ Checks product type to decide which transition of the workflow to follow.
        @return: True if all product ids received in argument are of type 'product' or 'consummable'. False if any is of type 'service'
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
        """ Depicts the capacity of the procurement workflow to deal with production of services.
            By default, it's False. Overwritten by project_mrp module.
        """
        return False

    def check_produce_product(self, cr, uid, procurement, context=None):
        """ Depicts the capacity of the procurement workflow to deal with production of products.
            By default, it's False. Overwritten by mrp module.
        """
        return False

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
                return False
            if product.type=='service':
                res = self.check_produce_service(cr, uid, procurement, context)
            else:
                res = self.check_produce_product(cr, uid, procurement, context)
            if not res:
                return False
        return True

    def check_buy(self, cr, uid, ids):
        """ Depicts the capacity of the procurement workflow to manage the supply_method == 'buy'.
            By default, it's False. Overwritten by purchase module.
        """
        return False

    def check_conditions_confirm2wait(self, cr, uid, ids):
        """ condition on the transition to go from 'confirm' activity to 'confirm_wait' activity """
        return not self.test_cancel(cr, uid, ids)

    def test_cancel(self, cr, uid, ids):
        """ Tests whether state of move is cancelled or not.
        @return: True or False
        """
        for record in self.browse(cr, uid, ids):
            if record.move_id and record.move_id.state == 'cancel':
                return True
        return False

    #Initialize get_phantom_bom_id method as it is raising an error from yml of mrp_jit
    #when one install first mrp and after that, mrp_jit. get_phantom_bom_id defined in mrp module
    #which is not dependent for mrp_jit.
    def get_phantom_bom_id(self, cr, uid, ids, context=None):
        return False

    def action_confirm(self, cr, uid, ids, context=None):
        """ Confirms procurement and writes exception message if any.
        @return: True
        """
        move_obj = self.pool.get('stock.move')
        for procurement in self.browse(cr, uid, ids, context=context):
            if procurement.product_qty <= 0.00:
                raise osv.except_osv(_('Data Insufficient !'),
                    _('Please check the quantity in procurement order(s) for the product "%s", it should not be 0 or less!' % procurement.product_id.name))
            if procurement.product_id.type in ('product', 'consu'):
                if not procurement.move_id:
                    source = procurement.location_id.id
                    if procurement.procure_method == 'make_to_order':
                        source = procurement.product_id.property_stock_procurement.id
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
        return True

    def action_move_assigned(self, cr, uid, ids, context=None):
        """ Changes procurement state to Running and writes message.
        @return: True
        """
        message = _('Products reserved from stock.')
        self.write(cr, uid, ids, {'state': 'running',
                'message': message}, context=context)
        self.message_post(cr, uid, ids, body=message, context=context)
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
                elif not ok:
                    message = _("Not enough stock.")

                if message:
                    message = _("Procurement '%s' is in exception: ") % (procurement.name) + message
                    #temporary context passed in write to prevent an infinite loop
                    ctx_wkf = dict(context or {})
                    ctx_wkf['workflow.trg_write.%s' % self._name] = False
                    self.write(cr, uid, [procurement.id], {'message': message},context=ctx_wkf)
                    self.message_post(cr, uid, [procurement.id], body=message, context=context)
        return ok

    def _workflow_trigger(self, cr, uid, ids, trigger, context=None):
        """ Don't trigger workflow for the element specified in trigger
        """
        wkf_op_key = 'workflow.%s.%s' % (trigger, self._name)
        if context and not context.get(wkf_op_key, True):
            # make sure we don't have a trigger loop while processing triggers
            return 
        return super(procurement_order,self)._workflow_trigger(cr, uid, ids, trigger, context=context)

    def action_produce_assign_service(self, cr, uid, ids, context=None):
        """ Changes procurement state to Running.
        @return: True
        """
        for procurement in self.browse(cr, uid, ids, context=context):
            self.write(cr, uid, [procurement.id], {'state': 'running'})
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

    # XXX action_cancel() should accept a context argument
    def action_cancel(self, cr, uid, ids):
        """Cancel Procurements and either cancel or assign the related Stock Moves, depending on the procurement configuration.
        
        @return: True
        """
        to_assign = []
        to_cancel = []
        move_obj = self.pool.get('stock.move')
        for proc in self.browse(cr, uid, ids):
            if proc.close_move and proc.move_id:
                if proc.move_id.state not in ('done', 'cancel'):
                    to_cancel.append(proc.move_id.id)
            else:
                if proc.move_id and proc.move_id.state == 'waiting':
                    to_assign.append(proc.move_id.id)
        if len(to_cancel):
            move_obj.action_cancel(cr, uid, to_cancel)
        if len(to_assign):
            move_obj.write(cr, uid, to_assign, {'state': 'assigned'})
        self.write(cr, uid, ids, {'state': 'cancel'})
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
        wf_service = netsvc.LocalService("workflow")
        for id in ids:
            wf_service.trg_trigger(uid, 'procurement.order', id, cr)
        return res

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
        'logic': fields.selection([('max','Order to Max'),('price','Best price (not yet active!)')], 'Reordering Mode', required=True),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse', required=True, ondelete="cascade"),
        'location_id': fields.many2one('stock.location', 'Location', required=True, ondelete="cascade"),
        'product_id': fields.many2one('product.product', 'Product', required=True, ondelete='cascade', domain=[('type','!=','service')]),
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
    _inherit="product.template"

    _columns = {
        'type': fields.selection([('product','Stockable Product'),('consu', 'Consumable'),('service','Service')], 'Product Type', required=True, help="Consumable: Will not imply stock management for this product. \nStockable product: Will imply stock management for this product."),
        'procure_method': fields.selection([('make_to_stock','Make to Stock'),('make_to_order','Make to Order')], 'Procurement Method', required=True, help="Make to Stock: When needed, the product is taken from the stock or we wait for replenishment. \nMake to Order: When needed, the product is purchased or produced."),
        'supply_method': fields.selection([('produce','Manufacture'),('buy','Buy')], 'Supply Method', required=True, help="Manufacture: When procuring the product, a manufacturing order or a task will be generated, depending on the product type. \nBuy: When procuring the product, a purchase order will be generated."),
    }
    _defaults = {
        'procure_method': 'make_to_stock',
        'supply_method': 'buy',
    }

class product_product(osv.osv):
    _inherit="product.product"
    _columns = {
        'orderpoint_ids': fields.one2many('stock.warehouse.orderpoint', 'product_id', 'Minimum Stock Rules'),
    }



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
