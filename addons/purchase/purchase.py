# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytz
from openerp import SUPERUSER_ID, workflow
from datetime import datetime
from dateutil.relativedelta import relativedelta
from operator import attrgetter
from openerp.tools.safe_eval import safe_eval as eval
from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.osv.orm import browse_record_list, browse_record, browse_null
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP
from openerp.tools.float_utils import float_compare
from openerp.exceptions import UserError

class purchase_order(osv.osv):

    def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        cur_obj = self.pool.get('res.currency')
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
                for c in line.taxes_id.compute_all(line.price_unit, cur, line.product_qty, product=line.product_id, partner=order.partner_id)['taxes']:
                    val += c.get('amount', 0.0)
            res[order.id]['amount_tax'] = cur_obj.round(cr, uid, cur, val)
            res[order.id]['amount_untaxed'] = cur_obj.round(cr, uid, cur, val1)
            res[order.id]['amount_total'] = res[order.id]['amount_untaxed'] + res[order.id]['amount_tax']
        return res

    def _set_minimum_planned_date(self, cr, uid, ids, name, value, arg, context=None):
        if not value: return False
        if type(ids)!=type([]):
            ids=[ids]
        pol_obj = self.pool.get('purchase.order.line')
        for po in self.browse(cr, uid, ids, context=context):
            if po.order_line:
                pol_ids = pol_obj.search(cr, uid, [
                    ('order_id', '=', po.id), '|', ('date_planned', '=', po.minimum_planned_date), ('date_planned', '<', value)
                ], context=context)
                pol_obj.write(cr, uid, pol_ids, {'date_planned': value}, context=context)
        self.invalidate_cache(cr, uid, context=context)
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
                p.order_id, sum(m.product_qty), m.state
            FROM
                stock_move m
            LEFT JOIN
                purchase_order_line p on (p.id=m.purchase_line_id)
            WHERE
                p.order_id IN %s GROUP BY m.state, p.order_id''',(tuple(ids),))
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
            res[purchase.id] = all(line.invoiced for line in purchase.order_line)
        return res
    
    def _get_journal(self, cr, uid, context=None):
        if context is None:
            context = {}
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        company_id = context.get('company_id', user.company_id.id)
        journal_obj = self.pool.get('account.journal')
        res = journal_obj.search(cr, uid, [('type', '=', 'purchase'),
                                            ('company_id', '=', company_id)],
                                                limit=1)
        return res and res[0] or False  

    def _get_picking_in(self, cr, uid, context=None):
        obj_data = self.pool.get('ir.model.data')
        type_obj = self.pool.get('stock.picking.type')
        user_obj = self.pool.get('res.users')
        company_id = user_obj.browse(cr, uid, uid, context=context).company_id.id
        types = type_obj.search(cr, uid, [('code', '=', 'incoming'), ('warehouse_id.company_id', '=', company_id)], context=context)
        if not types:
            types = type_obj.search(cr, uid, [('code', '=', 'incoming'), ('warehouse_id', '=', False)], context=context)
            if not types:
                raise UserError(_("Make sure you have at least an incoming picking type defined"))
        return types[0]

    def _get_picking_ids(self, cr, uid, ids, field_names, args, context=None):
        res = {}
        for po_id in ids:
            res[po_id] = []
        query = """
        SELECT picking_id, po.id FROM stock_picking p, stock_move m, purchase_order_line pol, purchase_order po
            WHERE po.id in %s and po.id = pol.order_id and pol.id = m.purchase_line_id and m.picking_id = p.id
            GROUP BY picking_id, po.id
             
        """
        cr.execute(query, (tuple(ids), ))
        picks = cr.fetchall()
        for pick_id, po_id in picks:
            res[po_id].append(pick_id)
        return res

    def _count_all(self, cr, uid, ids, field_name, arg, context=None):
        return {
            purchase.id: {
                'shipment_count': len(purchase.picking_ids),
                'invoice_count': len(purchase.invoice_ids),                
            }
            for purchase in self.browse(cr, uid, ids, context=context)
        }

    STATE_SELECTION = [
        ('draft', 'Draft PO'),
        ('sent', 'RFQ'),
        ('bid', 'Bid Received'),
        ('confirmed', 'Waiting Approval'),
        ('approved', 'Purchase Confirmed'),
        ('except_picking', 'Shipping Exception'),
        ('except_invoice', 'Invoice Exception'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ]

    READONLY_STATES = {
        'confirmed': [('readonly', True)],
        'approved': [('readonly', True)],
        'done': [('readonly', True)]
    }

    _columns = {
        'name': fields.char('Order Reference', required=True, select=True, copy=False,
                            help="Unique number of the purchase order, "
                                 "computed automatically when the purchase order is created."),
        'origin': fields.char('Source Document', copy=False,
                              help="Reference of the document that generated this purchase order "
                                   "request; a sales order or an internal procurement request."),
        'partner_ref': fields.char('Supplier Reference', states={'confirmed':[('readonly',True)],
                                                                 'approved':[('readonly',True)],
                                                                 'done':[('readonly',True)]},
                                   copy=False,
                                   help="Reference of the sales order or bid sent by your supplier. "
                                        "It's mainly used to do the matching when you receive the "
                                        "products as this reference is usually written on the "
                                        "delivery order sent by your supplier."),
        'date_order':fields.datetime('Order Date', required=True, states={'confirmed':[('readonly',True)],
                                                                      'approved':[('readonly',True)]},
                                 select=True, help="Depicts the date where the Quotation should be validated and converted into a Purchase Order, by default it's the creation date.",
                                 copy=False),
        'date_approve':fields.date('Date Approved', readonly=1, select=True, copy=False,
                                   help="Date on which purchase order has been approved"),
        'partner_id':fields.many2one('res.partner', 'Supplier', required=True, states=READONLY_STATES,
            change_default=True, track_visibility='always'),
        'dest_address_id':fields.many2one('res.partner', 'Customer Address (Direct Delivery)',
            states=READONLY_STATES,
            help="Put an address if you want to deliver directly from the supplier to the customer. " \
                "Otherwise, keep empty to deliver to your own company."
        ),
        'location_id': fields.many2one('stock.location', 'Destination', required=True, domain=[('usage','<>','view')], states=READONLY_STATES),
        'pricelist_id':fields.many2one('product.pricelist', 'Pricelist', required=True, states=READONLY_STATES, help="The pricelist sets the currency used for this purchase order. It also computes the supplier price for the selected products/quantities."),
        'currency_id': fields.many2one('res.currency','Currency', required=True, states=READONLY_STATES),
        'state': fields.selection(STATE_SELECTION, 'Status', readonly=True,
                                  help="The status of the purchase order or the quotation request. "
                                       "A request for quotation is a purchase order in a 'Draft' status. "
                                       "Then the order has to be confirmed by the user, the status switch "
                                       "to 'Confirmed'. Then the supplier must confirm the order to change "
                                       "the status to 'Approved'. When the purchase order is paid and "
                                       "received, the status becomes 'Done'. If a cancel action occurs in "
                                       "the invoice or in the receipt of goods, the status becomes "
                                       "in exception.",
                                  select=True, copy=False),
        'order_line': fields.one2many('purchase.order.line', 'order_id', 'Order Lines',
                                      states={'approved':[('readonly',True)],
                                              'done':[('readonly',True)]},
                                      copy=True),
        'validator' : fields.many2one('res.users', 'Validated by', readonly=True, copy=False),
        'notes': fields.text('Terms and Conditions'),
        'invoice_ids': fields.many2many('account.invoice', 'purchase_invoice_rel', 'purchase_id',
                                        'invoice_id', 'Invoices', copy=False,
                                        help="Invoices generated for a purchase order"),
        'picking_ids': fields.function(_get_picking_ids, method=True, type='one2many', relation='stock.picking', string='Picking List', help="This is the list of receipts that have been generated for this purchase order."),
        'shipped':fields.boolean('Received', readonly=True, select=True, copy=False,
                                 help="It indicates that a picking has been done"),
        'shipped_rate': fields.function(_shipped_rate, string='Received Ratio', type='float'),
        'invoiced': fields.function(_invoiced, string='Invoice Received', type='boolean', copy=False,
                                    help="It indicates that an invoice has been validated"),
        'invoiced_rate': fields.function(_invoiced_rate, string='Invoiced', type='float'),
        'invoice_method': fields.selection([('manual','Based on Purchase Order lines'),('order','Based on generated draft invoice'),('picking','Based on incoming shipments')], 'Invoicing Control', required=True,
            readonly=True, states={'draft':[('readonly',False)], 'sent':[('readonly',False)],'bid':[('readonly',False)]},
            help="Based on Purchase Order lines: place individual lines in 'Invoice Control / On Purchase Order lines' from where you can selectively create an invoice.\n" \
                "Based on generated invoice: create a draft invoice you can validate later.\n" \
                "Based on incoming shipments: let you create an invoice when receipts are validated."
        ),
        'minimum_planned_date':fields.function(_minimum_planned_date, fnct_inv=_set_minimum_planned_date, string='Expected Date', type='datetime', select=True, help="This is computed as the minimum scheduled date of all purchase order lines' products.",
            store = {
                'purchase.order.line': (_get_order, ['date_planned'], 10),
            }
        ),
        'amount_untaxed': fields.function(_amount_all, digits=0, string='Untaxed Amount',
            store={
                'purchase.order.line': (_get_order, None, 10),
            }, multi="sums", help="The amount without tax", track_visibility='always'),
        'amount_tax': fields.function(_amount_all, digits=0, string='Taxes',
            store={
                'purchase.order.line': (_get_order, None, 10),
            }, multi="sums", help="The tax amount"),
        'amount_total': fields.function(_amount_all, digits=0, string='Total',
            store={
                'purchase.order.line': (_get_order, None, 10),
            }, multi="sums", help="The total amount"),
        'fiscal_position_id': fields.many2one('account.fiscal.position', oldname='fiscal_position', string='Fiscal Position'),
        'payment_term_id': fields.many2one('account.payment.term', 'Payment Term'),
        'incoterm_id': fields.many2one('stock.incoterms', 'Incoterm', help="International Commercial Terms are a series of predefined commercial terms used in international transactions."),
        'product_id': fields.related('order_line', 'product_id', type='many2one', relation='product.product', string='Product'),
        'create_uid': fields.many2one('res.users', 'Responsible'),
        'company_id': fields.many2one('res.company', 'Company', required=True, select=1, states={'confirmed': [('readonly', True)], 'approved': [('readonly', True)]}),
        'journal_id': fields.many2one('account.journal', 'Journal'),
        'bid_date': fields.date('Bid Received On', readonly=True, help="Date on which the bid was received"),
        'bid_validity': fields.date('Bid Valid Until', help="Date on which the bid expired"),
        'picking_type_id': fields.many2one('stock.picking.type', 'Deliver To', help="This will determine picking type of incoming shipment", required=True,
                                           states={'confirmed': [('readonly', True)], 'approved': [('readonly', True)], 'done': [('readonly', True)]}),
        'related_location_id': fields.related('picking_type_id', 'default_location_dest_id', type='many2one', relation='stock.location', string="Related location", store=True),
        'related_usage': fields.related('location_id', 'usage', type='char'),
        'shipment_count': fields.function(_count_all, type='integer', string='Incoming Shipments', multi=True),
        'invoice_count': fields.function(_count_all, type='integer', string='Invoices', multi=True),
        'group_id': fields.many2one('procurement.group', string="Procurement Group"),
    }
    _defaults = {
        'date_order': fields.datetime.now,
        'state': 'draft',
        'name': lambda obj, cr, uid, context: '/',
        'shipped': 0,
        'invoice_method': 'order',
        'invoiced': 0,
        'pricelist_id': lambda self, cr, uid, context: context.get('partner_id', False) and self.pool.get('res.partner').browse(cr, uid, context['partner_id']).property_product_pricelist_purchase.id,
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'purchase.order', context=c),
        'journal_id': _get_journal,
        'currency_id': lambda self, cr, uid, context: self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.currency_id.id,
        'picking_type_id': _get_picking_in,
    }
    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)', 'Order Reference must be unique per Company!'),
    ]
    _name = "purchase.order"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _description = "Purchase Order"
    _order = 'date_order desc, id desc'

    def create(self, cr, uid, vals, context=None):
        if vals.get('name', '/') == '/':
            vals['name'] = self.pool.get('ir.sequence').next_by_code(cr, uid, 'purchase.order') or '/'
        context = dict(context or {}, mail_create_nolog=True)
        order = super(purchase_order, self).create(cr, uid, vals, context=context)
        self.message_post(cr, uid, [order], body=_("RFQ created"), context=context)
        return order

    def unlink(self, cr, uid, ids, context=None):
        purchase_orders = self.read(cr, uid, ids, ['state'], context=context)
        unlink_ids = []
        for s in purchase_orders:
            if s['state'] in ['draft','cancel']:
                unlink_ids.append(s['id'])
            else:
                raise UserError(_('In order to delete a purchase order, you must cancel it first.'))

        # automatically sending subflow.delete upon deletion
        self.signal_workflow(cr, uid, unlink_ids, 'purchase_cancel')

        return super(purchase_order, self).unlink(cr, uid, unlink_ids, context=context)

    def _track_subtype(self, cr, uid, ids, init_values, context=None):
        record = self.browse(cr, uid, ids[0], context=context)
        if 'state' in init_values and record.state == 'approved':
            return 'purchase.mt_rfq_approved'
        elif 'state' in init_values and record.state == 'confirmed':
            return 'purchase.mt_rfq_confirmed'
        elif 'state' in init_values and record.state == 'done':
            return 'purchase.mt_rfq_done'
        return super(purchase_order, self)._track_subtype(cr, uid, ids, init_values, context=context)

    def set_order_line_status(self, cr, uid, ids, status, context=None):
        line = self.pool.get('purchase.order.line')
        order_line_ids = []
        proc_obj = self.pool.get('procurement.order')
        for order in self.browse(cr, uid, ids, context=context):
            order_line_ids += [po_line.id for po_line in order.order_line]
        if order_line_ids:
            line.write(cr, uid, order_line_ids, {'state': status}, context=context)
        if order_line_ids and status == 'cancel':
            procs = proc_obj.search(cr, uid, [('purchase_line_id', 'in', order_line_ids)], context=context)
            if procs:
                proc_obj.write(cr, uid, procs, {'state': 'exception'}, context=context)
        return True

    def button_dummy(self, cr, uid, ids, context=None):
        return True

    def onchange_pricelist(self, cr, uid, ids, pricelist_id, context=None):
        if not pricelist_id:
            return {}
        return {'value': {'currency_id': self.pool.get('product.pricelist').browse(cr, uid, pricelist_id, context=context).currency_id.id}}

    #Destination address is used when dropshipping
    def onchange_dest_address_id(self, cr, uid, ids, address_id, context=None):
        if not address_id:
            return {}
        address = self.pool.get('res.partner')
        values = {}
        supplier = address.browse(cr, uid, address_id, context=context)
        if supplier:
            location_id = supplier.property_stock_customer.id
            values.update({'location_id': location_id})
        return {'value':values}

    def onchange_picking_type_id(self, cr, uid, ids, picking_type_id, context=None):
        value = {}
        if picking_type_id:
            picktype = self.pool.get("stock.picking.type").browse(cr, uid, picking_type_id, context=context)
            if picktype.default_location_dest_id:
                value.update({'location_id': picktype.default_location_dest_id.id, 'related_usage': picktype.default_location_dest_id.usage})
            value.update({'related_location_id': picktype.default_location_dest_id.id})
        return {'value': value}

    def onchange_partner_id(self, cr, uid, ids, partner_id, context=None):
        partner = self.pool.get('res.partner')
        if not partner_id:
            return {'value': {
                'fiscal_position_id': False,
                'payment_term_id': False,
                }}

        company_id = self.pool.get('res.users')._get_company(cr, uid, context=context)
        if not company_id:
            raise osv.except_osv(_('Error!'), _('There is no default company for the current user!'))
        fp = self.pool['account.fiscal.position'].get_fiscal_position(cr, uid, company_id, partner_id, context=context)
        supplier_address = partner.address_get(cr, uid, [partner_id], ['default'], context=context)
        supplier = partner.browse(cr, uid, partner_id, context=context)
        return {'value': {
            'pricelist_id': supplier.property_product_pricelist_purchase.id,
            'fiscal_position_id': fp or supplier.property_account_position and supplier.property_account_position.id or False,
            'payment_term_id': supplier.property_supplier_payment_term.id or False,
            }}

    def invoice_open(self, cr, uid, ids, context=None):
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')

        action_id = mod_obj.xmlid_to_res_id(cr, uid, 'account.action_invoice_tree2')
        result = act_obj.read(cr, uid, action_id, context=context)
        inv_ids = []
        for po in self.browse(cr, uid, ids, context=context):
            inv_ids += [invoice.id for invoice in po.invoice_ids]
        if not inv_ids:
            raise UserError(_('Please create Invoices.'))

        if len(inv_ids) > 1:
            result['domain'] = [('id', 'in', inv_ids)]
        else:
            res = mod_obj.xmlid_to_res_id(cr, uid, 'account.invoice_supplier_form')
            result['views'] = [(res, 'form')]
            result['res_id'] = inv_ids and inv_ids[0] or False
        return result

    def view_invoice(self, cr, uid, ids, context=None):
        '''
        This function returns an action that display existing invoices of given sales order ids. It can either be a in a list or in a form view, if there is only one invoice to show.
        '''
        context = dict(context or {})
        mod_obj = self.pool.get('ir.model.data')
        wizard_obj = self.pool.get('purchase.order.line_invoice')
        #compute the number of invoices to display
        inv_ids = []
        for po in self.browse(cr, uid, ids, context=context):
            if po.invoice_method == 'manual':
                if not po.invoice_ids:
                    context.update({'active_ids' :  [line.id for line in po.order_line]})
                    wizard_obj.makeInvoices(cr, uid, [], context=context)

        for po in self.browse(cr, uid, ids, context=context):
            inv_ids+= [invoice.id for invoice in po.invoice_ids]
        res = mod_obj.get_object_reference(cr, uid, 'account', 'invoice_supplier_form')
        res_id = res and res[1] or False

        return {
            'name': _('Supplier Bills'),
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': [res_id],
            'res_model': 'account.invoice',
            'context': "{'type':'in_invoice', 'journal_type': 'purchase'}",
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
            'res_id': inv_ids and inv_ids[0] or False,
        }

    def view_picking(self, cr, uid, ids, context=None):
        '''
        This function returns an action that display existing picking orders of given purchase order ids.
        '''
        if context is None:
            context = {}
        mod_obj = self.pool.get('ir.model.data')
        dummy, action_id = tuple(mod_obj.get_object_reference(cr, uid, 'stock', 'action_picking_tree'))
        action = self.pool.get('ir.actions.act_window').read(cr, uid, action_id, context=context)

        pick_ids = []
        for po in self.browse(cr, uid, ids, context=context):
            pick_ids += [picking.id for picking in po.picking_ids]

        #override the context to get rid of the default filtering on picking type
        action['context'] = {}
        #choose the view_mode accordingly
        if len(pick_ids) > 1:
            action['domain'] = "[('id','in',[" + ','.join(map(str, pick_ids)) + "])]"
        else:
            res = mod_obj.get_object_reference(cr, uid, 'stock', 'view_picking_form')
            action['views'] = [(res and res[1] or False, 'form')]
            action['res_id'] = pick_ids and pick_ids[0] or False
        return action


    def wkf_approve_order(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'approved', 'date_approve': fields.date.context_today(self,cr,uid,context=context)})
        return True

    def wkf_bid_received(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'bid', 'bid_date': fields.date.context_today(self,cr,uid,context=context)})

    def wkf_send_rfq(self, cr, uid, ids, context=None):
        '''
        This function opens a window to compose an email, with the edi purchase template message loaded by default
        '''
        if not context:
            context= {}
        ir_model_data = self.pool.get('ir.model.data')
        try:
            if context.get('send_rfq', False):
                template_id = ir_model_data.get_object_reference(cr, uid, 'purchase', 'email_template_edi_purchase')[1]
            else:
                template_id = ir_model_data.get_object_reference(cr, uid, 'purchase', 'email_template_edi_purchase_done')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference(cr, uid, 'mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False 
        ctx = dict(context)
        ctx.update({
            'default_model': 'purchase.order',
            'default_res_id': ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
        })
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    def print_quotation(self, cr, uid, ids, context=None):
        '''
        This function prints the request for quotation and mark it as sent, so that we can see more easily the next step of the workflow
        '''
        assert len(ids) == 1, 'This option should only be used for a single id at a time'
        self.signal_workflow(cr, uid, ids, 'send_rfq')
        return self.pool['report'].get_action(cr, uid, ids, 'purchase.report_purchasequotation', context=context)

    def wkf_confirm_order(self, cr, uid, ids, context=None):
        todo = []
        for po in self.browse(cr, uid, ids, context=context):
            if not po.order_line:
                raise UserError(_('You cannot confirm a purchase order without any purchase order line.'))
            if po.invoice_method == 'picking' and not any([l.product_id and l.product_id.type in ('product', 'consu') for l in po.order_line]):
                raise osv.except_osv(
                    _('Error!'),
                    _("You cannot confirm a purchase order with Invoice Control Method 'Based on incoming shipments' that doesn't contain any stockable item."))
            for line in po.order_line:
                if line.state=='draft':
                    todo.append(line.id)        
        self.pool.get('purchase.order.line').action_confirm(cr, uid, todo, context)
        for id in ids:
            self.write(cr, uid, [id], {'state' : 'confirmed', 'validator' : uid})
        return True

    def _choose_account_from_po_line(self, cr, uid, po_line, context=None):
        fiscal_obj = self.pool.get('account.fiscal.position')
        property_obj = self.pool.get('ir.property')
        if po_line.product_id:
            acc_id = po_line.product_id.property_account_expense.id
            if not acc_id:
                acc_id = po_line.product_id.categ_id.property_account_expense_categ.id
            if not acc_id:
                raise UserError(_('Define an expense account for this product: "%s" (id:%d).') % (po_line.product_id.name, po_line.product_id.id,))
        else:
            acc_id = property_obj.get(cr, uid, 'property_account_expense_categ', 'product.category', context=context).id
        fpos = po_line.order_id.fiscal_position_id or False
        #For anglo-saxon accounting
        account_id = fiscal_obj.map_account(cr, uid, fpos, acc_id)
        if po_line.company_id.anglo_saxon_accounting and po_line.product_id and not po_line.product_id.type == 'service':
            acc_id = po_line.product_id.property_stock_account_input and po_line.product_id.property_stock_account_input.id
            if not acc_id:
                acc_id = po_line.product_id.categ_id.property_stock_account_input_categ and po_line.product_id.categ_id.property_stock_account_input_categ.id
            if acc_id:
                fpos = po_line.order_id.fiscal_position_id or False
                account_id = self.pool.get('account.fiscal.position').map_account(cr, uid, fpos, acc_id)
        return account_id

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
            'invoice_line_tax_ids': [(6, 0, [x.id for x in order_line.taxes_id])],
            'account_analytic_id': order_line.account_analytic_id.id or False,
            'purchase_line_id': order_line.id,
        }

    def _prepare_invoice(self, cr, uid, order, line_ids, context=None):
        """Prepare the dict of values to create the new invoice for a
           purchase order. This method may be overridden to implement custom
           invoice generation (making sure to call super() to establish
           a clean extension chain).

           :param browse_record order: purchase.order record to invoice
           :param list(int) line_ids: list of invoice line IDs that must be
                                      attached to the invoice
           :return: dict of value to create() the invoice
        """
        journal_ids = self.pool['account.journal'].search(
                            cr, uid, [('type', '=', 'purchase'),
                                      ('company_id', '=', order.company_id.id)],
                            limit=1)
        if not journal_ids:
            raise UserError(_('Define purchase journal for this company: "%s" (id:%d).') % (order.company_id.name, order.company_id.id))
        return {
            'name': order.partner_ref or order.name,
            'reference': order.partner_ref or order.name,
            'account_id': order.partner_id.property_account_payable.id,
            'type': 'in_invoice',
            'partner_id': order.partner_id.id,
            'currency_id': order.currency_id.id,
            'journal_id': len(journal_ids) and journal_ids[0] or False,
            'invoice_line_ids': [(6, 0, line_ids)],
            'origin': order.name,
            'fiscal_position_id': order.fiscal_position_id.id or False,
            'payment_term_id': order.payment_term_id.id or False,
            'company_id': order.company_id.id,
        }

    def action_cancel_draft(self, cr, uid, ids, context=None):
        if not len(ids):
            return False
        self.write(cr, uid, ids, {'state':'draft','shipped':0})
        self.set_order_line_status(cr, uid, ids, 'draft', context=context)
        for p_id in ids:
            # Deleting the existing instance of workflow for PO
            self.delete_workflow(cr, uid, [p_id]) # TODO is it necessary to interleave the calls?
            self.create_workflow(cr, uid, [p_id])
        return True

    def wkf_po_done(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'done'}, context=context)
        self.set_order_line_status(cr, uid, ids, 'done', context=context)

    def action_invoice_create(self, cr, uid, ids, context=None):
        """Generates invoice for given ids of purchase orders and links that invoice ID to purchase order.
        :param ids: list of ids of purchase orders.
        :return: ID of created invoice.
        :rtype: int
        """
        context = dict(context or {})
        
        inv_obj = self.pool.get('account.invoice')
        inv_line_obj = self.pool.get('account.invoice.line')

        res = False
        uid_company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        for order in self.browse(cr, uid, ids, context=context):
            context.pop('force_company', None)
            if order.company_id.id != uid_company_id:
                #if the company of the document is different than the current user company, force the company in the context
                #then re-do a browse to read the property fields for the good company.
                context['force_company'] = order.company_id.id
                order = self.browse(cr, uid, order.id, context=context)
            
            # generate invoice line correspond to PO line and link that to created invoice (inv_id) and PO line
            inv_lines = []
            for po_line in order.order_line:
                acc_id = self._choose_account_from_po_line(cr, uid, po_line, context=context)
                inv_line_data = self._prepare_inv_line(cr, uid, acc_id, po_line, context=context)
                inv_line_id = inv_line_obj.create(cr, uid, inv_line_data, context=context)
                inv_lines.append(inv_line_id)
                po_line.write({'invoice_lines': [(4, inv_line_id)]})

            # get invoice data and create invoice
            inv_data = self._prepare_invoice(cr, uid, order, inv_lines, context=context)
            inv_id = inv_obj.create(cr, uid, inv_data, context=context)

            # Link this new invoice to related purchase order
            order.write({'invoice_ids': [(4, inv_id)]})
            res = inv_id
        return res

    def invoice_done(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'approved'}, context=context)
        return True

    def has_stockable_product(self, cr, uid, ids, *args):
        for order in self.browse(cr, uid, ids):
            for order_line in order.order_line:
                if order_line.product_id and order_line.product_id.type in ('product', 'consu'):
                    return True
        return False

    def wkf_action_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'cancel'}, context=context)
        self.set_order_line_status(cr, uid, ids, 'cancel', context=context)

    def action_cancel(self, cr, uid, ids, context=None):
        for purchase in self.browse(cr, uid, ids, context=context):
            for pick in purchase.picking_ids:
                for move in pick.move_lines:
                    if pick.state == 'done':
                        raise UserError(_('Unable to cancel the purchase order %s.') % (purchase.name) + _('You have already received some goods for it.  '))
            self.pool.get('stock.picking').action_cancel(cr, uid, [x.id for x in purchase.picking_ids if x.state != 'cancel'], context=context)
            for inv in purchase.invoice_ids:
                if inv and inv.state not in ('cancel', 'draft'):
                    raise UserError(_("Unable to cancel this purchase order.") + " " + _("You must first cancel all invoices related to this purchase order."))
            self.pool.get('account.invoice') \
                .signal_workflow(cr, uid, map(attrgetter('id'), purchase.invoice_ids), 'invoice_cancel')
        self.signal_workflow(cr, uid, ids, 'purchase_cancel')
        return True

    def _prepare_order_line_move(self, cr, uid, order, order_line, picking_id, group_id, context=None):
        ''' prepare the stock move data from the PO line. This function returns a list of dictionary ready to be used in stock.move's create()'''
        product_uom = self.pool.get('product.uom')
        price_unit = order_line.price_unit
        if order_line.product_uom.id != order_line.product_id.uom_id.id:
            price_unit *= order_line.product_uom.factor / order_line.product_id.uom_id.factor
        if order.currency_id.id != order.company_id.currency_id.id:
            #we don't round the price_unit, as we may want to store the standard price with more digits than allowed by the currency
            price_unit = self.pool.get('res.currency').compute(cr, uid, order.currency_id.id, order.company_id.currency_id.id, price_unit, round=False, context=context)
        res = []
        move_template = {
            'name': order_line.name or '',
            'product_id': order_line.product_id.id,
            'product_uom': order_line.product_uom.id,
            'product_uos': order_line.product_uom.id,
            'date': order.date_order,
            'date_expected': order_line.date_planned,
            'location_id': order.partner_id.property_stock_supplier.id,
            'location_dest_id': order.location_id.id,
            'picking_id': picking_id,
            'partner_id': order.dest_address_id.id,
            'move_dest_id': False,
            'state': 'draft',
            'purchase_line_id': order_line.id,
            'company_id': order.company_id.id,
            'price_unit': price_unit,
            'picking_type_id': order.picking_type_id.id,
            'group_id': group_id,
            'procurement_id': False,
            'origin': order.name,
            'route_ids': order.picking_type_id.warehouse_id and [(6, 0, [x.id for x in order.picking_type_id.warehouse_id.route_ids])] or [],
            'warehouse_id':order.picking_type_id.warehouse_id.id,
            'invoice_state': order.invoice_method == 'picking' and '2binvoiced' or 'none',
        }

        diff_quantity = order_line.product_qty
        for procurement in order_line.procurement_ids:
            procurement_qty = product_uom._compute_qty(cr, uid, procurement.product_uom.id, procurement.product_qty, to_uom_id=order_line.product_uom.id)
            tmp = move_template.copy()
            tmp.update({
                'product_uom_qty': min(procurement_qty, diff_quantity),
                'product_uos_qty': min(procurement_qty, diff_quantity),
                'move_dest_id': procurement.move_dest_id.id,  #move destination is same as procurement destination
                'procurement_id': procurement.id,
                'invoice_state': procurement.rule_id.invoice_state or (procurement.location_id and procurement.location_id.usage == 'customer' and procurement.invoice_state=='2binvoiced' and '2binvoiced') or (order.invoice_method == 'picking' and '2binvoiced') or 'none', #dropship case takes from sale
                'propagate': procurement.rule_id.propagate,
            })
            diff_quantity -= min(procurement_qty, diff_quantity)
            res.append(tmp)
        #if the order line has a bigger quantity than the procurement it was for (manually changed or minimal quantity), then
        #split the future stock move in two because the route followed may be different.
        if float_compare(diff_quantity, 0.0, precision_rounding=order_line.product_uom.rounding) > 0:
            move_template['product_uom_qty'] = diff_quantity
            move_template['product_uos_qty'] = diff_quantity
            res.append(move_template)
        return res

    def _create_stock_moves(self, cr, uid, order, order_lines, picking_id=False, context=None):
        """Creates appropriate stock moves for given order lines, whose can optionally create a
        picking if none is given or no suitable is found, then confirms the moves, makes them
        available, and confirms the pickings.

        If ``picking_id`` is provided, the stock moves will be added to it, otherwise a standard
        incoming picking will be created to wrap the stock moves (default behavior of the stock.move)

        Modules that wish to customize the procurements or partition the stock moves over
        multiple stock pickings may override this method and call ``super()`` with
        different subsets of ``order_lines`` and/or preset ``picking_id`` values.

        :param browse_record order: purchase order to which the order lines belong
        :param list(browse_record) order_lines: purchase order line records for which picking
                                                and moves should be created.
        :param int picking_id: optional ID of a stock picking to which the created stock moves
                               will be added. A new picking will be created if omitted.
        :return: None
        """
        stock_move = self.pool.get('stock.move')
        todo_moves = []
        if order.group_id:
            new_group = order.group_id.id
        else:
            new_group = self.pool.get("procurement.group").create(cr, uid, {'name': order.name, 'partner_id': order.partner_id.id}, context=context)

        for order_line in order_lines:
            if not order_line.product_id:
                continue

            if order_line.product_id.type in ('product', 'consu'):
                for vals in self._prepare_order_line_move(cr, uid, order, order_line, picking_id, new_group, context=context):
                    move = stock_move.create(cr, uid, vals, context=context)
                    todo_moves.append(move)

        todo_moves = stock_move.action_confirm(cr, uid, todo_moves)
        stock_move.force_assign(cr, uid, todo_moves)

    def test_moves_done(self, cr, uid, ids, context=None):
        '''PO is done at the delivery side if all the incoming shipments are done'''
        for purchase in self.browse(cr, uid, ids, context=context):
            for picking in purchase.picking_ids:
                if picking.state != 'done':
                    return False
        return True

    def test_moves_except(self, cr, uid, ids, context=None):
        ''' PO is in exception at the delivery side if one of the picking is canceled
            and the other pickings are completed (done or canceled)
        '''
        at_least_one_canceled = False
        alldoneorcancel = True
        for purchase in self.browse(cr, uid, ids, context=context):
            for picking in purchase.picking_ids:
                if picking.state == 'cancel':
                    at_least_one_canceled = True
                if picking.state not in ['done', 'cancel']:
                    alldoneorcancel = False
        return at_least_one_canceled and alldoneorcancel

    def move_lines_get(self, cr, uid, ids, *args):
        res = []
        for order in self.browse(cr, uid, ids, context={}):
            for line in order.order_line:
                res += [x.id for x in line.move_ids]
        return res

    def action_picking_create(self, cr, uid, ids, context=None):
        for order in self.browse(cr, uid, ids):
            picking_vals = {
                'picking_type_id': order.picking_type_id.id,
                'partner_id': order.partner_id.id,
                'date': order.date_order,
                'origin': order.name
            }
            picking_id = self.pool.get('stock.picking').create(cr, uid, picking_vals, context=context)
            self._create_stock_moves(cr, uid, order, order.order_line, picking_id, context=context)

    def picking_done(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'shipped':1,'state':'approved'}, context=context)
        # Do check on related procurements:
        proc_obj = self.pool.get("procurement.order")
        po_lines = []
        for po in self.browse(cr, uid, ids, context=context):
            po_lines += [x.id for x in po.order_line]
        if po_lines:
            procs = proc_obj.search(cr, uid, [('purchase_line_id', 'in', po_lines)], context=context)
            if procs:
                proc_obj.check(cr, uid, procs, context=context)
        for id in ids:
            self.message_post(cr, uid, id, body=_("Products received"), context=context)
        return True

    def do_merge(self, cr, uid, ids, context=None):
        """
        To merge similar type of purchase orders.
        Orders will only be merged if:
        * Purchase Orders are in draft
        * Purchase Orders belong to the same partner
        * Purchase Orders are have same stock location, same pricelist, same currency
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
        def make_key(br, fields):
            list_key = []
            for field in fields:
                field_val = getattr(br, field)
                if field in ('product_id', 'account_analytic_id'):
                    if not field_val:
                        field_val = False
                if isinstance(field_val, browse_record):
                    field_val = field_val.id
                elif isinstance(field_val, browse_null):
                    field_val = False
                elif isinstance(field_val, browse_record_list):
                    field_val = ((6, 0, tuple([v.id for v in field_val])),)
                list_key.append((field, field_val))
            list_key.sort()
            return tuple(list_key)

        context = dict(context or {})

        # Compute what the new orders should contain
        new_orders = {}

        order_lines_to_move = {}
        for porder in [order for order in self.browse(cr, uid, ids, context=context) if order.state == 'draft']:
            order_key = make_key(porder, ('partner_id', 'location_id', 'pricelist_id', 'currency_id'))
            new_order = new_orders.setdefault(order_key, ({}, []))
            new_order[1].append(porder.id)
            order_infos = new_order[0]
            order_lines_to_move.setdefault(order_key, [])

            if not order_infos:
                order_infos.update({
                    'origin': porder.origin,
                    'date_order': porder.date_order,
                    'partner_id': porder.partner_id.id,
                    'dest_address_id': porder.dest_address_id.id,
                    'picking_type_id': porder.picking_type_id.id,
                    'location_id': porder.location_id.id,
                    'pricelist_id': porder.pricelist_id.id,
                    'currency_id': porder.currency_id.id,
                    'state': 'draft',
                    'order_line': {},
                    'notes': '%s' % (porder.notes or '',),
                    'fiscal_position_id': porder.fiscal_position_id and porder.fiscal_position_id.id or False,
                })
            else:
                if porder.date_order < order_infos['date_order']:
                    order_infos['date_order'] = porder.date_order
                if porder.notes:
                    order_infos['notes'] = (order_infos['notes'] or '') + ('\n%s' % (porder.notes,))
                if porder.origin:
                    order_infos['origin'] = (order_infos['origin'] or '') + ' ' + porder.origin

            order_lines_to_move[order_key] += [order_line.id for order_line in porder.order_line]

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
            order_data['order_line'] = [(6, 0, order_lines_to_move[order_key])]

            # create the new order
            context.update({'mail_create_nolog': True})
            neworder_id = self.create(cr, uid, order_data)
            self.message_post(cr, uid, [neworder_id], body=_("RFQ created"), context=context)
            orders_info.update({neworder_id: old_ids})
            allorders.append(neworder_id)

            # make triggers pointing to the old orders point to the new order
            for old_id in old_ids:
                self.redirect_workflow(cr, uid, [(old_id, neworder_id)])
                self.signal_workflow(cr, uid, [old_id], 'purchase_cancel')

        return orders_info


class purchase_order_line(osv.osv):
    def _amount_line(self, cr, uid, ids, prop, arg, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            cur = line.order_id.pricelist_id.currency_id
            res[line.id] = line.taxes_id.compute_all(line.price_unit, cur, line.product_qty, product=line.product_id, partner=line.order_id.partner_id)['total_excluded']
        return res

    def _get_uom_id(self, cr, uid, context=None):
        try:
            proxy = self.pool.get('ir.model.data')
            result = proxy.get_object_reference(cr, uid, 'product', 'product_uom_unit')
            return result[1]
        except Exception, ex:
            return False

    _columns = {
        'name': fields.text('Description', required=True),
        'product_qty': fields.float('Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), required=True),
        'date_planned': fields.datetime('Scheduled Date', required=True, select=True),
        'taxes_id': fields.many2many('account.tax', 'purchase_order_taxe', 'ord_id', 'tax_id', 'Taxes'),
        'product_uom': fields.many2one('product.uom', 'Product Unit of Measure', required=True),
        'product_id': fields.many2one('product.product', 'Product', domain=[('purchase_ok','=',True)], change_default=True),
        'move_ids': fields.one2many('stock.move', 'purchase_line_id', 'Reservation', readonly=True, ondelete='set null'),
        'price_unit': fields.float('Unit Price', required=True, digits_compute= dp.get_precision('Product Price')),
        'price_subtotal': fields.function(_amount_line, string='Subtotal', digits=0),
        'order_id': fields.many2one('purchase.order', 'Order Reference', select=True, required=True, ondelete='cascade'),
        'account_analytic_id':fields.many2one('account.analytic.account', 'Analytic Account',),
        'company_id': fields.related('order_id','company_id',type='many2one',relation='res.company',string='Company', store=True, readonly=True),
        'state': fields.selection([('draft', 'Draft'), ('confirmed', 'Confirmed'), ('done', 'Done'), ('cancel', 'Cancelled')],
                                  'Status', required=True, readonly=True, copy=False,
                                  help=' * The \'Draft\' status is set automatically when purchase order in draft status. \
                                       \n* The \'Confirmed\' status is set automatically as confirm when purchase order in confirm status. \
                                       \n* The \'Done\' status is set automatically when purchase order is set as done. \
                                       \n* The \'Cancelled\' status is set automatically when user cancel purchase order.'),
        'invoice_lines': fields.many2many('account.invoice.line', 'purchase_order_line_invoice_rel',
                                          'order_line_id', 'invoice_id', 'Invoice Lines',
                                          readonly=True, copy=False),
        'invoiced': fields.boolean('Invoiced', readonly=True, copy=False),
        'partner_id': fields.related('order_id', 'partner_id', string='Partner', readonly=True, type="many2one", relation="res.partner", store=True),
        'date_order': fields.related('order_id', 'date_order', string='Order Date', readonly=True, type="datetime"),
        'procurement_ids': fields.one2many('procurement.order', 'purchase_line_id', string='Associated procurements'),
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

    def unlink(self, cr, uid, ids, context=None):
        for line in self.browse(cr, uid, ids, context=context):
            if line.order_id.state in ['approved', 'done'] and line.state not in ['draft', 'cancel']:
                raise UserError(_('Cannot delete a purchase order line which is in state \'%s\'.') %(line.state,))
        procurement_obj = self.pool.get('procurement.order')
        procurement_ids_to_except = procurement_obj.search(cr, uid, [('purchase_line_id', 'in', ids)], context=context)
        if procurement_ids_to_except:
            self.pool['procurement.order'].write(cr, uid, procurement_ids_to_except, {'state': 'exception'}, context=context)
        return super(purchase_order_line, self).unlink(cr, uid, ids, context=context)

    def onchange_product_uom(self, cr, uid, ids, pricelist_id, product_id, qty, uom_id,
            partner_id, date_order=False, fiscal_position_id=False, date_planned=False,
            name=False, price_unit=False, state='draft', context=None):
        """
        onchange handler of product_uom.
        """
        if context is None:
            context = {}
        if not uom_id:
            return {'value': {'price_unit': price_unit or 0.0, 'name': name or '', 'product_uom' : uom_id or False}}
        context = dict(context, purchase_uom_check=True)
        return self.onchange_product_id(cr, uid, ids, pricelist_id, product_id, qty, uom_id,
            partner_id, date_order=date_order, fiscal_position_id=fiscal_position_id, date_planned=date_planned,
            name=name, price_unit=price_unit, state=state, replace=False, context=context)

    def _get_date_planned(self, cr, uid, supplier_info, date_order_str, context=None):
        """Return the datetime value to use as Schedule Date (``date_planned``) for
           PO Lines that correspond to the given product.supplierinfo,
           when ordered at `date_order_str`.

           :param browse_record | False supplier_info: product.supplierinfo, used to
               determine delivery delay (if False, default delay = 0)
           :param str date_order_str: date of order field, as a string in
               DEFAULT_SERVER_DATETIME_FORMAT
           :rtype: datetime
           :return: desired Schedule Date for the PO line
        """
        supplier_delay = int(supplier_info.delay) if supplier_info else 0
        return datetime.strptime(date_order_str, DEFAULT_SERVER_DATETIME_FORMAT) + relativedelta(days=supplier_delay)

    def action_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'cancel'}, context=context)
        # We will group by PO first, so we do the check only once for each PO
        purchase_orders = list(set([x.order_id for x in self.browse(cr, uid, ids, context=context)]))
        for purchase in purchase_orders:
            if all([l.state == 'cancel' for l in purchase.order_line]):
                self.pool.get('purchase.order').action_cancel(cr, uid, [purchase.id], context=context)

    def _check_product_uom_group(self, cr, uid, context=None):
        group_uom = self.pool.get('ir.model.data').get_object(cr, uid, 'product', 'group_uom')
        res = [user for user in group_uom.users if user.id == uid]
        return len(res) and True or False

    def onchange_product_id(self, cr, uid, ids, pricelist_id, product_id, qty, uom_id,
            partner_id, date_order=False, fiscal_position_id=False, date_planned=False,
            name=False, price_unit=False, state='draft', replace=True, context=None):
        """
        onchange handler of product_id.
        """
        if context is None:
            context = {}

        res = {'value': {'price_unit': price_unit or 0.0, 'name': name or '', 'product_uom' : uom_id or False}}
        if not product_id:
            return res

        product_product = self.pool.get('product.product')
        product_uom = self.pool.get('product.uom')
        res_partner = self.pool.get('res.partner')
        product_pricelist = self.pool.get('product.pricelist')
        account_fiscal_position = self.pool.get('account.fiscal.position')
        account_tax = self.pool.get('account.tax')

        # - check for the presence of partner_id and pricelist_id
        #if not partner_id:
        #    raise UserError(_('Select a partner in purchase order to choose a product.'))
        #if not pricelist_id:
        #    raise UserError(_('Select a price list in the purchase order form before choosing a product.'))

        # - determine name and notes based on product in partner lang.
        context_partner = context.copy()
        if partner_id:
            lang = res_partner.browse(cr, uid, partner_id).lang
            context_partner.update( {'lang': lang, 'partner_id': partner_id} )
        product = product_product.browse(cr, uid, product_id, context=context_partner)
        if replace:
            #call name_get() with partner in the context to eventually match name and description in the seller_ids field
            dummy, name = product_product.name_get(cr, uid, product_id, context=context_partner)[0]
            if product.description_purchase:
                name += '\n' + product.description_purchase
            res['value'].update({'name': name})

        # - set a domain on product_uom
        res['domain'] = {'product_uom': [('category_id','=',product.uom_id.category_id.id)]}

        # - check that uom and product uom belong to the same category
        product_uom_po_id = product.uom_po_id.id
        if not uom_id:
            uom_id = product_uom_po_id

        if product.uom_id.category_id.id != product_uom.browse(cr, uid, uom_id, context=context).category_id.id:
            if context.get('purchase_uom_check') and self._check_product_uom_group(cr, uid, context=context):
                res['warning'] = {'title': _('Warning!'), 'message': _('Selected Unit of Measure does not belong to the same category as the product Unit of Measure.')}
            uom_id = product_uom_po_id

        res['value'].update({'product_uom': uom_id})

        # - determine product_qty and date_planned based on seller info
        if not date_order:
            date_order = fields.datetime.now()


        supplierinfo = False
        precision = self.pool.get('decimal.precision').precision_get(cr, uid, 'Product Unit of Measure')
        for supplier in product.seller_ids:
            if partner_id and (supplier.name.id == partner_id):
                supplierinfo = supplier
                if supplierinfo.product_uom.id != uom_id:
                    res['warning'] = {'title': _('Warning!'), 'message': _('The selected supplier only sells this product by %s') % supplierinfo.product_uom.name }
                min_qty = product_uom._compute_qty(cr, uid, supplierinfo.product_uom.id, supplierinfo.min_qty, to_uom_id=uom_id)
                if float_compare(min_qty , qty, precision_digits=precision) == 1: # If the supplier quantity is greater than entered from user, set minimal.
                    if qty:
                        res['warning'] = {'title': _('Warning!'), 'message': _('The selected supplier has a minimal quantity set to %s %s, you should not purchase less.') % (supplierinfo.min_qty, supplierinfo.product_uom.name)}
                    qty = min_qty
        dt = self._get_date_planned(cr, uid, supplierinfo, date_order, context=context).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        qty = qty or 1.0
        res['value'].update({'date_planned': date_planned or dt})
        if qty:
            res['value'].update({'product_qty': qty})

        price = price_unit
        if price_unit is False or price_unit is None:
            # - determine price_unit and taxes_id
            if pricelist_id:
                date_order_str = datetime.strptime(date_order, DEFAULT_SERVER_DATETIME_FORMAT).strftime(DEFAULT_SERVER_DATE_FORMAT)
                price = product_pricelist.price_get(cr, uid, [pricelist_id],
                        product.id, qty or 1.0, partner_id or False, {'uom': uom_id, 'date': date_order_str})[pricelist_id]
            else:
                price = product.standard_price

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


class procurement_rule(osv.osv):
    _inherit = 'procurement.rule'

    def _get_action(self, cr, uid, context=None):
        return [('buy', _('Buy'))] + super(procurement_rule, self)._get_action(cr, uid, context=context)


class procurement_order(osv.osv):
    _inherit = 'procurement.order'
    _columns = {
        'purchase_line_id': fields.many2one('purchase.order.line', 'Purchase Order Line'),
        'purchase_id': fields.related('purchase_line_id', 'order_id', type='many2one', relation='purchase.order', string='Purchase Order'),
    }

    def propagate_cancels(self, cr, uid, ids, context=None):
        purchase_line_obj = self.pool.get('purchase.order.line')
        lines_to_cancel = []
        uom_obj = self.pool.get("product.uom")
        for procurement in self.browse(cr, uid, ids, context=context):
            if procurement.rule_id.action == 'buy' and procurement.purchase_line_id:
                if procurement.purchase_line_id.state not in ('draft', 'cancel'):
                    raise UserError(
                        _('Can not cancel this procurement like this as the related purchase order has been confirmed already.  Please cancel the purchase order first. '))

                new_qty, new_price = self._calc_new_qty_price(cr, uid, procurement, cancel=True, context=context)
                if new_qty != procurement.purchase_line_id.product_qty:
                    purchase_line_obj.write(cr, uid, [procurement.purchase_line_id.id], {'product_qty': new_qty, 'price_unit': new_price}, context=context)
                if float_compare(new_qty, 0.0, precision_rounding=procurement.product_uom.rounding) != 1:
                    if procurement.purchase_line_id.id not in lines_to_cancel:
                        lines_to_cancel += [procurement.purchase_line_id.id]
        if lines_to_cancel:
            purchase_line_obj.action_cancel(cr, uid, lines_to_cancel, context=context)
            purchase_line_obj.unlink(cr, uid, lines_to_cancel, context=context)
        return super(procurement_order, self).propagate_cancels(cr, uid, ids, context=context)

    def _run(self, cr, uid, procurement, context=None):
        if procurement.rule_id and procurement.rule_id.action == 'buy':
            #make a purchase order for the procurement
            return self.make_po(cr, uid, [procurement.id], context=context)[procurement.id]
        return super(procurement_order, self)._run(cr, uid, procurement, context=context)

    #TODO: Autocommit needed?
    def run(self, cr, uid, ids, autocommit=False, context=None):
        procs = self.browse(cr, uid, ids, context=context)
        to_assign = [x for x in procs if x.state not in ('running', 'done')]
        self._assign_multi(cr, uid, to_assign, context=context)
        buy_ids = [x.id for x in to_assign if x.rule_id and x.rule_id.action == 'buy']
        if buy_ids:
            result_dict = self.make_po(cr, uid, buy_ids, context=context)
            runnings = []
            exceptions = []
            for proc in result_dict.keys():
                if result_dict[proc]:
                    runnings += [proc]
                else:
                    exceptions += [proc]
            if runnings:
                self.write(cr, uid, runnings, {'state': 'running'}, context=context)
            if exceptions:
                self.write(cr, uid, exceptions, {'state': 'exception'}, context=context)
        set_others = set(ids) - set(buy_ids)
        return super(procurement_order, self).run(cr, uid, list(set_others), context=context)

    def _check(self, cr, uid, procurement, context=None):
        if procurement.purchase_line_id and procurement.purchase_line_id.order_id.shipped:  # TOCHECK: does it work for several deliveries?
            return True
        return super(procurement_order, self)._check(cr, uid, procurement, context=context)

    def _check_supplier_info(self, cr, uid, ids, context=None):
        ''' Check the supplier info field of a product and write an error message on the procurement if needed.
        Returns True if all needed information is there, False if some configuration mistake is detected.
        '''
        partner_obj = self.pool.get('res.partner')
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        for procurement in self.browse(cr, uid, ids, context=context):
            message = ''
            partner = procurement.product_id.seller_id #Taken Main Supplier of Product of Procurement.

            if not procurement.product_id.seller_ids:
                message = _('No supplier defined for this product !')
            elif not partner:
                message = _('No default supplier defined for this product')
            elif not partner_obj.address_get(cr, uid, [partner.id], ['delivery'])['delivery']:
                message = _('No address defined for the supplier')

            if message:
                if procurement.message != message:
                    cr.execute('update procurement_order set message=%s where id=%s', (message, procurement.id))
                return False

            if user.company_id and user.company_id.partner_id:
                if partner.id == user.company_id.partner_id.id:
                    raise UserError(_('The product "%s" has been defined with your company as reseller which seems to be a configuration error!' % procurement.product_id.name))

        return True

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

    def _get_product_supplier(self, cr, uid, procurement, context=None):
        ''' returns the main supplier of the procurement's product given as argument'''
        supplierinfo = self.pool['product.supplierinfo']
        company_supplier = supplierinfo.search(cr, uid,
            [('product_tmpl_id', '=', procurement.product_id.product_tmpl_id.id), ('company_id', '=', procurement.company_id.id)], limit=1, context=context)
        if company_supplier:
            return supplierinfo.browse(cr, uid, company_supplier[0], context=context).name
        return procurement.product_id.seller_id

    def _get_po_line_values_from_procs(self, cr, uid, procurements, partner, schedule_date, context=None):
        res = {}
        if context is None:
            context = {}
        uom_obj = self.pool.get('product.uom')
        pricelist_obj = self.pool.get('product.pricelist')
        prod_obj = self.pool.get('product.product')
        acc_pos_obj = self.pool.get('account.fiscal.position')

        pricelist_id = partner.property_product_pricelist_purchase.id
        prices_qty = []
        for procurement in procurements:
            seller_qty = procurement.product_id.seller_qty
            uom_id = procurement.product_id.uom_po_id.id
            qty = uom_obj._compute_qty(cr, uid, procurement.product_uom.id, procurement.product_qty, uom_id)
            if seller_qty:
                qty = max(qty, seller_qty)
            prices_qty += [(procurement.product_id, qty, partner)]
        prices = pricelist_obj.price_get_multi(cr, uid, [pricelist_id], prices_qty)

        #Passing partner_id to context for purchase order line integrity of Line name
        new_context = context.copy()
        new_context.update({'lang': partner.lang, 'partner_id': partner.id})
        names = prod_obj.name_get(cr, uid, [x.product_id.id for x in procurements], context=context)
        names_dict = {}
        for id, name in names:
            names_dict[id] = name
        for procurement in procurements:
            taxes_ids = procurement.product_id.supplier_taxes_id
            taxes = acc_pos_obj.map_tax(cr, uid, partner.property_account_position, taxes_ids)
            name = names_dict[procurement.product_id.id]
            if procurement.product_id.description_purchase:
                name += '\n' + procurement.product_id.description_purchase
            price = prices[procurement.product_id.id][pricelist_id]

            values = {
                'name': name,
                'product_qty': qty,
                'product_id': procurement.product_id.id,
                'product_uom': procurement.product_id.uom_po_id.id,
                'price_unit': price or 0.0,
                'date_planned': schedule_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                'taxes_id': [(6, 0, taxes)],
                'procurement_ids': [(4, procurement.id)]
                }
            res[procurement.id] = values
        return res

    def _calc_new_qty_price(self, cr, uid, procurement, po_line=None, cancel=False, context=None):
        if not po_line:
            po_line = procurement.purchase_line_id

        uom_obj = self.pool.get('product.uom')
        qty = uom_obj._compute_qty(cr, uid, procurement.product_uom.id, procurement.product_qty,
            procurement.product_id.uom_po_id.id)
        if cancel:
            qty = -qty

        # Make sure we use the minimum quantity of the partner corresponding to the PO
        if po_line.product_id.seller_id.id == po_line.order_id.partner_id.id:
            supplierinfo_min_qty = po_line.product_id.seller_qty
        else:
            supplierinfo_obj = self.pool.get('product.supplierinfo')
            supplierinfo_ids = supplierinfo_obj.search(cr, uid, [('name', '=', po_line.order_id.partner_id.id), ('product_tmpl_id', '=', po_line.product_id.product_tmpl_id.id)])
            supplierinfo_min_qty = supplierinfo_obj.browse(cr, uid, supplierinfo_ids).min_qty

        if supplierinfo_min_qty == 0.0:
            qty += po_line.product_qty
        else:
            # Recompute quantity by adding existing running procurements.
            for proc in po_line.procurement_ids:
                qty += uom_obj._compute_qty(cr, uid, proc.product_uom.id, proc.product_qty,
                    proc.product_id.uom_po_id.id) if proc.state == 'running' else 0.0
            qty = max(qty, supplierinfo_min_qty) if qty > 0.0 else 0.0

        price = po_line.price_unit
        if qty != po_line.product_qty:
            pricelist_obj = self.pool.get('product.pricelist')
            pricelist_id = po_line.order_id.partner_id.property_product_pricelist_purchase.id
            price = pricelist_obj.price_get(cr, uid, [pricelist_id], procurement.product_id.id, qty, po_line.order_id.partner_id.id, {'uom': procurement.product_uom.id})[pricelist_id]

        return qty, price

    def _get_grouping_dicts(self, cr, uid, ids, context=None):
        """
        It will group the procurements according to the pos they should go into.  That way, lines going to the same
        po, can be processed at once.
        Returns two dictionaries:
        add_purchase_dicts: key: po value: procs to add to the po
        create_purchase_dicts: key: values for proc to create (not that necessary as they are in procurement => TODO),
                                values: procs to add
        """
        po_obj = self.pool.get('purchase.order')
        # Regroup POs
        cr.execute("""
            SELECT psi.name, p.id, pr.id, pr.picking_type_id, p.location_id, p.partner_dest_id, p.company_id, p.group_id,
            pr.group_propagation_option, pr.group_id, psi.qty
             FROM procurement_order AS p
                LEFT JOIN procurement_rule AS pr ON pr.id = p.rule_id
                LEFT JOIN procurement_group AS pg ON p.group_id = pg.id,
            product_supplierinfo AS psi, product_product AS pp
            WHERE
             p.product_id = pp.id AND p.id in %s AND psi.product_tmpl_id = pp.product_tmpl_id
             AND (psi.company_id = p.company_id or psi.company_id IS NULL)
             ORDER BY psi.sequence,
                psi.name, p.rule_id, p.location_id, p.company_id, p.partner_dest_id, p.group_id
        """, (tuple(ids), ))
        res = cr.fetchall()
        old = False
        # A giant dict for grouping lines, ... to do at once
        create_purchase_procs = {} # Lines to add to a newly to create po
        add_purchase_procs = {} # Lines to add/adjust in an existing po
        proc_seller = {} # To check we only process one po
        for partner, proc, rule, pick_type, location, partner_dest, company, group, group_propagation, fixed_group, qty in res:
            if not proc_seller.get(proc):
                proc_seller[proc] = partner
                new = partner, rule, pick_type, location, company, group, group_propagation, fixed_group
                if new != old:
                    old = new
                    dom = [
                        ('partner_id', '=', partner), ('state', '=', 'draft'), ('picking_type_id', '=', pick_type),
                        ('location_id', '=', location), ('company_id', '=', company), ('dest_address_id', '=', partner_dest)]
                    if group_propagation == 'propagate':
                        dom += [('group_id', '=', group)]
                    elif group_propagation == 'fixed':
                        dom += [('group_id', '=', fixed_group)]
                    available_draft_po_ids = po_obj.search(cr, uid, dom, context=context)
                    available_draft_po = available_draft_po_ids and available_draft_po_ids[0] or False
                # Add to dictionary
                if available_draft_po:
                    if add_purchase_procs.get(available_draft_po):
                        add_purchase_procs[available_draft_po] += [proc]
                    else:
                        add_purchase_procs[available_draft_po] = [proc]
                else:
                    if create_purchase_procs.get(new):
                        create_purchase_procs[new] += [proc]
                    else:
                        create_purchase_procs[new] = [proc]
        return add_purchase_procs, create_purchase_procs

    def make_po(self, cr, uid, ids, context=None):
        res = {}
        po_obj = self.pool.get('purchase.order')
        po_line_obj = self.pool.get('purchase.order.line')
        seq_obj = self.pool.get('ir.sequence')
        uom_obj = self.pool.get('product.uom')
        add_purchase_procs, create_purchase_procs = self._get_grouping_dicts(cr, uid, ids, context=context)
        procs_done = []

        # Let us check existing purchase orders and add/adjust lines on them
        for add_purchase in add_purchase_procs.keys():
            procs_done += add_purchase_procs[add_purchase]
            po = po_obj.browse(cr, uid, add_purchase, context=context)
            lines_to_update = {}
            line_values = []
            procurements = self.browse(cr, uid, add_purchase_procs[add_purchase], context=context)
            po_line_ids = po_line_obj.search(cr, uid, [('order_id', '=', add_purchase), ('product_id', 'in', [x.product_id.id for x in procurements])], context=context)
            po_lines = po_line_obj.browse(cr, uid, po_line_ids, context=context)
            po_prod_dict = {}
            for pol in po_lines:
                po_prod_dict[pol.product_id.id] = pol
            procs_to_create = []
            #Check which procurements need a new line and which need to be added to an existing one
            for proc in procurements:
                if po_prod_dict.get(proc.product_id.id):
                    po_line = po_prod_dict[proc.product_id.id]
                    # FIXME: compute quantity using `_calc_new_qty_price` method.
                    # new_qty, new_price = self._calc_new_qty_price(cr, uid, proc, po_line=po_line, context=context)
                    uom_id = po_line.product_uom  # Convert to UoM of existing line
                    qty = uom_obj._compute_qty_obj(cr, uid, proc.product_uom, proc.product_qty, uom_id)

                    if lines_to_update.get(po_line):
                        lines_to_update[po_line] += [(proc.id, qty)]
                    else:
                        lines_to_update[po_line] = [(proc.id, qty)]
                else:
                    procs_to_create.append(proc)

            procs = []
            # Update the quantities of the lines that need to
            for line in lines_to_update.keys():
                tot_qty = 0
                for proc, qty in lines_to_update[line]:
                    tot_qty += qty
                    self.message_post(cr, uid, proc, body=_("Quantity added in existing Purchase Order Line"), context=context)
                line_values += [(1, line.id, {'product_qty': line.product_qty + tot_qty, 'procurement_ids': [(4, x[0]) for x in lines_to_update[line]]})]

            # Create lines for which no line exists yet
            if procs_to_create:
                partner = po.partner_id
                schedule_date = datetime.strptime(po.minimum_planned_date, DEFAULT_SERVER_DATETIME_FORMAT)
                value_lines = self._get_po_line_values_from_procs(cr, uid, procs_to_create, partner, schedule_date, context=context)
                line_values += [(0, 0, value_lines[x]) for x in value_lines.keys()]
                for proc in procs_to_create:
                    self.message_post(cr, uid, [proc.id], body=_("Purchase line created and linked to an existing Purchase Order"), context=context)
            po_obj.write(cr, uid, [add_purchase], {'order_line': line_values},context=context)


        # Create new purchase orders
        partner_obj = self.pool.get("res.partner")
        new_pos = []
        for create_purchase in create_purchase_procs.keys():
            procs_done += create_purchase_procs[create_purchase]
            line_values = []
            procurements = self.browse(cr, uid, create_purchase_procs[create_purchase], context=context)
            partner = partner_obj.browse(cr, uid, create_purchase[0], context=context)

            #Create purchase order itself:
            procurement = procurements[0]
            schedule_date = self._get_purchase_schedule_date(cr, uid, procurement, procurement.company_id, context=context)
            purchase_date = self._get_purchase_order_date(cr, uid, procurement, procurement.company_id, schedule_date, context=context)

            value_lines = self._get_po_line_values_from_procs(cr, uid, procurements, partner, schedule_date, context=context)
            line_values += [(0, 0, value_lines[x]) for x in value_lines.keys()]
            name = seq_obj.next_by_code(cr, uid, 'purchase.order') or _('PO: %s') % procurement.name
            gpo = procurement.rule_id.group_propagation_option
            group = (gpo == 'fixed' and procurement.rule_id.group_id.id) or (gpo == 'propagate' and procurement.group_id.id) or False
            po_vals = {
                'name': name,
                'origin': procurement.origin,
                'partner_id': create_purchase[0],
                'location_id': procurement.location_id.id,
                'picking_type_id': procurement.rule_id.picking_type_id.id,
                'pricelist_id': partner.property_product_pricelist_purchase.id,
                'date_order': purchase_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                'company_id': procurement.company_id.id,
                'fiscal_position_id': partner.property_account_position.id,
                'payment_term_id': partner.property_supplier_payment_term.id,
                'dest_address_id': procurement.partner_dest_id.id,
                'group_id': group,
                'order_line': line_values,
                }
            new_po = po_obj.create(cr, uid, po_vals, context=context)
            new_pos.append(new_po)
            for proc in create_purchase_procs[create_purchase]:
                self.message_post(cr, uid, proc, body=_("Draft Purchase Order created"), context=context)

        other_proc_ids = list(set(ids) - set(procs_done))
        res = dict.fromkeys(ids, True)
        if other_proc_ids:
            other_procs = self.browse(cr, uid, other_proc_ids, context=context)
            for procurement in other_procs:
                res[procurement.id] = False
                self.message_post(cr, uid, [procurement.id], _('There is no supplier associated to product %s') % (procurement.product_id.name))
        return res


class mail_mail(osv.Model):
    _name = 'mail.mail'
    _inherit = 'mail.mail'

    def _postprocess_sent_message(self, cr, uid, mail, context=None, mail_sent=True):
        if mail_sent and mail.model == 'purchase.order':
            obj = self.pool.get('purchase.order').browse(cr, uid, mail.res_id, context=context)
            if obj.state == 'draft':
                self.pool.get('purchase.order').signal_workflow(cr, uid, [mail.res_id], 'send_rfq')
        return super(mail_mail, self)._postprocess_sent_message(cr, uid, mail=mail, context=context, mail_sent=mail_sent)


class product_template(osv.Model):
    _name = 'product.template'
    _inherit = 'product.template'
    
    def _get_buy_route(self, cr, uid, context=None):
        
        buy_route = self.pool.get('ir.model.data').xmlid_to_res_id(cr, uid, 'purchase.route_warehouse0_buy')
        if buy_route:
            return [buy_route]
        return []

    def _purchase_count(self, cr, uid, ids, field_name, arg, context=None):
        res = dict.fromkeys(ids, 0)
        for template in self.browse(cr, uid, ids, context=context):
            res[template.id] = sum([p.purchase_count for p in template.product_variant_ids])
        return res

    _columns = {
        'property_account_creditor_price_difference': fields.property(
            type='many2one',
            relation='account.account',
            string="Price Difference Account",
            help="This account will be used to value price difference between purchase price and cost price."),
        'purchase_ok': fields.boolean('Can be Purchased', help="Specify if the product can be selected in a purchase order line."),
        'purchase_count': fields.function(_purchase_count, string='# Purchases', type='integer'),
    }

    _defaults = {
        'purchase_ok': 1,
        'route_ids': _get_buy_route,
    }

    def action_view_purchases(self, cr, uid, ids, context=None):
        products = self._get_products(cr, uid, ids, context=context)
        result = self._get_act_window_dict(cr, uid, 'purchase.action_purchase_line_product_tree', context=context)
        result['domain'] = "[('product_id','in',[" + ','.join(map(str, products)) + "])]"
        return result

class product_product(osv.Model):
    _name = 'product.product'
    _inherit = 'product.product'
    
    def _purchase_count(self, cr, uid, ids, field_name, arg, context=None):
        Purchase = self.pool['purchase.order']
        return {
            product_id: Purchase.search_count(cr,uid, [('order_line.product_id', '=', product_id)], context=context) 
            for product_id in ids
        }

    def action_view_purchases(self, cr, uid, ids, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        result = self.pool['product.template']._get_act_window_dict(cr, uid, 'purchase.action_purchase_line_product_tree', context=context)
        result['domain'] = "[('product_id','in',[" + ','.join(map(str, ids)) + "])]"
        return result

    _columns = {
        'purchase_count': fields.function(_purchase_count, string='# Purchases', type='integer'),
    }

class product_category(osv.Model):
    _inherit = "product.category"
    _columns = {
        'property_account_creditor_price_difference_categ': fields.property(
            type='many2one',
            relation='account.account',
            string="Price Difference Account",
            help="This account will be used to value price difference between purchase price and cost price."),
    }


class mail_compose_message(osv.Model):
    _inherit = 'mail.compose.message'

    def send_mail(self, cr, uid, ids, auto_commit=False, context=None):
        context = context or {}
        if context.get('default_model') == 'purchase.order' and context.get('default_res_id'):
            context = dict(context, mail_post_autofollow=True)
            self.pool.get('purchase.order').signal_workflow(cr, uid, [context['default_res_id']], 'send_rfq')
        return super(mail_compose_message, self).send_mail(cr, uid, ids, context=context)


class account_invoice(osv.Model):
    """ Override account_invoice to add Chatter messages on the related purchase
        orders, logging the invoice receipt or payment. """
    _inherit = 'account.invoice'

    def invoice_validate(self, cr, uid, ids, context=None):
        res = super(account_invoice, self).invoice_validate(cr, uid, ids, context=context)
        purchase_order_obj = self.pool.get('purchase.order')
        # read access on purchase.order object is not required
        if not purchase_order_obj.check_access_rights(cr, uid, 'read', raise_exception=False):
            user_id = SUPERUSER_ID
        else:
            user_id = uid
        po_ids = purchase_order_obj.search(cr, user_id, [('invoice_ids', 'in', ids)], context=context)
        for order in purchase_order_obj.browse(cr, user_id, po_ids, context=context):
            purchase_order_obj.message_post(cr, user_id, order.id, body=_("Invoice received"), context=context)
            invoiced = []
            shipped = True
            # for invoice method manual or order, don't care about shipping state
            # for invoices based on incoming shippment, beware of partial deliveries
            if (order.invoice_method == 'picking' and
                    not all(picking.invoice_state in ['invoiced'] for picking in order.picking_ids)):
                shipped = False
            for po_line in order.order_line:
                if all(line.invoice_id.state not in ['draft', 'cancel'] for line in po_line.invoice_lines):
                    invoiced.append(po_line.id)
            if invoiced and shipped:
                self.pool['purchase.order.line'].write(cr, user_id, invoiced, {'invoiced': True})
            workflow.trg_write(user_id, 'purchase.order', order.id, cr)
        return res

    def confirm_paid(self, cr, uid, ids, context=None):
        res = super(account_invoice, self).confirm_paid(cr, uid, ids, context=context)
        purchase_order_obj = self.pool.get('purchase.order')
        # read access on purchase.order object is not required
        if not purchase_order_obj.check_access_rights(cr, uid, 'read', raise_exception=False):
            user_id = SUPERUSER_ID
        else:
            user_id = uid
        po_ids = purchase_order_obj.search(cr, user_id, [('invoice_ids', 'in', ids)], context=context)
        for po_id in po_ids:
            purchase_order_obj.message_post(cr, user_id, po_id, body=_("Invoice paid"), context=context)
        return res

class account_invoice_line(osv.Model):
    """ Override account_invoice_line to add the link to the purchase order line it is related to"""
    _inherit = 'account.invoice.line'
    _columns = {
        'purchase_line_id': fields.many2one('purchase.order.line',
            'Purchase Order Line', ondelete='set null', select=True,
            readonly=True),
    }

    def move_line_get(self, cr, uid, invoice_id, context=None):
        res = super(account_invoice_line,self).move_line_get(cr, uid, invoice_id, context=context)
        if self.company_id.anglo_saxon_accounting:
            if inv.type in ('in_invoice','in_refund'):
                for i_line in inv.invoice_line_ids:
                    res.extend(self._anglo_saxon_purchase_move_lines(cr, uid, i_line, res, context=context))
        return res

    def _anglo_saxon_purchase_move_lines(self, cr, uid, i_line, res, context=None):
        """Return the additional move lines for purchase invoices and refunds.

        i_line: An account.invoice.line object.
        res: The move line entries produced so far by the parent move_line_get.
        """
        inv = i_line.invoice_id
        company_currency = inv.company_id.currency_id.id
        if i_line.product_id and i_line.product_id.valuation == 'real_time':
            if i_line.product_id.type != 'service':
                # get the price difference account at the product
                acc = i_line.product_id.property_account_creditor_price_difference and i_line.product_id.property_account_creditor_price_difference.id
                if not acc:
                    # if not found on the product get the price difference account at the category
                    acc = i_line.product_id.categ_id.property_account_creditor_price_difference_categ and i_line.product_id.categ_id.property_account_creditor_price_difference_categ.id
                a = None

                # oa will be the stock input account
                # first check the product, if empty check the category
                oa = i_line.product_id.property_stock_account_input and i_line.product_id.property_stock_account_input.id
                if not oa:
                    oa = i_line.product_id.categ_id.property_stock_account_input_categ and i_line.product_id.categ_id.property_stock_account_input_categ.id
                if oa:
                    # get the fiscal position
                    fpos = i_line.invoice_id.fiscal_position_id or False
                    a = self.pool.get('account.fiscal.position').map_account(cr, uid, fpos, oa)
                diff_res = []
                account_prec = inv.company_id.currency_id.decimal_places
                # calculate and write down the possible price difference between invoice price and product price
                for line in res:
                    if line.get('invl_id', 0) == i_line.id and a == line['account_id']:
                        uom = i_line.product_id.uos_id or i_line.product_id.uom_id
                        valuation_price_unit = self.pool.get('product.uom')._compute_price(cr, uid, uom.id, i_line.product_id.standard_price, i_line.uos_id.id)
                        if i_line.product_id.cost_method != 'standard' and i_line.purchase_line_id:
                            #for average/fifo/lifo costing method, fetch real cost price from incomming moves
                            stock_move_obj = self.pool.get('stock.move')
                            valuation_stock_move = stock_move_obj.search(cr, uid, [('purchase_line_id', '=', i_line.purchase_line_id.id)], limit=1, context=context)
                            if valuation_stock_move:
                                valuation_price_unit = stock_move_obj.browse(cr, uid, valuation_stock_move[0], context=context).price_unit
                        if inv.currency_id.id != company_currency:
                            valuation_price_unit = self.pool.get('res.currency').compute(cr, uid, company_currency, inv.currency_id.id, valuation_price_unit, context={'date': inv.date_invoice})
                        if valuation_price_unit != i_line.price_unit and line['price_unit'] == i_line.price_unit and acc:
                            # price with discount and without tax included
                            price_unit = self.pool['account.tax'].compute_all(cr, uid, line['taxes'], i_line.price_unit * (1-(i_line.discount or 0.0)/100.0),
                                inv.currency_id.id, line['quantity'])['total_excluded']
                            price_line = round(valuation_price_unit * line['quantity'], account_prec)
                            price_diff = round(price_unit - price_line, account_prec)
                            line.update({'price': price_line})
                            diff_res.append({
                                'type': 'src',
                                'name': i_line.name[:64],
                                'price_unit': round(price_diff / line['quantity'], account_prec),
                                'quantity': line['quantity'],
                                'price': price_diff,
                                'account_id': acc,
                                'product_id': line['product_id'],
                                'uos_id': line['uos_id'],
                                'account_analytic_id': line['account_analytic_id'],
                                'taxes': line.get('taxes', []),
                                })
                return diff_res
        return []


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
