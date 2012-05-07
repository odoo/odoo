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
from tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP

#
# Model definition
#
class purchase_order(osv.osv):

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
               for c in self.pool.get('account.tax').compute_all(cr, uid, line.taxes_id, line.price_unit, line.product_qty, line.product_id.id, order.partner_id)['taxes']:
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
                res[purchase.id] = tot * 100.0 / purchase.amount_untaxed
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
        'date_order':fields.date('Order Date', required=True, states={'confirmed':[('readonly',True)], 'approved':[('readonly',True)]}, select=True, help="Date on which this document has been created."),
        'date_approve':fields.date('Date Approved', readonly=1, select=True, help="Date on which purchase order has been approved"),
        'partner_id':fields.many2one('res.partner', 'Supplier', required=True, states={'confirmed':[('readonly',True)], 'approved':[('readonly',True)],'done':[('readonly',True)]}, change_default=True),
        'dest_address_id':fields.many2one('res.partner', 'Customer Address (Direct Delivery)',
            states={'confirmed':[('readonly',True)], 'approved':[('readonly',True)],'done':[('readonly',True)]},
            help="Put an address if you want to deliver directly from the supplier to the customer." \
                "In this case, it will remove the warehouse link and set the customer location."
        ),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse', states={'confirmed':[('readonly',True)], 'approved':[('readonly',True)],'done':[('readonly',True)]}),
        'location_id': fields.many2one('stock.location', 'Destination', required=True, domain=[('usage','<>','view')]),
        'pricelist_id':fields.many2one('product.pricelist', 'Pricelist', required=True, states={'confirmed':[('readonly',True)], 'approved':[('readonly',True)],'done':[('readonly',True)]}, help="The pricelist sets the currency used for this purchase order. It also computes the supplier price for the selected products/quantities."),
        'state': fields.selection(STATE_SELECTION, 'Status', readonly=True, help="The state of the purchase order or the quotation request. A quotation is a purchase order in a 'Draft' state. Then the order has to be confirmed by the user, the state switch to 'Confirmed'. Then the supplier must confirm the order to change the state to 'Approved'. When the purchase order is paid and received, the state becomes 'Done'. If a cancel action occurs in the invoice or in the reception of goods, the state becomes in exception.", select=True),
        'order_line': fields.one2many('purchase.order.line', 'order_id', 'Order Lines', states={'approved':[('readonly',True)],'done':[('readonly',True)]}),
        'validator' : fields.many2one('res.users', 'Validated by', readonly=True),
        'notes': fields.text('Notes'),
        'invoice_ids': fields.many2many('account.invoice', 'purchase_invoice_rel', 'purchase_id', 'invoice_id', 'Invoices', help="Invoices generated for a purchase order"),
        'picking_ids': fields.one2many('stock.picking', 'purchase_id', 'Picking List', readonly=True, help="This is the list of picking list that have been generated for this purchase"),
        'shipped':fields.boolean('Received', readonly=True, select=True, help="It indicates that a picking has been done"),
        'shipped_rate': fields.function(_shipped_rate, string='Received', type='float'),
        'invoiced': fields.function(_invoiced, string='Invoiced & Paid', type='boolean', help="It indicates that an invoice has been paid"),
        'invoiced_rate': fields.function(_invoiced_rate, string='Invoiced', type='float'),
        'invoice_method': fields.selection([('manual','Based on Purchase Order lines'),('order','Based on generated draft invoice'),('picking','Bases on incoming shipments')], 'Invoicing Control', required=True,
            help="Based on Purchase Order lines: place individual lines in 'Invoice Control > Based on P.O. lines' from where you can selectively create an invoice.\n" \
                "Based on generated invoice: create a draft invoice you can validate later.\n" \
                "Bases on incoming shipments: let you create an invoice when receptions are validated."
        ),
        'minimum_planned_date':fields.function(_minimum_planned_date, fnct_inv=_set_minimum_planned_date, string='Expected Date', type='date', select=True, help="This is computed as the minimum scheduled date of all purchase order lines' products.",
            store = {
                'purchase.order.line': (_get_order, ['date_planned'], 10),
            }
        ),
        'amount_untaxed': fields.function(_amount_all, digits_compute= dp.get_precision('Purchase Price'), string='Untaxed Amount',
            store={
                'purchase.order.line': (_get_order, None, 10),
            }, multi="sums", help="The amount without tax"),
        'amount_tax': fields.function(_amount_all, digits_compute= dp.get_precision('Purchase Price'), string='Taxes',
            store={
                'purchase.order.line': (_get_order, None, 10),
            }, multi="sums", help="The tax amount"),
        'amount_total': fields.function(_amount_all, digits_compute= dp.get_precision('Purchase Price'), string='Total',
            store={
                'purchase.order.line': (_get_order, None, 10),
            }, multi="sums",help="The total amount"),
        'fiscal_position': fields.many2one('account.fiscal.position', 'Fiscal Position'),
        'product_id': fields.related('order_line','product_id', type='many2one', relation='product.product', string='Product'),
        'create_uid':  fields.many2one('res.users', 'Responsible'),
        'company_id': fields.many2one('res.company','Company',required=True,select=1),
    }
    _defaults = {
        'date_order': fields.date.context_today,
        'state': 'draft',
        'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'purchase.order'),
        'shipped': 0,
        'invoice_method': 'order',
        'invoiced': 0,
        'pricelist_id': lambda self, cr, uid, context: context.get('partner_id', False) and self.pool.get('res.partner').browse(cr, uid, context['partner_id']).property_product_pricelist_purchase.id,
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'purchase.order', context=c),
    }
    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)', 'Order Reference must be unique per Company!'),
    ]
    _name = "purchase.order"
    _inherit = ['ir.needaction_mixin', 'mail.thread']
    _description = "Purchase Order"
    _order = "name desc"
    
    def create(self, cr, uid, vals, context=None):
        order =  super(purchase_order, self).create(cr, uid, vals, context=context)
        if order:
            self.create_send_note(cr, uid, [order], context=context)
        return order
    
    def unlink(self, cr, uid, ids, context=None):
        purchase_orders = self.read(cr, uid, ids, ['state'], context=context)
        unlink_ids = []
        for s in purchase_orders:
            if s['state'] in ['draft','cancel']:
                unlink_ids.append(s['id'])
            else:
                raise osv.except_osv(_('Invalid action !'), _('In order to delete a purchase order, it must be cancelled first!'))

        # TODO: temporary fix in 5.0, to remove in 5.2 when subflows support
        # automatically sending subflow.delete upon deletion
        wf_service = netsvc.LocalService("workflow")
        for id in unlink_ids:
            wf_service.trg_validate(uid, 'purchase.order', id, 'purchase_cancel', cr)

        return super(purchase_order, self).unlink(cr, uid, unlink_ids, context=context)

    def button_dummy(self, cr, uid, ids, context=None):
        return True

    def onchange_dest_address_id(self, cr, uid, ids, address_id):
        if not address_id:
            return {}
        address = self.pool.get('res.partner')
        values = {'warehouse_id': False}
        supplier = address.browse(cr, uid, address_id)
        if supplier:
            location_id = supplier.property_stock_customer.id
            values.update({'location_id': location_id})
        return {'value':values}

    def onchange_warehouse_id(self, cr, uid, ids, warehouse_id):
        if not warehouse_id:
            return {}
        warehouse = self.pool.get('stock.warehouse').browse(cr, uid, warehouse_id)
        return {'value':{'location_id': warehouse.lot_input_id.id, 'dest_address_id': False}}

    def onchange_partner_id(self, cr, uid, ids, partner_id):
        partner = self.pool.get('res.partner')
        if not partner_id:
            return {'value':{'fiscal_position': False}}
        supplier_address = partner.address_get(cr, uid, [partner_id], ['default'])
        supplier = partner.browse(cr, uid, partner_id)
        pricelist = supplier.property_product_pricelist_purchase.id
        fiscal_position = supplier.property_account_position and supplier.property_account_position.id or False
        return {'value':{'pricelist_id': pricelist, 'fiscal_position': fiscal_position}}

    def wkf_approve_order(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'approved', 'date_approve': fields.date.context_today(self,cr,uid,context=context)})
        return True

    #TODO: implement messages system
    def wkf_confirm_order(self, cr, uid, ids, context=None):
        todo = []
        for po in self.browse(cr, uid, ids, context=context):
            if not po.order_line:
                raise osv.except_osv(_('Error !'),_('You cannot confirm a purchase order without any lines.'))
            for line in po.order_line:
                if line.state=='draft':
                    todo.append(line.id)
            message = _("Purchase order '%s' is confirmed.") % (po.name,)
            self.log(cr, uid, po.id, message)
