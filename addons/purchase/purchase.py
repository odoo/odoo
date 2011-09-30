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

import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

from osv import osv, fields
import netsvc
import pooler
from tools.translate import _
import decimal_precision as dp
from osv.orm import browse_record, browse_null

#
# Model definition
#
class purchase_order(osv.osv):

    def _calc_amount(self, cr, uid, ids, prop, unknow_none, unknow_dict):
        res = {}
        for order in self.browse(cr, uid, ids):
            res[order.id] = 0
            for oline in order.order_line:
                res[order.id] += oline.price_unit * oline.product_qty
        return res

    def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        cur_obj=self.pool.get('res.currency')
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = {
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
                'amount_total': 0.0,
            }
            val = val1 = 0.0
            cur = order.pricelist_id.currency_id
            for line in order.order_line:
               val1 += line.price_subtotal
               for c in self.pool.get('account.tax').compute_all(cr, uid, line.taxes_id, line.price_unit, line.product_qty, order.partner_address_id.id, line.product_id.id, order.partner_id)['taxes']:
                    val += c.get('amount', 0.0)
            res[order.id]['amount_tax']=cur_obj.round(cr, uid, cur, val)
            res[order.id]['amount_untaxed']=cur_obj.round(cr, uid, cur, val1)
            res[order.id]['amount_total']=res[order.id]['amount_untaxed'] + res[order.id]['amount_tax']
        return res

    def _set_minimum_planned_date(self, cr, uid, ids, name, value, arg, context=None):
        if not value: return False
        if type(ids)!=type([]):
            ids=[ids]
        for po in self.browse(cr, uid, ids, context=context):
            if po.order_line:
                cr.execute("""update purchase_order_line set
                        date_planned=%s
                    where
                        order_id=%s and
                        (date_planned=%s or date_planned<%s)""", (value,po.id,po.minimum_planned_date,value))
            cr.execute("""update purchase_order set
                    minimum_planned_date=%s where id=%s""", (value, po.id))
        return True

    def _minimum_planned_date(self, cr, uid, ids, field_name, arg, context=None):
        res={}
        purchase_obj=self.browse(cr, uid, ids, context=context)
        for purchase in purchase_obj:
            res[purchase.id] = False
            if purchase.order_line:
                min_date=purchase.order_line[0].date_planned
                for line in purchase.order_line:
                    if line.date_planned < min_date:
                        min_date=line.date_planned
                res[purchase.id]=min_date
        return res


    def _invoiced_rate(self, cursor, user, ids, name, arg, context=None):
        res = {}
        for purchase in self.browse(cursor, user, ids, context=context):
            tot = 0.0
            for invoice in purchase.invoice_ids:
                if invoice.state not in ('draft','cancel'):
                    tot += invoice.amount_untaxed
            
            if purchase.amount_untaxed:
                res[purchase.id] = min(100.0, tot * 100.0 / (purchase.amount_untaxed))
            else:
                res[purchase.id] = 0.0
        return res

    def _shipped_rate(self, cr, uid, ids, name, arg, context=None):
        if not ids: return {}
        res = {}
        for id in ids:
            res[id] = [0.0,0.0]
        cr.execute('''SELECT
                p.purchase_id,sum(m.product_qty), m.state
            FROM
                stock_move m
            LEFT JOIN
                stock_picking p on (p.id=m.picking_id)
            WHERE
                p.purchase_id IN %s GROUP BY m.state, p.purchase_id''',(tuple(ids),))
        for oid,nbr,state in cr.fetchall():
            if state=='cancel':
                continue
            if state=='done':
                res[oid][0] += nbr or 0.0
                res[oid][1] += nbr or 0.0
            else:
                res[oid][1] += nbr or 0.0
        for r in res:
            if not res[r][1]:
                res[r] = 0.0
            else:
                res[r] = 100.0 * res[r][0] / res[r][1]
        return res

    def _get_order(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('purchase.order.line').browse(cr, uid, ids, context=context):
            result[line.order_id.id] = True
        return result.keys()

    def _invoiced(self, cursor, user, ids, name, arg, context=None):
        res = {}
        for purchase in self.browse(cursor, user, ids, context=context):
            invoiced = False
            if purchase.invoiced_rate == 100.00:
                invoiced = True
            res[purchase.id] = invoiced
        return res

    STATE_SELECTION = [
        ('draft', 'Request for Quotation'),
        ('wait', 'Waiting'),
        ('confirmed', 'Waiting Approval'),
        ('approved', 'Approved'),
        ('except_picking', 'Shipping Exception'),
        ('except_invoice', 'Invoice Exception'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ]

    _columns = {
        'name': fields.char('Order Reference', size=64, required=True, select=True, help="unique number of the purchase order,computed automatically when the purchase order is created"),
        'origin': fields.char('Source Document', size=64,
            help="Reference of the document that generated this purchase order request."
        ),
        'partner_ref': fields.char('Supplier Reference', states={'confirmed':[('readonly',True)], 'approved':[('readonly',True)],'done':[('readonly',True)]}, size=64),
        'date_order':fields.date('Date Ordered', required=True, states={'confirmed':[('readonly',True)], 'approved':[('readonly',True)]}, select=True, help="Date on which this document has been created."),
        'date_approve':fields.date('Date Approved', readonly=1, select=True, help="Date on which purchase order has been approved"),
        'partner_id':fields.many2one('res.partner', 'Supplier', required=True, states={'confirmed':[('readonly',True)], 'approved':[('readonly',True)],'done':[('readonly',True)]}, change_default=True),
        'partner_address_id':fields.many2one('res.partner.address', 'Address', required=True,
            states={'confirmed':[('readonly',True)], 'approved':[('readonly',True)],'done':[('readonly',True)]},domain="[('partner_id', '=', partner_id)]"),
        'dest_address_id':fields.many2one('res.partner.address', 'Destination Address',
            states={'confirmed':[('readonly',True)], 'approved':[('readonly',True)],'done':[('readonly',True)]},
            help="Put an address if you want to deliver directly from the supplier to the customer." \
                "In this case, it will remove the warehouse link and set the customer location."
        ),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse', states={'confirmed':[('readonly',True)], 'approved':[('readonly',True)],'done':[('readonly',True)]}),
        'location_id': fields.many2one('stock.location', 'Destination', required=True, domain=[('usage','<>','view')]),
        'pricelist_id':fields.many2one('product.pricelist', 'Pricelist', required=True, states={'confirmed':[('readonly',True)], 'approved':[('readonly',True)],'done':[('readonly',True)]}, help="The pricelist sets the currency used for this purchase order. It also computes the supplier price for the selected products/quantities."),
        'state': fields.selection(STATE_SELECTION, 'State', readonly=True, help="The state of the purchase order or the quotation request. A quotation is a purchase order in a 'Draft' state. Then the order has to be confirmed by the user, the state switch to 'Confirmed'. Then the supplier must confirm the order to change the state to 'Approved'. When the purchase order is paid and received, the state becomes 'Done'. If a cancel action occurs in the invoice or in the reception of goods, the state becomes in exception.", select=True),
        'order_line': fields.one2many('purchase.order.line', 'order_id', 'Order Lines', states={'approved':[('readonly',True)],'done':[('readonly',True)]}),
        'validator' : fields.many2one('res.users', 'Validated by', readonly=True),
        'notes': fields.text('Notes'),
        'invoice_ids': fields.many2many('account.invoice', 'purchase_invoice_rel', 'purchase_id', 'invoice_id', 'Invoices', help="Invoices generated for a purchase order"),
        'picking_ids': fields.one2many('stock.picking', 'purchase_id', 'Picking List', readonly=True, help="This is the list of picking list that have been generated for this purchase"),
        'shipped':fields.boolean('Received', readonly=True, select=True, help="It indicates that a picking has been done"),
        'shipped_rate': fields.function(_shipped_rate, method=True, string='Received', type='float'),
        'invoiced': fields.function(_invoiced, method=True, string='Invoiced & Paid', type='boolean', help="It indicates that an invoice has been paid"),
        'invoiced_rate': fields.function(_invoiced_rate, method=True, string='Invoiced', type='float'),
        'invoice_method': fields.selection([('manual','Manual'),('order','From Order'),('picking','From Picking')], 'Invoicing Control', required=True,
            help="From Order: a draft invoice will be pre-generated based on the purchase order. The accountant " \
                "will just have to validate this invoice for control.\n" \
                "From Picking: a draft invoice will be pre-generated based on validated receptions.\n" \
                "Manual: allows you to generate suppliers invoices by chosing in the uninvoiced lines of all manual purchase orders."
        ),
        'minimum_planned_date':fields.function(_minimum_planned_date, fnct_inv=_set_minimum_planned_date, method=True, string='Expected Date', type='date', select=True, help="This is computed as the minimum scheduled date of all purchase order lines' products.",
            store = {
                'purchase.order.line': (_get_order, ['date_planned'], 10),
            }
        ),
        'amount_untaxed': fields.function(_amount_all, method=True, digits_compute= dp.get_precision('Purchase Price'), string='Untaxed Amount',
            store={
                'purchase.order.line': (_get_order, None, 10),
            }, multi="sums", help="The amount without tax"),
        'amount_tax': fields.function(_amount_all, method=True, digits_compute= dp.get_precision('Purchase Price'), string='Taxes',
            store={
                'purchase.order.line': (_get_order, None, 10),
            }, multi="sums", help="The tax amount"),
        'amount_total': fields.function(_amount_all, method=True, digits_compute= dp.get_precision('Purchase Price'), string='Total',
            store={
                'purchase.order.line': (_get_order, None, 10),
            }, multi="sums",help="The total amount"),
        'fiscal_position': fields.many2one('account.fiscal.position', 'Fiscal Position'),
        'product_id': fields.related('order_line','product_id', type='many2one', relation='product.product', string='Product'),
        'create_uid':  fields.many2one('res.users', 'Responsible'),
        'company_id': fields.many2one('res.company','Company',required=True,select=1),
    }
    _defaults = {
        'date_order': lambda *a: time.strftime('%Y-%m-%d'),
        'state': 'draft',
        'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'purchase.order'),
        'shipped': 0,
        'invoice_method': 'order',
        'invoiced': 0,
        'partner_address_id': lambda self, cr, uid, context: context.get('partner_id', False) and self.pool.get('res.partner').address_get(cr, uid, [context['partner_id']], ['default'])['default'],
        'pricelist_id': lambda self, cr, uid, context: context.get('partner_id', False) and self.pool.get('res.partner').browse(cr, uid, context['partner_id']).property_product_pricelist_purchase.id,
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'purchase.order', context=c),
    }
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Order Reference must be unique !'),
    ]
    _name = "purchase.order"
    _description = "Purchase Order"
    _order = "name desc"

    def unlink(self, cr, uid, ids, context=None):
        purchase_orders = self.read(cr, uid, ids, ['state'], context=context)
        unlink_ids = []
        for s in purchase_orders:
            if s['state'] in ['draft','cancel']:
                unlink_ids.append(s['id'])
            else:
                raise osv.except_osv(_('Invalid action !'), _('Cannot delete Purchase Order(s) which are in %s State!')  % _(dict(purchase_order.STATE_SELECTION).get(s['state'])))

        # TODO: temporary fix in 5.0, to remove in 5.2 when subflows support
        # automatically sending subflow.delete upon deletion
        wf_service = netsvc.LocalService("workflow")
        for id in unlink_ids:
            wf_service.trg_validate(uid, 'purchase.order', id, 'purchase_cancel', cr)

        return super(purchase_order, self).unlink(cr, uid, unlink_ids, context=context)

    def button_dummy(self, cr, uid, ids, context=None):
        return True

    def onchange_dest_address_id(self, cr, uid, ids, adr_id):
        if not adr_id:
            return {}
        values = {'warehouse_id': False}
        part_id = self.pool.get('res.partner.address').browse(cr, uid, adr_id).partner_id
        if part_id:
            loc_id = part_id.property_stock_customer.id
            values.update({'location_id': loc_id})
        return {'value':values}

    def onchange_warehouse_id(self, cr, uid, ids, warehouse_id):
        if not warehouse_id:
            return {}
        res = self.pool.get('stock.warehouse').read(cr, uid, [warehouse_id], ['lot_input_id'])[0]['lot_input_id'][0]
        return {'value':{'location_id': res, 'dest_address_id': False}}

    def onchange_partner_id(self, cr, uid, ids, part):

        if not part:
            return {'value':{'partner_address_id': False, 'fiscal_position': False}}
        addr = self.pool.get('res.partner').address_get(cr, uid, [part], ['default'])
        part = self.pool.get('res.partner').browse(cr, uid, part)
        pricelist = part.property_product_pricelist_purchase.id
        fiscal_position = part.property_account_position and part.property_account_position.id or False
        return {'value':{'partner_address_id': addr['default'], 'pricelist_id': pricelist, 'fiscal_position': fiscal_position}}

    def wkf_approve_order(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'approved', 'date_approve': time.strftime('%Y-%m-%d')})
        return True

    #TODO: implement messages system
    def wkf_confirm_order(self, cr, uid, ids, context=None):
        todo = []
        for po in self.browse(cr, uid, ids, context=context):
            if not po.order_line:
                raise osv.except_osv(_('Error !'),_('You can not confirm purchase order without Purchase Order Lines.'))
            for line in po.order_line:
                if line.state=='draft':
                    todo.append(line.id)
            message = _("Purchase order '%s' is confirmed.") % (po.name,)
            self.log(cr, uid, po.id, message)