#        current_name = self.name_get(cr, uid, ids)[0][1]
        self.pool.get('purchase.order.line').action_confirm(cr, uid, todo, context)
        for id in ids:
            self.write(cr, uid, [id], {'state' : 'confirmed', 'validator' : uid})
        self.confirm_send_note(cr, uid, ids, context)
        return True

    def _prepare_inv_line(self, cr, uid, account_id, order_line, context=None):
        """Collects require data from purchase order line that is used to create invoice line
        for that purchase order line
        :param account_id: Expense account of the product of PO line if any.
        :param browse_record order_line: Purchase order line browse record
        :return: Value for fields of invoice lines.
        :rtype: dict
        """
        return {
            'name': order_line.name,
            'account_id': account_id,
            'price_unit': order_line.price_unit or 0.0,
            'quantity': order_line.product_qty,
            'product_id': order_line.product_id.id or False,
            'uos_id': order_line.product_uom.id or False,
            'invoice_line_tax_id': [(6, 0, [x.id for x in order_line.taxes_id])],
            'account_analytic_id': order_line.account_analytic_id.id or False,
        }

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

    def action_invoice_create(self, cr, uid, ids, context=None):
        """Generates invoice for given ids of purchase orders and links that invoice ID to purchase order.
        :param ids: list of ids of purchase orders.
        :return: ID of created invoice.
        :rtype: int
        """
        res = False

        journal_obj = self.pool.get('account.journal')
        inv_obj = self.pool.get('account.invoice')
        inv_line_obj = self.pool.get('account.invoice.line')
        fiscal_obj = self.pool.get('account.fiscal.position')
        property_obj = self.pool.get('ir.property')

        for order in self.browse(cr, uid, ids, context=context):
            pay_acc_id = order.partner_id.property_account_payable.id
            journal_ids = journal_obj.search(cr, uid, [('type', '=','purchase'),('company_id', '=', order.company_id.id)], limit=1)
            if not journal_ids:
                raise osv.except_osv(_('Error !'),
                    _('There is no purchase journal defined for this company: "%s" (id:%d)') % (order.company_id.name, order.company_id.id))

            # generate invoice line correspond to PO line and link that to created invoice (inv_id) and PO line
            inv_lines = []
            for po_line in order.order_line:
                if po_line.product_id:
                    acc_id = po_line.product_id.product_tmpl_id.property_account_expense.id
                    if not acc_id:
                        acc_id = po_line.product_id.categ_id.property_account_expense_categ.id
                    if not acc_id:
                        raise osv.except_osv(_('Error !'), _('There is no expense account defined for this product: "%s" (id:%d)') % (po_line.product_id.name, po_line.product_id.id,))
                else:
                    acc_id = property_obj.get(cr, uid, 'property_account_expense_categ', 'product.category').id
                fpos = order.fiscal_position or False
                acc_id = fiscal_obj.map_account(cr, uid, fpos, acc_id)

                inv_line_data = self._prepare_inv_line(cr, uid, acc_id, po_line, context=context)
                inv_line_id = inv_line_obj.create(cr, uid, inv_line_data, context=context)
                inv_lines.append(inv_line_id)

                po_line.write({'invoiced':True, 'invoice_lines': [(4, inv_line_id)]}, context=context)

            # get invoice data and create invoice
            inv_data = {
                'name': order.partner_ref or order.name,
                'reference': order.partner_ref or order.name,
                'account_id': pay_acc_id,
                'type': 'in_invoice',
                'partner_id': order.partner_id.id,
                'currency_id': order.pricelist_id.currency_id.id,
                'journal_id': len(journal_ids) and journal_ids[0] or False,
                'invoice_line': [(6, 0, inv_lines)],
                'origin': order.name,
                'fiscal_position': order.fiscal_position.id or order.partner_id.property_account_position.id,
                'payment_term': order.partner_id.property_payment_term and order.partner_id.property_payment_term.id or False,
                'company_id': order.company_id.id,
            }
            inv_id = inv_obj.create(cr, uid, inv_data, context=context)

            # compute the invoice
            inv_obj.button_compute(cr, uid, [inv_id], context=context, set_total=True)

            # Link this new invoice to related purchase order
            order.write({'invoice_ids': [(4, inv_id)]}, context=context)
            res = inv_id
        if res:
            self.invoice_send_note(cr, uid, ids, res, context)
        return res
    
    def invoice_done(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'approved'}, context=context)
        self.invoice_done_send_note(cr, uid, ids, context=context)
        return True
        
    def has_stockable_product(self,cr, uid, ids, *args):
        for order in self.browse(cr, uid, ids):
            for order_line in order.order_line:
                if order_line.product_id and order_line.product_id.product_tmpl_id.type in ('product', 'consu'):
                    return True
        return False

    def action_cancel(self, cr, uid, ids, context=None):
        wf_service = netsvc.LocalService("workflow")
        for purchase in self.browse(cr, uid, ids, context=context):
            for pick in purchase.picking_ids:
                if pick.state not in ('draft','cancel'):
                    raise osv.except_osv(
                        _('Unable to cancel this purchase order!'),
                        _('You must first cancel all receptions related to this purchase order.'))
            for pick in purchase.picking_ids:
                wf_service.trg_validate(uid, 'stock.picking', pick.id, 'button_cancel', cr)
            for inv in purchase.invoice_ids:
                if inv and inv.state not in ('cancel','draft'):
                    raise osv.except_osv(
                        _('Unable to cancel this purchase order!'),
                        _('You must first cancel all invoices related to this purchase order.'))
                if inv:
                    wf_service.trg_validate(uid, 'account.invoice', inv.id, 'invoice_cancel', cr)
        self.write(cr,uid,ids,{'state':'cancel'})

        for (id, name) in self.name_get(cr, uid, ids):
            wf_service.trg_validate(uid, 'purchase.order', id, 'purchase_cancel', cr)
            message = _("Purchase order '%s' is cancelled.") % name
            self.log(cr, uid, id, message)
        return True

    def _prepare_order_picking(self, cr, uid, order, context=None):
        return {
            'name': self.pool.get('ir.sequence').get(cr, uid, 'stock.picking.in'),
            'origin': order.name + ((order.origin and (':' + order.origin)) or ''),
            'date': order.date_order,
            'type': 'in',
            'partner_id': order.dest_address_id.id or order.partner_id.id,
            'invoice_state': '2binvoiced' if order.invoice_method == 'picking' else 'none',
            'purchase_id': order.id,
            'company_id': order.company_id.id,
            'move_lines' : [],
        }

    def _prepare_order_line_move(self, cr, uid, order, order_line, picking_id, context=None):
        return {
            'name': order.name + ': ' + (order_line.name or ''),
            'product_id': order_line.product_id.id,
            'product_qty': order_line.product_qty,
            'product_uos_qty': order_line.product_qty,
            'product_uom': order_line.product_uom.id,
            'product_uos': order_line.product_uom.id,
            'date': order_line.date_planned,
            'date_expected': order_line.date_planned,
            'location_id': order.partner_id.property_stock_supplier.id,
            'location_dest_id': order.location_id.id,
            'picking_id': picking_id,
            'partner_id': order.dest_address_id.id or order.partner_id.id,
            'move_dest_id': order_line.move_dest_id.id,
            'state': 'draft',
            'purchase_line_id': order_line.id,
            'company_id': order.company_id.id,
            'price_unit': order_line.price_unit
        }

    def _create_pickings(self, cr, uid, order, order_lines, picking_id=False, context=None):
        """Creates pickings and appropriate stock moves for given order lines, then
        confirms the moves, makes them available, and confirms the picking.

        If ``picking_id`` is provided, the stock moves will be added to it, otherwise
        a standard outgoing picking will be created to wrap the stock moves, as returned
        by :meth:`~._prepare_order_picking`.

        Modules that wish to customize the procurements or partition the stock moves over
        multiple stock pickings may override this method and call ``super()`` with
        different subsets of ``order_lines`` and/or preset ``picking_id`` values.

        :param browse_record order: purchase order to which the order lines belong
        :param list(browse_record) order_lines: purchase order line records for which picking
                                                and moves should be created.
        :param int picking_id: optional ID of a stock picking to which the created stock moves
                               will be added. A new picking will be created if omitted.
        :return: list of IDs of pickings used/created for the given order lines (usually just one)
        """
        if not picking_id:
            picking_id = self.pool.get('stock.picking').create(cr, uid, self._prepare_order_picking(cr, uid, order, context=context))
        todo_moves = []
        stock_move = self.pool.get('stock.move')
        wf_service = netsvc.LocalService("workflow")
        for order_line in order_lines:
            if not order_line.product_id:
                continue
            if order_line.product_id.type in ('product', 'consu'):
                move = stock_move.create(cr, uid, self._prepare_order_line_move(cr, uid, order, order_line, picking_id, context=context))
                if order_line.move_dest_id:
                    order_line.move_dest_id.write({'location_id': order.location_id.id})
                todo_moves.append(move)
        stock_move.action_confirm(cr, uid, todo_moves)
        stock_move.force_assign(cr, uid, todo_moves)
        wf_service.trg_validate(uid, 'stock.picking', picking_id, 'button_confirm', cr)
        return [picking_id]

    def action_picking_create(self,cr, uid, ids, context=None):
        picking_ids = []
        for order in self.browse(cr, uid, ids):
            picking_ids.extend(self._create_pickings(cr, uid, order, order.order_line, None, context=context))

        # Must return one unique picking ID: the one to connect in the subflow of the purchase order.
        # In case of multiple (split) pickings, we should return the ID of the critical one, i.e. the
        # one that should trigger the advancement of the purchase workflow.
        # By default we will consider the first one as most important, but this behavior can be overridden.
        if picking_ids:
            self.shipment_send_note(cr, uid, ids, picking_ids[0], context=context)
        return picking_ids[0] if picking_ids else False

    def picking_done(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'shipped':1,'state':'approved'}, context=context)
        self.shipment_done_send_note(cr, uid, ids, context=context)
        return True

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
        #TOFIX: merged order line should be unlink
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
                    'date_order': porder.date_order,
                    'partner_id': porder.partner_id.id,
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
                if porder.date_order < order_infos['date_order']:
                    order_infos['date_order'] = porder.date_order
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
        
    # --------------------------------------
    # OpenChatter methods and notifications
    # --------------------------------------
    
    def get_needaction_user_ids(self, cr, uid, ids, context=None):
        result = dict.fromkeys(ids, [])
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.state == 'approved':
                result[obj.id] = [obj.validator.id]
        return result
    
    def create_send_note(self, cr, uid, ids, context=None):
        return self.message_append_note(cr, uid, ids, body=_("Request for quotation <b>created</b>."), context=context)

    def confirm_send_note(self, cr, uid, ids, context=None):
        for obj in self.browse(cr, uid, ids, context=context):
            self.message_subscribe(cr, uid, [obj.id], [obj.validator.id], context=context)
            self.message_append_note(cr, uid, [obj.id], body=_("Quotation for <em>%s</em> <b>converted</b> to a Purchase Order of %s %s.") % (obj.partner_id.name, obj.amount_total, obj.pricelist_id.currency_id.symbol), context=context)
        
    def shipment_send_note(self, cr, uid, ids, picking_id, context=None):
        for order in self.browse(cr, uid, ids, context=context):
            for picking in (pck for pck in order.picking_ids if pck.id == picking_id):
                # convert datetime field to a datetime, using server format, then
                # convert it to the user TZ and re-render it with %Z to add the timezone
                picking_datetime = fields.DT.datetime.strptime(picking.min_date, DEFAULT_SERVER_DATETIME_FORMAT)
                picking_date_str = fields.datetime.context_timestamp(cr, uid, picking_datetime, context=context).strftime(DATETIME_FORMATS_MAP['%+'] + " (%Z)")
                self.message_append_note(cr, uid, [order.id], body=_("Shipment <em>%s</em> <b>scheduled</b> for %s.") % (picking.name, picking_date_str), context=context)
    
    def invoice_send_note(self, cr, uid, ids, invoice_id, context=None):
        for order in self.browse(cr, uid, ids, context=context):
            for invoice in (inv for inv in order.invoice_ids if inv.id == invoice_id):
                self.message_append_note(cr, uid, [order.id], body=_("Draft Invoice of %s %s is <b>waiting for validation</b>.") % (invoice.amount_total, invoice.currency_id.symbol), context=context)
    
    def shipment_done_send_note(self, cr, uid, ids, context=None):
        self.message_append_note(cr, uid, ids, body=_("""Shipment <b>received</b>."""), context=context)
     
    def invoice_done_send_note(self, cr, uid, ids, context=None):
        self.message_append_note(cr, uid, ids, body=_("Invoice <b>paid</b>."), context=context)
    
    def cancel_send_note(self, cr, uid, ids, context=None):
        for obj in self.browse(cr, uid, ids, context=context):
            self.message_append_note(cr, uid, [obj.id], body=_("Purchase Order for <em>%s</em> <b>cancelled</b>.") % (obj.partner_id.name), context=context)

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

    def _get_uom_id(self, cr, uid, context=None):
        try:
            proxy = self.pool.get('ir.model.data')
            result = proxy.get_object_reference(cr, uid, 'product', 'product_uom_unit')
            return result[1]
        except Exception, ex:
            return False

    _columns = {
        'name': fields.char('Description', size=256, required=True),
        'product_qty': fields.float('Quantity', digits_compute=dp.get_precision('Product UoM'), required=True),
        'date_planned': fields.date('Scheduled Date', required=True, select=True),
        'taxes_id': fields.many2many('account.tax', 'purchase_order_taxe', 'ord_id', 'tax_id', 'Taxes'),
        'product_uom': fields.many2one('product.uom', 'Product UOM', required=True),
        'product_id': fields.many2one('product.product', 'Product', domain=[('purchase_ok','=',True)], change_default=True),
        'move_ids': fields.one2many('stock.move', 'purchase_line_id', 'Reservation', readonly=True, ondelete='set null'),
        'move_dest_id': fields.many2one('stock.move', 'Reservation Destination', ondelete='set null'),
        'price_unit': fields.float('Unit Price', required=True, digits_compute= dp.get_precision('Purchase Price')),
        'price_subtotal': fields.function(_amount_line, string='Subtotal', digits_compute= dp.get_precision('Purchase Price')),
        'notes': fields.text('Notes'),
        'order_id': fields.many2one('purchase.order', 'Order Reference', select=True, required=True, ondelete='cascade'),
        'account_analytic_id':fields.many2one('account.analytic.account', 'Analytic Account',),
        'company_id': fields.related('order_id','company_id',type='many2one',relation='res.company',string='Company', store=True, readonly=True),
        'state': fields.selection([('draft', 'Draft'), ('confirmed', 'Confirmed'), ('done', 'Done'), ('cancel', 'Cancelled')], 'Status', required=True, readonly=True,
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
        'product_uom' : _get_uom_id,
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

    def onchange_product_uom(self, cr, uid, ids, pricelist_id, product_id, qty, uom_id,
            partner_id, date_order=False, fiscal_position_id=False, date_planned=False,
            name=False, price_unit=False, notes=False, context=None):
        """
        onchange handler of product_uom.
        """
        if not uom_id:
            return {'value': {'price_unit': price_unit or 0.0, 'name': name or '', 'notes': notes or'', 'product_uom' : uom_id or False}}
        return self.onchange_product_id(cr, uid, ids, pricelist_id, product_id, qty, uom_id,
            partner_id, date_order=date_order, fiscal_position_id=fiscal_position_id, date_planned=date_planned,
            name=name, price_unit=price_unit, notes=notes, context=context)

    def _get_date_planned(self, cr, uid, supplier_info, date_order_str, context=None):
        """Return the datetime value to use as Schedule Date (``date_planned``) for
           PO Lines that correspond to the given product.supplierinfo,
           when ordered at `date_order_str`.

           :param browse_record | False supplier_info: product.supplierinfo, used to
               determine delivery delay (if False, default delay = 0)
           :param str date_order_str: date of order, as a string in
               DEFAULT_SERVER_DATE_FORMAT
           :rtype: datetime
           :return: desired Schedule Date for the PO line
        """
        supplier_delay = int(supplier_info.delay) if supplier_info else 0
        return datetime.strptime(date_order_str, DEFAULT_SERVER_DATE_FORMAT) + relativedelta(days=supplier_delay)

    def onchange_product_id(self, cr, uid, ids, pricelist_id, product_id, qty, uom_id,
            partner_id, date_order=False, fiscal_position_id=False, date_planned=False,
            name=False, price_unit=False, notes=False, context=None):
        """
        onchange handler of product_id.
        """
        if context is None:
            context = {}

        res = {'value': {'price_unit': price_unit or 0.0, 'name': name or '', 'notes': notes or '', 'product_uom' : uom_id or False}}
        if not product_id:
            return res

        product_product = self.pool.get('product.product')
        product_uom = self.pool.get('product.uom')
        res_partner = self.pool.get('res.partner')
        product_supplierinfo = self.pool.get('product.supplierinfo')
        product_pricelist = self.pool.get('product.pricelist')
        account_fiscal_position = self.pool.get('account.fiscal.position')
        account_tax = self.pool.get('account.tax')

        # - check for the presence of partner_id and pricelist_id
        if not pricelist_id:
            raise osv.except_osv(_('No Pricelist !'), _('You have to select a pricelist or a supplier in the purchase form !\nPlease set one before choosing a product.'))
        if not partner_id:
            raise osv.except_osv(_('No Partner!'), _('You have to select a partner in the purchase form !\nPlease set one partner before choosing a product.'))

        # - determine name and notes based on product in partner lang.
        lang = res_partner.browse(cr, uid, partner_id).lang
        context_partner = {'lang': lang, 'partner_id': partner_id}
        product = product_product.browse(cr, uid, product_id, context=context_partner)
        res['value'].update({'name': product.name, 'notes': notes or product.description_purchase})

        # - set a domain on product_uom
        res['domain'] = {'product_uom': [('category_id','=',product.uom_id.category_id.id)]}

        # - check that uom and product uom belong to the same category
        product_uom_po_id = product.uom_po_id.id
        if not uom_id:
            uom_id = product_uom_po_id

        if product.uom_id.category_id.id != product_uom.browse(cr, uid, uom_id, context=context).category_id.id:
            res['warning'] = {'title': _('Warning'), 'message': _('Selected UOM does not belong to the same category as the product UOM')}
            uom_id = product_uom_po_id

        res['value'].update({'product_uom': uom_id})

        # - determine product_qty and date_planned based on seller info
        if not date_order:
            date_order = fields.date.context_today(cr,uid,context=context)

        qty = qty or 1.0
        supplierinfo = False
        supplierinfo_ids = product_supplierinfo.search(cr, uid, [('name','=',partner_id),('product_id','=',product.id)])
        if supplierinfo_ids:
            supplierinfo = product_supplierinfo.browse(cr, uid, supplierinfo_ids[0], context=context)
            if supplierinfo.product_uom.id != uom_id:
                res['warning'] = {'title': _('Warning'), 'message': _('The selected supplier only sells this product by %s') % supplierinfo.product_uom.name }
            min_qty = product_uom._compute_qty(cr, uid, supplierinfo.product_uom.id, supplierinfo.min_qty, to_uom_id=uom_id)
            if qty < min_qty: # If the supplier quantity is greater than entered from user, set minimal.
                res['warning'] = {'title': _('Warning'), 'message': _('The selected supplier has a minimal quantity set to %s %s, you should not purchase less.') % (supplierinfo.min_qty, supplierinfo.product_uom.name)}
                qty = min_qty

        dt = self._get_date_planned(cr, uid, supplierinfo, date_order, context=context).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        res['value'].update({'date_planned': date_planned or dt, 'product_qty': qty})

        # - determine price_unit and taxes_id
        price = product_pricelist.price_get(cr, uid, [pricelist_id],
                    product.id, qty or 1.0, partner_id, {'uom': uom_id, 'date': date_order})[pricelist_id]

        taxes = account_tax.browse(cr, uid, map(lambda x: x.id, product.supplier_taxes_id))
        fpos = fiscal_position_id and account_fiscal_position.browse(cr, uid, fiscal_position_id, context=context) or False
        taxes_ids = account_fiscal_position.map_tax(cr, uid, fpos, taxes)
        res['value'].update({'price_unit': price, 'taxes_id': taxes_ids})

        return res

    product_id_change = onchange_product_id
    product_uom_change = onchange_product_uom

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

    def create_procurement_purchase_order(self, cr, uid, procurement, po_vals, line_vals, context=None):
        """Create the purchase order from the procurement, using
           the provided field values, after adding the given purchase
           order line in the purchase order.

           :params procurement: the procurement object generating the purchase order
           :params dict po_vals: field values for the new purchase order (the
                                 ``order_line`` field will be overwritten with one
                                 single line, as passed in ``line_vals``).
           :params dict line_vals: field values of the single purchase order line that
                                   the purchase order will contain.
           :return: id of the newly created purchase order
           :rtype: int
        """
        po_vals.update({'order_line': [(0,0,line_vals)]})
        return self.pool.get('purchase.order').create(cr, uid, po_vals, context=context)

    def _get_purchase_schedule_date(self, cr, uid, procurement, company, context=None):
        """Return the datetime value to use as Schedule Date (``date_planned``) for the
           Purchase Order Lines created to satisfy the given procurement.

           :param browse_record procurement: the procurement for which a PO will be created.
           :param browse_report company: the company to which the new PO will belong to.
           :rtype: datetime
           :return: the desired Schedule Date for the PO lines
        """
        procurement_date_planned = datetime.strptime(procurement.date_planned, DEFAULT_SERVER_DATETIME_FORMAT)
        schedule_date = (procurement_date_planned - relativedelta(days=company.po_lead))
        return schedule_date

    def _get_purchase_order_date(self, cr, uid, procurement, company, schedule_date, context=None):
        """Return the datetime value to use as Order Date (``date_order``) for the
           Purchase Order created to satisfy the given procurement.

           :param browse_record procurement: the procurement for which a PO will be created.
           :param browse_report company: the company to which the new PO will belong to.
           :param datetime schedule_date: desired Scheduled Date for the Purchase Order lines.
           :rtype: datetime
           :return: the desired Order Date for the PO
        """
        seller_delay = int(procurement.product_id.seller_delay)
        return schedule_date - relativedelta(days=seller_delay)

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
        seq_obj = self.pool.get('ir.sequence')
        warehouse_obj = self.pool.get('stock.warehouse')
        for procurement in self.browse(cr, uid, ids, context=context):
            res_id = procurement.move_id.id
            partner = procurement.product_id.seller_id # Taken Main Supplier of Product of Procurement.
            seller_qty = procurement.product_id.seller_qty
            partner_id = partner.id
            address_id = partner_obj.address_get(cr, uid, [partner_id], ['delivery'])['delivery']
            pricelist_id = partner.property_product_pricelist_purchase.id
            warehouse_id = warehouse_obj.search(cr, uid, [('company_id', '=', procurement.company_id.id or company.id)], context=context)
            uom_id = procurement.product_id.uom_po_id.id

            qty = uom_obj._compute_qty(cr, uid, procurement.product_uom.id, procurement.product_qty, uom_id)
            if seller_qty:
                qty = max(qty,seller_qty)

            price = pricelist_obj.price_get(cr, uid, [pricelist_id], procurement.product_id.id, qty, partner_id, {'uom': uom_id})[pricelist_id]

            schedule_date = self._get_purchase_schedule_date(cr, uid, procurement, company, context=context)
            purchase_date = self._get_purchase_order_date(cr, uid, procurement, company, schedule_date, context=context)

            #Passing partner_id to context for purchase order line integrity of Line name
            context.update({'lang': partner.lang, 'partner_id': partner_id})

            product = prod_obj.browse(cr, uid, procurement.product_id.id, context=context)
            taxes_ids = procurement.product_id.product_tmpl_id.supplier_taxes_id
            taxes = acc_pos_obj.map_tax(cr, uid, partner.property_account_position, taxes_ids)

            line_vals = {
                'name': product.partner_ref,
                'product_qty': qty,
                'product_id': procurement.product_id.id,
                'product_uom': uom_id,
                'price_unit': price or 0.0,
                'date_planned': schedule_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                'move_dest_id': res_id,
                'notes': product.description_purchase,
                'taxes_id': [(6,0,taxes)],
            }
            name = seq_obj.get(cr, uid, 'purchase.order') or _('PO: %s') % procurement.name
            po_vals = {
                'name': name,
                'origin': procurement.origin,
                'partner_id': partner_id,
                'location_id': procurement.location_id.id,
                'warehouse_id': warehouse_id and warehouse_id[0] or False,
                'pricelist_id': pricelist_id,
                'date_order': purchase_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                'company_id': procurement.company_id.id,
                'fiscal_position': partner.property_account_position and partner.property_account_position.id or False
            }
            res[procurement.id] = self.create_procurement_purchase_order(cr, uid, procurement, po_vals, line_vals, context=context)
            self.write(cr, uid, [procurement.id], {'state': 'running', 'purchase_id': res[procurement.id]})
        return res

procurement_order()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