#        current_name = self.name_get(cr, uid, ids)[0][1]
        self.pool.get('purchase.order.line').action_confirm(cr, uid, todo, context)
        for id in ids:
            self.write(cr, uid, [id], {'state' : 'confirmed', 'validator' : uid})
        return True

    def wkf_warn_buyer(self, cr, uid, ids):
        self.write(cr, uid, ids, {'state' : 'wait', 'validator' : uid})
        request = pooler.get_pool(cr.dbname).get('res.request')
        for po in self.browse(cr, uid, ids):
            managers = []
            for oline in po.order_line:
                manager = oline.product_id.product_manager
                if manager and not (manager.id in managers):
                    managers.append(manager.id)
            for manager_id in managers:
                request.create(cr, uid,{
                       'name' : _("Purchase amount over the limit"),
                       'act_from' : uid,
                       'act_to' : manager_id,
                       'body': _('Somebody has just confirmed a purchase with an amount over the defined limit'),
                       'ref_partner_id': po.partner_id.id,
                       'ref_doc1': 'purchase.order,%d' % (po.id,),
                })
    def inv_line_create(self, cr, uid, a, ol):
        return (0, False, {
            'name': ol.name,
            'account_id': a,
            'price_unit': ol.price_unit or 0.0,
            'quantity': ol.product_qty,
            'product_id': ol.product_id.id or False,
            'uos_id': ol.product_uom.id or False,
            'invoice_line_tax_id': [(6, 0, [x.id for x in ol.taxes_id])],
            'account_analytic_id': ol.account_analytic_id.id or False,
        })

    def action_cancel_draft(self, cr, uid, ids, *args):
        if not len(ids):
            return False
        self.write(cr, uid, ids, {'state':'draft','shipped':0})
        wf_service = netsvc.LocalService("workflow")
        for p_id in ids:
            # Deleting the existing instance of workflow for PO
            wf_service.trg_delete(uid, 'purchase.order', p_id, cr)
            wf_service.trg_create(uid, 'purchase.order', p_id, cr)
        for (id,name) in self.name_get(cr, uid, ids):
            message = _("Purchase order '%s' has been set in draft state.") % name
            self.log(cr, uid, id, message)
        return True

    def action_invoice_create(self, cr, uid, ids, *args):
        res = False
        property_obj = self.pool.get('ir.property')
        fp_obj =  self.pool.get('account.fiscal.position')
        journal_obj = self.pool.get('account.journal')
        for o in self.browse(cr, uid, ids):
            il = []
            todo = []
            for ol in o.order_line:
                todo.append(ol.id)
                if ol.product_id:
                    acc_id = ol.product_id.product_tmpl_id.property_account_expense.id
                    if not acc_id:
                        acc_id = ol.product_id.categ_id.property_account_expense_categ.id
                    if not acc_id:
                        raise osv.except_osv(_('Error !'), _('There is no expense account defined for this product: "%s" (id:%d)') % (ol.product_id.name, ol.product_id.id,))
                else:
                    prop = property_obj.get(cr, uid, 'property_account_expense_categ', 'product.category')
                    acc_id = prop and prop.id or False
                fpos = o.fiscal_position or False
                acc_id = fp_obj.map_account(cr, uid, fpos, acc_id)
                if not acc_id:
                    raise osv.except_osv(_('Error !'),
                        _('There is no expense account defined in default Properties for Product Category or Fiscal Position is not defined !'))
                il.append(self.inv_line_create(cr, uid, acc_id, ol))

            acc_id = o.partner_id.property_account_payable.id
            journal_ids = journal_obj.search(cr, uid, [('type', '=','purchase'),('company_id', '=', o.company_id.id)], limit=1)
            if not journal_ids:
                raise osv.except_osv(_('Error !'),
                    _('There is no purchase journal defined for this company: "%s" (id:%d)') % (o.company_id.name, o.company_id.id))
            inv = {
                'name': o.partner_ref or o.name,
                'reference': o.partner_ref or o.name,
                'account_id': acc_id,
                'type': 'in_invoice',
                'partner_id': o.partner_id.id,
                'currency_id': o.pricelist_id.currency_id.id,
                'address_invoice_id': o.partner_address_id.id,
                'address_contact_id': o.partner_address_id.id,
                'journal_id': len(journal_ids) and journal_ids[0] or False,
                'origin': o.name,
                'invoice_line': il,
                'fiscal_position': o.fiscal_position.id or o.partner_id.property_account_position.id,
                'payment_term': o.partner_id.property_payment_term and o.partner_id.property_payment_term.id or False,
                'company_id': o.company_id.id,
            }
            inv_id = self.pool.get('account.invoice').create(cr, uid, inv, {'type':'in_invoice', 'journal_type': 'purchase'})
            self.pool.get('account.invoice').button_compute(cr, uid, [inv_id], {'type':'in_invoice'}, set_total=True)
            self.pool.get('purchase.order.line').write(cr, uid, todo, {'invoiced':True})
            self.write(cr, uid, [o.id], {'invoice_ids': [(4, inv_id)]})
            res = inv_id
        return res

    def has_stockable_product(self,cr, uid, ids, *args):
        for order in self.browse(cr, uid, ids):
            for order_line in order.order_line:
                if order_line.product_id and order_line.product_id.product_tmpl_id.type in ('product', 'consu'):
                    return True
        return False

    def action_cancel(self, cr, uid, ids, context=None):
        for purchase in self.browse(cr, uid, ids, context=context):
            for pick in purchase.picking_ids:
                if pick.state not in ('draft','cancel'):
                    raise osv.except_osv(
                        _('Could not cancel purchase order !'),
                        _('You must first cancel all picking attached to this purchase order.'))
            for pick in purchase.picking_ids:
                wf_service = netsvc.LocalService("workflow")
                wf_service.trg_validate(uid, 'stock.picking', pick.id, 'button_cancel', cr)
            for inv in purchase.invoice_ids:
                if inv and inv.state not in ('cancel','draft'):
                    raise osv.except_osv(
                        _('Could not cancel this purchase order !'),
                        _('You must first cancel all invoices attached to this purchase order.'))
                if inv:
                    wf_service = netsvc.LocalService("workflow")
                    wf_service.trg_validate(uid, 'account.invoice', inv.id, 'invoice_cancel', cr)
        self.write(cr,uid,ids,{'state':'cancel'})
        for (id,name) in self.name_get(cr, uid, ids):
            message = _("Purchase order '%s' is cancelled.") % name
            self.log(cr, uid, id, message)
        return True

    def action_picking_create(self,cr, uid, ids, *args):
        picking_id = False
        for order in self.browse(cr, uid, ids):
            loc_id = order.partner_id.property_stock_supplier.id
            istate = 'none'
            if order.invoice_method=='picking':
                istate = '2binvoiced'
            pick_name = self.pool.get('ir.sequence').get(cr, uid, 'stock.picking.in')
            picking_id = self.pool.get('stock.picking').create(cr, uid, {
                'name': pick_name,
                'origin': order.name+((order.origin and (':'+order.origin)) or ''),
                'type': 'in',
                'address_id': order.dest_address_id.id or order.partner_address_id.id,
                'invoice_state': istate,
                'purchase_id': order.id,
                'company_id': order.company_id.id,
                'move_lines' : [],
            })
            todo_moves = []
            for order_line in order.order_line:
                if not order_line.product_id:
                    continue
                if order_line.product_id.product_tmpl_id.type in ('product', 'consu'):
                    dest = order.location_id.id
                    move = self.pool.get('stock.move').create(cr, uid, {
                        'name': order.name + ': ' +(order_line.name or ''),
                        'product_id': order_line.product_id.id,
                        'product_qty': order_line.product_qty,
                        'product_uos_qty': order_line.product_qty,
                        'product_uom': order_line.product_uom.id,
                        'product_uos': order_line.product_uom.id,
                        'date': order_line.date_planned,
                        'date_expected': order_line.date_planned,
                        'location_id': loc_id,
                        'location_dest_id': dest,
                        'picking_id': picking_id,
                        'move_dest_id': order_line.move_dest_id.id,
                        'state': 'draft',
                        'purchase_line_id': order_line.id,
                        'company_id': order.company_id.id,
                        'price_unit': order_line.price_unit
                    })
                    if order_line.move_dest_id:
                        self.pool.get('stock.move').write(cr, uid, [order_line.move_dest_id.id], {'location_id':order.location_id.id})
                    todo_moves.append(move)
            self.pool.get('stock.move').action_confirm(cr, uid, todo_moves)
            self.pool.get('stock.move').force_assign(cr, uid, todo_moves)
            wf_service = netsvc.LocalService("workflow")
            wf_service.trg_validate(uid, 'stock.picking', picking_id, 'button_confirm', cr)
        return picking_id

    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        default.update({
            'state':'draft',
            'shipped':False,
            'invoiced':False,
            'invoice_ids': [],
            'picking_ids': [],
            'name': self.pool.get('ir.sequence').get(cr, uid, 'purchase.order'),
        })
        return super(purchase_order, self).copy(cr, uid, id, default, context)


    def do_merge(self, cr, uid, ids, context=None):
        """
        To merge similar type of purchase orders.
        Orders will only be merged if:
        * Purchase Orders are in draft
        * Purchase Orders belong to the same partner
        * Purchase Orders are have same stock location, same pricelist
        Lines will only be merged if:
        * Order lines are exactly the same except for the quantity and unit

         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param ids: the ID or list of IDs
         @param context: A standard dictionary

         @return: new purchase order id

        """
        wf_service = netsvc.LocalService("workflow")
        def make_key(br, fields):
            list_key = []
            for field in fields:
                field_val = getattr(br, field)
                if field in ('product_id', 'move_dest_id', 'account_analytic_id'):
                    if not field_val:
                        field_val = False
                if isinstance(field_val, browse_record):
                    field_val = field_val.id
                elif isinstance(field_val, browse_null):
                    field_val = False
                elif isinstance(field_val, list):
                    field_val = ((6, 0, tuple([v.id for v in field_val])),)
                list_key.append((field, field_val))
            list_key.sort()
            return tuple(list_key)

    # compute what the new orders should contain

        new_orders = {}

        for porder in [order for order in self.browse(cr, uid, ids, context=context) if order.state == 'draft']:
            order_key = make_key(porder, ('partner_id', 'location_id', 'pricelist_id'))
            new_order = new_orders.setdefault(order_key, ({}, []))
            new_order[1].append(porder.id)
            order_infos = new_order[0]
            if not order_infos:
                order_infos.update({
                    'origin': porder.origin,
                    'date_order': time.strftime('%Y-%m-%d'),
                    'partner_id': porder.partner_id.id,
                    'partner_address_id': porder.partner_address_id.id,
                    'dest_address_id': porder.dest_address_id.id,
                    'warehouse_id': porder.warehouse_id.id,
                    'location_id': porder.location_id.id,
                    'pricelist_id': porder.pricelist_id.id,
                    'state': 'draft',
                    'order_line': {},
                    'notes': '%s' % (porder.notes or '',),
                    'fiscal_position': porder.fiscal_position and porder.fiscal_position.id or False,
                })
            else:
                if porder.notes:
                    order_infos['notes'] = (order_infos['notes'] or '') + ('\n%s' % (porder.notes,))
                if porder.origin:
                    order_infos['origin'] = (order_infos['origin'] or '') + ' ' + porder.origin

            for order_line in porder.order_line:
                line_key = make_key(order_line, ('name', 'date_planned', 'taxes_id', 'price_unit', 'notes', 'product_id', 'move_dest_id', 'account_analytic_id'))
                o_line = order_infos['order_line'].setdefault(line_key, {})
                if o_line:
                    # merge the line with an existing line
                    o_line['product_qty'] += order_line.product_qty * order_line.product_uom.factor / o_line['uom_factor']
                else:
                    # append a new "standalone" line
                    for field in ('product_qty', 'product_uom'):
                        field_val = getattr(order_line, field)
                        if isinstance(field_val, browse_record):
                            field_val = field_val.id
                        o_line[field] = field_val
                    o_line['uom_factor'] = order_line.product_uom and order_line.product_uom.factor or 1.0



        allorders = []
        orders_info = {}
        for order_key, (order_data, old_ids) in new_orders.iteritems():
            # skip merges with only one order
            if len(old_ids) < 2:
                allorders += (old_ids or [])
                continue

            # cleanup order line data
            for key, value in order_data['order_line'].iteritems():
                del value['uom_factor']
                value.update(dict(key))
            order_data['order_line'] = [(0, 0, value) for value in order_data['order_line'].itervalues()]

            # create the new order
            neworder_id = self.create(cr, uid, order_data)
            orders_info.update({neworder_id: old_ids})
            allorders.append(neworder_id)

            # make triggers pointing to the old orders point to the new order
            for old_id in old_ids:
                wf_service.trg_redirect(uid, 'purchase.order', old_id, neworder_id, cr)
                wf_service.trg_validate(uid, 'purchase.order', old_id, 'purchase_cancel', cr)
        return orders_info

purchase_order()

class purchase_order_line(osv.osv):
    def _amount_line(self, cr, uid, ids, prop, arg, context=None):
        res = {}
        cur_obj=self.pool.get('res.currency')
        tax_obj = self.pool.get('account.tax')
        for line in self.browse(cr, uid, ids, context=context):
            taxes = tax_obj.compute_all(cr, uid, line.taxes_id, line.price_unit, line.product_qty)
            cur = line.order_id.pricelist_id.currency_id
            res[line.id] = cur_obj.round(cr, uid, cur, taxes['total'])
        return res

    _columns = {
        'name': fields.char('Description', size=256, required=True),
        'product_qty': fields.float('Quantity', required=True, digits=(16,2)),
        'date_planned': fields.date('Scheduled Date', required=True, select=True),
        'taxes_id': fields.many2many('account.tax', 'purchase_order_taxe', 'ord_id', 'tax_id', 'Taxes'),
        'product_uom': fields.many2one('product.uom', 'Product UOM', required=True),
        'product_id': fields.many2one('product.product', 'Product', domain=[('purchase_ok','=',True)], change_default=True),
        'move_ids': fields.one2many('stock.move', 'purchase_line_id', 'Reservation', readonly=True, ondelete='set null'),
        'move_dest_id': fields.many2one('stock.move', 'Reservation Destination', ondelete='set null'),
        'price_unit': fields.float('Unit Price', required=True, digits_compute= dp.get_precision('Purchase Price')),
        'price_subtotal': fields.function(_amount_line, method=True, string='Subtotal', digits_compute= dp.get_precision('Purchase Price')),
        'notes': fields.text('Notes'),
        'order_id': fields.many2one('purchase.order', 'Order Reference', select=True, required=True, ondelete='cascade'),
        'account_analytic_id':fields.many2one('account.analytic.account', 'Analytic Account',),
        'company_id': fields.related('order_id','company_id',type='many2one',relation='res.company',string='Company', store=True, readonly=True),
        'state': fields.selection([('draft', 'Draft'), ('confirmed', 'Confirmed'), ('done', 'Done'), ('cancel', 'Cancelled')], 'State', required=True, readonly=True,
                                  help=' * The \'Draft\' state is set automatically when purchase order in draft state. \
                                       \n* The \'Confirmed\' state is set automatically as confirm when purchase order in confirm state. \
                                       \n* The \'Done\' state is set automatically when purchase order is set as done. \
                                       \n* The \'Cancelled\' state is set automatically when user cancel purchase order.'),
        'invoice_lines': fields.many2many('account.invoice.line', 'purchase_order_line_invoice_rel', 'order_line_id', 'invoice_id', 'Invoice Lines', readonly=True),
        'invoiced': fields.boolean('Invoiced', readonly=True),
        'partner_id': fields.related('order_id','partner_id',string='Partner',readonly=True,type="many2one", relation="res.partner", store=True),
        'date_order': fields.related('order_id','date_order',string='Order Date',readonly=True,type="date")

    }
    _defaults = {
        'product_qty': lambda *a: 1.0,
        'state': lambda *args: 'draft',
        'invoiced': lambda *a: 0,
    }
    _table = 'purchase_order_line'
    _name = 'purchase.order.line'
    _description = 'Purchase Order Line'

    def copy_data(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        default.update({'state':'draft', 'move_ids':[],'invoiced':0,'invoice_lines':[]})
        return super(purchase_order_line, self).copy_data(cr, uid, id, default, context)

    def product_id_change(self, cr, uid, ids, pricelist, product, qty, uom,
            partner_id, date_order=False, fiscal_position=False, date_planned=False,
            name=False, price_unit=False, notes=False):
        if not pricelist:
            raise osv.except_osv(_('No Pricelist !'), _('You have to select a pricelist or a supplier in the purchase form !\nPlease set one before choosing a product.'))
        if not  partner_id:
            raise osv.except_osv(_('No Partner!'), _('You have to select a partner in the purchase form !\nPlease set one partner before choosing a product.'))
        if not product:
            return {'value': {'price_unit': price_unit or 0.0, 'name': name or '',
                'notes': notes or'', 'product_uom' : uom or False}, 'domain':{'product_uom':[]}}
        res = {}
        prod= self.pool.get('product.product').browse(cr, uid, product)

        product_uom_pool = self.pool.get('product.uom')
        lang=False
        if partner_id:
            lang=self.pool.get('res.partner').read(cr, uid, partner_id, ['lang'])['lang']
        context={'lang':lang}
        context['partner_id'] = partner_id

        prod = self.pool.get('product.product').browse(cr, uid, product, context=context)
        prod_uom_po = prod.uom_po_id.id
        if not uom:
            uom = prod_uom_po
        if not date_order:
            date_order = time.strftime('%Y-%m-%d')
        qty = qty or 1.0
        seller_delay = 0

        prod_name = self.pool.get('product.product').name_get(cr, uid, [prod.id], context=context)[0][1]
        res = {}
        for s in prod.seller_ids:
            if s.name.id == partner_id:
                seller_delay = s.delay
                if s.product_uom:
                    temp_qty = product_uom_pool._compute_qty(cr, uid, s.product_uom.id, s.min_qty, to_uom_id=prod.uom_id.id)
                    uom = s.product_uom.id #prod_uom_po
                temp_qty = s.min_qty # supplier _qty assigned to temp
                if qty < temp_qty: # If the supplier quantity is greater than entered from user, set minimal.
                    qty = temp_qty
                    res.update({'warning': {'title': _('Warning'), 'message': _('The selected supplier has a minimal quantity set to %s, you cannot purchase less.') % qty}})
        qty_in_product_uom = product_uom_pool._compute_qty(cr, uid, uom, qty, to_uom_id=prod.uom_id.id)
        price = self.pool.get('product.pricelist').price_get(cr,uid,[pricelist],
                    product, qty_in_product_uom or 1.0, partner_id, {
                        'uom': uom,
                        'date': date_order,
                        })[pricelist]
        dt = (datetime.now() + relativedelta(days=int(seller_delay) or 0.0)).strftime('%Y-%m-%d %H:%M:%S')


        res.update({'value': {'price_unit': price, 'name': prod_name,
            'taxes_id':map(lambda x: x.id, prod.supplier_taxes_id),
            'date_planned': date_planned or dt,'notes': notes or prod.description_purchase,
            'product_qty': qty,
            'product_uom': uom}})
        domain = {}

        taxes = self.pool.get('account.tax').browse(cr, uid,map(lambda x: x.id, prod.supplier_taxes_id))
        fpos = fiscal_position and self.pool.get('account.fiscal.position').browse(cr, uid, fiscal_position) or False
        res['value']['taxes_id'] = self.pool.get('account.fiscal.position').map_tax(cr, uid, fpos, taxes)

        res2 = self.pool.get('product.uom').read(cr, uid, [uom], ['category_id'])
        res3 = prod.uom_id.category_id.id
        domain = {'product_uom':[('category_id','=',res2[0]['category_id'][0])]}
        if res2[0]['category_id'][0] != res3:
            raise osv.except_osv(_('Wrong Product UOM !'), _('You have to select a product UOM in the same category than the purchase UOM of the product'))

        res['domain'] = domain
        return res

    def product_uom_change(self, cr, uid, ids, pricelist, product, qty, uom,
            partner_id, date_order=False, fiscal_position=False, date_planned=False,
            name=False, price_unit=False, notes=False):
        res = self.product_id_change(cr, uid, ids, pricelist, product, qty, uom,
                partner_id, date_order=date_order, fiscal_position=fiscal_position, date_planned=date_planned,
            name=name, price_unit=price_unit, notes=notes)
        if 'product_uom' in res['value']:
            if uom and (uom != res['value']['product_uom']) and res['value']['product_uom']:
                seller_uom_name = self.pool.get('product.uom').read(cr, uid, [res['value']['product_uom']], ['name'])[0]['name']
                res.update({'warning': {'title': _('Warning'), 'message': _('The selected supplier only sells this product by %s') % seller_uom_name }})
            del res['value']['product_uom']
        if not uom:
            res['value']['price_unit'] = 0.0
        return res

    def action_confirm(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'confirmed'}, context=context)
        return True

purchase_order_line()

class procurement_order(osv.osv):
    _inherit = 'procurement.order'
    _columns = {
        'purchase_id': fields.many2one('purchase.order', 'Purchase Order'),
    }

    def action_po_assign(self, cr, uid, ids, context=None):
        """ This is action which call from workflow to assign purchase order to procurements
        @return: True
        """
        res = self.make_po(cr, uid, ids, context=context)
        res = res.values()
        return len(res) and res[0] or 0 #TO CHECK: why workflow is generated error if return not integer value

    def make_po(self, cr, uid, ids, context=None):
        """ Make purchase order from procurement
        @return: New created Purchase Orders procurement wise
        """
        res = {}
        if context is None:
            context = {}
        company = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id
        partner_obj = self.pool.get('res.partner')
        uom_obj = self.pool.get('product.uom')
        pricelist_obj = self.pool.get('product.pricelist')
        prod_obj = self.pool.get('product.product')
        acc_pos_obj = self.pool.get('account.fiscal.position')
        po_obj = self.pool.get('purchase.order')
        for procurement in self.browse(cr, uid, ids, context=context):
            res_id = procurement.move_id.id
            partner = procurement.product_id.seller_id # Taken Main Supplier of Product of Procurement.
            seller_qty = procurement.product_id.seller_qty
            seller_delay = int(procurement.product_id.seller_delay)
            partner_id = partner.id
            address_id = partner_obj.address_get(cr, uid, [partner_id], ['delivery'])['delivery']
            pricelist_id = partner.property_product_pricelist_purchase.id

            uom_id = procurement.product_id.uom_po_id.id

            qty = uom_obj._compute_qty(cr, uid, procurement.product_uom.id, procurement.product_qty, uom_id)
            if seller_qty:
                qty = max(qty,seller_qty)

            price = pricelist_obj.price_get(cr, uid, [pricelist_id], procurement.product_id.id, qty, partner_id, {'uom': uom_id})[pricelist_id]

            newdate = datetime.strptime(procurement.date_planned, '%Y-%m-%d %H:%M:%S')
            newdate = (newdate - relativedelta(days=company.po_lead)) - relativedelta(days=seller_delay)

            #Passing partner_id to context for purchase order line integrity of Line name
            context.update({'lang': partner.lang, 'partner_id': partner_id})

            product = prod_obj.browse(cr, uid, procurement.product_id.id, context=context)

            line = {
                'name': product.partner_ref,
                'product_qty': qty,
                'product_id': procurement.product_id.id,
                'product_uom': uom_id,
                'price_unit': price,
                'date_planned': newdate.strftime('%Y-%m-%d %H:%M:%S'),
                'move_dest_id': res_id,
                'notes': product.description_purchase,
            }

            taxes_ids = procurement.product_id.product_tmpl_id.supplier_taxes_id
            taxes = acc_pos_obj.map_tax(cr, uid, partner.property_account_position, taxes_ids)
            line.update({
                'taxes_id': [(6,0,taxes)]
            })
            purchase_id = po_obj.create(cr, uid, {
                'origin': procurement.origin,
                'partner_id': partner_id,
                'partner_address_id': address_id,
                'location_id': procurement.location_id.id,
                'pricelist_id': pricelist_id,
                'order_line': [(0,0,line)],
                'company_id': procurement.company_id.id,
                'fiscal_position': partner.property_account_position and partner.property_account_position.id or False
            })
            res[procurement.id] = purchase_id
            self.write(cr, uid, [procurement.id], {'state': 'running', 'purchase_id': purchase_id})
        return res

procurement_order()

class stock_invoice_onshipping(osv.osv_memory):
    _inherit = "stock.invoice.onshipping"

    def create_invoice(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = super(stock_invoice_onshipping,self).create_invoice(cr, uid, ids, context=context)
        purchase_obj = self.pool.get('purchase.order')
        picking_obj = self.pool.get('stock.picking')
        for pick_id in res:
            pick = picking_obj.browse(cr, uid, pick_id, context=context)
            if pick.purchase_id:
                purchase_obj.write(cr, uid, [pick.purchase_id.id], {
                    'invoice_ids': [(4, res[pick_id])]}, context=context)
        return res

stock_invoice_onshipping()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
