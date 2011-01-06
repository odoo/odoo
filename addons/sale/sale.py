# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time
import netsvc
from osv import fields, osv
from mx import DateTime
from tools import config
from tools.translate import _


class sale_shop(osv.osv):
    _name = "sale.shop"
    _description = "Sale Shop"
    _columns = {
        'name': fields.char('Shop Name', size=64, required=True),
        'payment_default_id': fields.many2one('account.payment.term', 'Default Payment Term', required=True),
        'payment_account_id': fields.many2many('account.account', 'sale_shop_account', 'shop_id', 'account_id', 'Payment Accounts'),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse'),
        'pricelist_id': fields.many2one('product.pricelist', 'Pricelist'),
        'project_id': fields.many2one('account.analytic.account', 'Analytic Account'),
    }
sale_shop()


def _incoterm_get(self, cr, uid, context={}):
    cr.execute('select code, code||\', \'||name from stock_incoterms where active')
    return cr.fetchall()


class sale_order(osv.osv):
    _name = "sale.order"
    _description = "Sale Order"

    def copy(self, cr, uid, id, default=None, context={}):
        if not default:
            default = {}
        default.update({
            'state': 'draft',
            'shipped': False,
            'invoice_ids': [],
            'picking_ids': [],
            'name': self.pool.get('ir.sequence').get(cr, uid, 'sale.order'),
        })
        return super(sale_order, self).copy(cr, uid, id, default, context)

    def _amount_line_tax(self, cr, uid, line, context={}):
        val = 0.0
        for c in self.pool.get('account.tax').compute(cr, uid, line.tax_id, line.price_unit * (1-(line.discount or 0.0)/100.0), line.product_uom_qty, line.order_id.partner_invoice_id.id, line.product_id, line.order_id.partner_id):
            val += c['amount']
        return val

    def _amount_all(self, cr, uid, ids, field_name, arg, context):
        res = {}
        cur_obj = self.pool.get('res.currency')
        for order in self.browse(cr, uid, ids):
            res[order.id] = {
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
                'amount_total': 0.0,
            }
            val = val1 = 0.0
            cur = order.pricelist_id.currency_id
            for line in order.order_line:
                val1 += line.price_subtotal
                val += self._amount_line_tax(cr, uid, line, context)
            res[order.id]['amount_tax'] = cur_obj.round(cr, uid, cur, val)
            res[order.id]['amount_untaxed'] = cur_obj.round(cr, uid, cur, val1)
            res[order.id]['amount_total'] = res[order.id]['amount_untaxed'] + res[order.id]['amount_tax']
        return res

    def _picked_rate(self, cr, uid, ids, name, arg, context=None):
        if not ids:
            return {}
        res = {}
        for id in ids:
            res[id] = [0.0, 0.0]
        cr.execute('''SELECT
                p.sale_id,sum(m.product_qty), mp.state as mp_state, m.state as state, p.type as tp
            FROM
                stock_move m
            LEFT JOIN
                stock_picking p on (p.id=m.picking_id)
            LEFT JOIN
                mrp_procurement mp on (mp.move_id=m.id)
            WHERE
                p.sale_id in %s
            GROUP BY m.state, mp.state, p.sale_id, p.type''', (tuple(ids),))

        for oid, nbr, state, move_state, type_pick in cr.fetchall():
            if state == 'cancel':
                continue
            res[oid][1] += nbr or 0.0
            if state == 'done' or move_state == 'done':
                res[oid][0] += nbr or 0.0
            
            if type_pick == 'in':#which  clearly means that this is a returned picking
                res[oid][1] -= 2*nbr or 0.0 # Deducting the return picking qty
                if state == 'done' or move_state == 'done':
                    nbr += nbr
                res[oid][0] -= nbr or 0.0
                
        for r in res:
            if not res[r][1]:
                res[r] = 0.0
            else:
                res[r] = 100.0 * res[r][0] / res[r][1]
        for order in self.browse(cr, uid, ids, context):
            if order.shipped:
                res[order.id] = 100.0
        return res

    def _invoiced_rate(self, cursor, user, ids, name, arg, context=None):
        res = {}
        for sale in self.browse(cursor, user, ids, context=context):
            if sale.invoiced:
                res[sale.id] = 100.0
                continue
            tot = 0.0
            for invoice in sale.invoice_ids:
                if invoice.state not in ('draft', 'cancel'):
                    tot += invoice.amount_untaxed

            if tot:
                res[sale.id] = min(100.0, tot * 100.0 / (sale.amount_untaxed or 1.00))
            else:
                res[sale.id] = 0.0
        return res

    def _invoiced(self, cursor, user, ids, name, arg, context=None):
        res = {}
        for sale in self.browse(cursor, user, ids, context=context):
            res[sale.id] = True
            for invoice in sale.invoice_ids:
                if invoice.state != 'paid':
                    res[sale.id] = False
                    break
            if not sale.invoice_ids:
                res[sale.id] = False
        return res

    def _invoiced_search(self, cursor, user, obj, name, args, context):
        if not len(args):
            return []
        clause = ''
        no_invoiced = False
        for arg in args:
            if arg[1] == '=':
                if arg[2]:
                    clause += 'AND inv.state = \'paid\''
                else:
                    clause += 'AND inv.state <> \'paid\''
                    no_invoiced = True
        cursor.execute('SELECT rel.order_id ' \
                'FROM sale_order_invoice_rel AS rel, account_invoice AS inv ' \
                'WHERE rel.invoice_id = inv.id ' + clause)
        res = cursor.fetchall()
        if no_invoiced:
            cursor.execute('SELECT sale.id ' \
                    'FROM sale_order AS sale ' \
                    'WHERE sale.id NOT IN ' \
                        '(SELECT rel.order_id ' \
                        'FROM sale_order_invoice_rel AS rel)')
            res.extend(cursor.fetchall())
        if not res:
            return [('id', '=', 0)]
        return [('id', 'in', [x[0] for x in res])]

    def _get_order(self, cr, uid, ids, context={}):
        result = {}
        for line in self.pool.get('sale.order.line').browse(cr, uid, ids, context=context):
            result[line.order_id.id] = True
        return result.keys()

    _columns = {
        'name': fields.char('Order Reference', size=64, required=True, select=True),
        'shop_id': fields.many2one('sale.shop', 'Shop', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'origin': fields.char('Origin', size=64),
        'client_order_ref': fields.char('Customer Ref', size=64),

        'state': fields.selection([
            ('draft', 'Quotation'),
            ('waiting_date', 'Waiting Schedule'),
            ('manual', 'Manual In Progress'),
            ('progress', 'In Progress'),
            ('shipping_except', 'Shipping Exception'),
            ('invoice_except', 'Invoice Exception'),
            ('done', 'Done'),
            ('cancel', 'Cancelled')
            ], 'Order State', readonly=True, help="Gives the state of the quotation or sale order. The exception state is automatically set when a cancel operation occurs in the invoice validation (Invoice Exception) or in the packing list process (Shipping Exception). The 'Waiting Schedule' state is set when the invoice is confirmed but waiting for the scheduler to run on the date 'Date Ordered'.", select=True),
        'date_order': fields.date('Date Ordered', required=True, readonly=True, states={'draft': [('readonly', False)]}),

        'user_id': fields.many2one('res.users', 'Salesman', states={'draft': [('readonly', False)]}, select=True),
        'partner_id': fields.many2one('res.partner', 'Customer', readonly=True, states={'draft': [('readonly', False)]}, required=True, change_default=True, select=True),
        'partner_invoice_id': fields.many2one('res.partner.address', 'Invoice Address', readonly=True, required=True, states={'draft': [('readonly', False)]}),
        'partner_order_id': fields.many2one('res.partner.address', 'Ordering Contact', readonly=True, required=True, states={'draft': [('readonly', False)]}, help="The name and address of the contact that requested the order or quotation."),
        'partner_shipping_id': fields.many2one('res.partner.address', 'Shipping Address', readonly=True, required=True, states={'draft': [('readonly', False)]}),

        'incoterm': fields.selection(_incoterm_get, 'Incoterm', size=3),
        'picking_policy': fields.selection([('direct', 'Partial Delivery'), ('one', 'Complete Delivery')],
            'Packing Policy', required=True, help="""If you don't have enough stock available to deliver all at once, do you accept partial shipments or not?"""),
        'order_policy': fields.selection([
            ('prepaid', 'Payment Before Delivery'),
            ('manual', 'Shipping & Manual Invoice'),
            ('postpaid', 'Invoice on Order After Delivery'),
            ('picking', 'Invoice from the Packing'),
        ], 'Shipping Policy', required=True, readonly=True, states={'draft': [('readonly', False)]},
                    help="""The Shipping Policy is used to synchronise invoice and delivery operations.
  - The 'Pay before delivery' choice will first generate the invoice and then generate the packing order after the payment of this invoice.
  - The 'Shipping & Manual Invoice' will create the packing order directly and wait for the user to manually click on the 'Invoice' button to generate the draft invoice.
  - The 'Invoice on Order After Delivery' choice will generate the draft invoice based on sale order after all packing lists have been finished.
  - The 'Invoice from the packing' choice is used to create an invoice during the packing process."""),
        'pricelist_id': fields.many2one('product.pricelist', 'Pricelist', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'project_id': fields.many2one('account.analytic.account', 'Analytic Account', readonly=True, states={'draft': [('readonly', False)]}),

        'order_line': fields.one2many('sale.order.line', 'order_id', 'Order Lines', readonly=True, states={'draft': [('readonly', False)]}),
        'invoice_ids': fields.many2many('account.invoice', 'sale_order_invoice_rel', 'order_id', 'invoice_id', 'Invoices', help="This is the list of invoices that have been generated for this sale order. The same sale order may have been invoiced in several times (by line for example)."),
        'picking_ids': fields.one2many('stock.picking', 'sale_id', 'Related Packing', readonly=True, help="This is the list of picking list that have been generated for this invoice"),
        'shipped': fields.boolean('Picked', readonly=True),
        'picked_rate': fields.function(_picked_rate, method=True, string='Picked', type='float'),
        'invoiced_rate': fields.function(_invoiced_rate, method=True, string='Invoiced', type='float'),
        'invoiced': fields.function(_invoiced, method=True, string='Paid',
            fnct_search=_invoiced_search, type='boolean'),
        'note': fields.text('Notes'),

        'amount_untaxed': fields.function(_amount_all, method=True, digits=(16, int(config['price_accuracy'])), string='Untaxed Amount',
            store = {
                'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 10),
                'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty'], 10),
            },
            multi='sums'),
        'amount_tax': fields.function(_amount_all, method=True, digits=(16, int(config['price_accuracy'])), string='Taxes',
            store = {
                'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 10),
                'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty'], 10),
            },
            multi='sums'),
        'amount_total': fields.function(_amount_all, method=True, digits=(16, int(config['price_accuracy'])), string='Total',
            store = {
                'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 10),
                'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty'], 10),
            },
            multi='sums'),

        'invoice_quantity': fields.selection([('order', 'Ordered Quantities'), ('procurement', 'Shipped Quantities')], 'Invoice on', help="The sale order will automatically create the invoice proposition (draft invoice). Ordered and delivered quantities may not be the same. You have to choose if you invoice based on ordered or shipped quantities. If the product is a service, shipped quantities means hours spent on the associated tasks.", required=True),
        'payment_term': fields.many2one('account.payment.term', 'Payment Term'),
        'fiscal_position': fields.many2one('account.fiscal.position', 'Fiscal Position')
    }
    _defaults = {
        'picking_policy': lambda *a: 'direct',
        'date_order': lambda *a: time.strftime('%Y-%m-%d'),
        'order_policy': lambda *a: 'manual',
        'state': lambda *a: 'draft',
        'user_id': lambda obj, cr, uid, context: uid,
        'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'sale.order'),
        'invoice_quantity': lambda *a: 'order',
        'partner_invoice_id': lambda self, cr, uid, context: context.get('partner_id', False) and self.pool.get('res.partner').address_get(cr, uid, [context['partner_id']], ['invoice'])['invoice'],
        'partner_order_id': lambda self, cr, uid, context: context.get('partner_id', False) and  self.pool.get('res.partner').address_get(cr, uid, [context['partner_id']], ['contact'])['contact'],
        'partner_shipping_id': lambda self, cr, uid, context: context.get('partner_id', False) and self.pool.get('res.partner').address_get(cr, uid, [context['partner_id']], ['delivery'])['delivery'],
#        'pricelist_id': lambda self, cr, uid, context: context.get('partner_id', False) and self.pool.get('res.partner').browse(cr, uid, context['partner_id']).property_product_pricelist.id,
    }
    _order = 'name desc'

    # Form filling
    def unlink(self, cr, uid, ids, context=None):
        sale_orders = self.read(cr, uid, ids, ['state'])
        unlink_ids = []
        for s in sale_orders:
            if s['state'] in ['draft', 'cancel']:
                unlink_ids.append(s['id'])
            else:
                raise osv.except_osv(_('Invalid action !'), _('Cannot delete Sale Order(s) which are already confirmed !'))
        return osv.osv.unlink(self, cr, uid, unlink_ids, context=context)

    def onchange_shop_id(self, cr, uid, ids, shop_id):
        v = {}
        if shop_id:
            shop = self.pool.get('sale.shop').browse(cr, uid, shop_id)
            v['project_id'] = shop.project_id.id
            # Que faire si le client a une pricelist a lui ?
            if shop.pricelist_id.id:
                v['pricelist_id'] = shop.pricelist_id.id
            #v['payment_default_id']=shop.payment_default_id.id
        return {'value': v}

    def action_cancel_draft(self, cr, uid, ids, *args):
        if not len(ids):
            return False
        cr.execute('select id from sale_order_line where order_id in %s', (tuple(ids),))
        line_ids = map(lambda x: x[0], cr.fetchall())
        self.write(cr, uid, ids, {'state': 'draft', 'invoice_ids': [], 'shipped': 0})
        self.pool.get('sale.order.line').write(cr, uid, line_ids, {'invoiced': False, 'state': 'draft', 'invoice_lines': [(6, 0, [])]})
        wf_service = netsvc.LocalService("workflow")
        for inv_id in ids:
            # Deleting the existing instance of workflow for SO
            wf_service.trg_delete(uid, 'sale.order', inv_id, cr)
            wf_service.trg_create(uid, 'sale.order', inv_id, cr)
        return True

    def onchange_partner_id(self, cr, uid, ids, part):
        if not part:
            return {'value': {'partner_invoice_id': False, 'partner_shipping_id': False, 'partner_order_id': False, 'payment_term': False, 'fiscal_position': False}}

        addr = self.pool.get('res.partner').address_get(cr, uid, [part], ['delivery', 'invoice', 'contact'])
        part = self.pool.get('res.partner').browse(cr, uid, part)
        pricelist = part.property_product_pricelist and part.property_product_pricelist.id or False
        payment_term = part.property_payment_term and part.property_payment_term.id or False
        fiscal_position = part.property_account_position and part.property_account_position.id or False
        dedicated_salesman = part.user_id and part.user_id.id or uid

        val = {
            'partner_invoice_id': addr['invoice'],
            'partner_order_id': addr['contact'],
            'partner_shipping_id': addr['delivery'],
            'payment_term': payment_term,
            'fiscal_position': fiscal_position,
            'user_id': dedicated_salesman,
        }

        if pricelist:
            val['pricelist_id'] = pricelist

        return {'value': val}

    def shipping_policy_change(self, cr, uid, ids, policy, context={}):
        if not policy:
            return {}
        inv_qty = 'order'
        if policy == 'prepaid':
            inv_qty = 'order'
        elif policy == 'picking':
            inv_qty = 'procurement'
        return {'value': {'invoice_quantity': inv_qty}}

    def write(self, cr, uid, ids, vals, context=None):
        if 'order_policy' in vals:
            if vals['order_policy'] == 'prepaid':
                vals.update({'invoice_quantity': 'order'})
            elif vals['order_policy'] == 'picking':
                vals.update({'invoice_quantity': 'procurement'})
        return super(sale_order, self).write(cr, uid, ids, vals, context=context)

    def create(self, cr, uid, vals, context={}):
        if 'order_policy' in vals:
            if vals['order_policy'] == 'prepaid':
                vals.update({'invoice_quantity': 'order'})
            if vals['order_policy'] == 'picking':
                vals.update({'invoice_quantity': 'procurement'})
        return super(sale_order, self).create(cr, uid, vals, context=context)

    def button_dummy(self, cr, uid, ids, context={}):
        return True

#FIXME: the method should return the list of invoices created (invoice_ids)
# and not the id of the last invoice created (res). The problem is that we
# cannot change it directly since the method is called by the sale order
# workflow and I suppose it expects a single id...
    def _inv_get(self, cr, uid, order, context={}):
        return {}

    def _make_invoice(self, cr, uid, order, lines, context={}):
        a = order.partner_id.property_account_receivable.id
        if order.payment_term:
            pay_term = order.payment_term.id
        else:
            pay_term = False
        for preinv in order.invoice_ids:
            if preinv.state not in ('cancel',):
                for preline in preinv.invoice_line:
                    inv_line_id = self.pool.get('account.invoice.line').copy(cr, uid, preline.id, {'invoice_id': False, 'price_unit': -preline.price_unit})
                    lines.append(inv_line_id)
        inv = {
            'name': order.client_order_ref or order.name,
            'origin': order.name,
            'type': 'out_invoice',
            'reference': "P%dSO%d" % (order.partner_id.id, order.id),
            'account_id': a,
            'partner_id': order.partner_id.id,
            'address_invoice_id': order.partner_invoice_id.id,
            'address_contact_id': order.partner_order_id.id,
            'invoice_line': [(6, 0, lines)],
            'currency_id': order.pricelist_id.currency_id.id,
            'comment': order.note,
            'payment_term': pay_term,
            'fiscal_position': order.fiscal_position.id or order.partner_id.property_account_position.id
        }
        inv_obj = self.pool.get('account.invoice')
        inv.update(self._inv_get(cr, uid, order))
        inv_id = inv_obj.create(cr, uid, inv)
        data = inv_obj.onchange_payment_term_date_invoice(cr, uid, [inv_id], pay_term, time.strftime('%Y-%m-%d'))
        if data.get('value', False):
            inv_obj.write(cr, uid, [inv_id], data['value'], context=context)
        inv_obj.button_compute(cr, uid, [inv_id])
        return inv_id

    def action_invoice_create(self, cr, uid, ids, grouped=False, states=['confirmed', 'done', 'exception']):
        res = False
        invoices = {}
        invoice_ids = []

        for o in self.browse(cr, uid, ids):
            lines = []
            for line in o.order_line:
                if (line.state in states) and not line.invoiced:
                    lines.append(line.id)
            created_lines = self.pool.get('sale.order.line').invoice_line_create(cr, uid, lines)
            if created_lines:
                invoices.setdefault(o.partner_id.id, []).append((o, created_lines))

        if not invoices:
            for o in self.browse(cr, uid, ids):
                for i in o.invoice_ids:
                    if i.state == 'draft':
                        return i.id
        picking_obj = self.pool.get('stock.picking')
        for val in invoices.values():
            if grouped:
                res = self._make_invoice(cr, uid, val[0][0], reduce(lambda x, y: x + y, [l for o, l in val], []))
                for o, l in val:
                    self.write(cr, uid, [o.id], {'state': 'progress'})
                    if o.order_policy == 'picking':
                        picking_obj.write(cr, uid, map(lambda x: x.id, o.picking_ids), {'invoice_state': 'invoiced'})
                    cr.execute('insert into sale_order_invoice_rel (order_id,invoice_id) values (%s,%s)', (o.id, res))
            else:
                for order, il in val:
                    res = self._make_invoice(cr, uid, order, il)
                    invoice_ids.append(res)
                    self.write(cr, uid, [order.id], {'state': 'progress'})
                    if order.order_policy == 'picking':
                        picking_obj.write(cr, uid, map(lambda x: x.id, order.picking_ids), {'invoice_state': 'invoiced'})
                    cr.execute('insert into sale_order_invoice_rel (order_id,invoice_id) values (%s,%s)', (order.id, res))
        return res

    def action_invoice_cancel(self, cr, uid, ids, context=None):
        for sale in self.browse(cr, uid, ids):
            for line in sale.order_line:
                #
                # Check if the line is invoiced (has asociated invoice
                # lines from non-cancelled invoices).
                #
                invoiced = False
                for iline in line.invoice_lines:
                    if iline.invoice_id and iline.invoice_id.state != 'cancel':
                        invoiced = True
                        break
                # Update the line (only when needed)
                if line.invoiced != invoiced:
                    self.pool.get('sale.order.line').write(cr, uid, [line.id], {'invoiced': invoiced}, context=context)
        self.write(cr, uid, ids, {'state': 'invoice_except', 'invoice_ids': False}, context=context)
        return True
    
    def action_invoice_end(self, cr, uid, ids, context=None):
        for order in self.browse(cr, uid, ids, context=context):
            #
            # Update the sale order lines state (and invoiced flag).
            #
            for line in order.order_line:
                vals = {}
                #
                # Check if the line is invoiced (has asociated invoice
                # lines from non-cancelled invoices).
                #
                invoiced = False
                for iline in line.invoice_lines:
                    if iline.invoice_id and iline.invoice_id.state != 'cancel':
                        invoiced = True
                        break
                if line.invoiced != invoiced:
                    vals['invoiced'] = invoiced
                # If the line was in exception state, now it gets confirmed.
                if line.state == 'exception':
                    vals['state'] = 'confirmed'
                # Update the line (only when needed).
                if vals:
                    self.pool.get('sale.order.line').write(cr, uid, [line.id], vals, context=context)
            #
            # Update the sale order state.
            #
            if order.state == 'invoice_except':
                self.write(cr, uid, [order.id], {'state' : 'progress'}, context=context)
            
        return True
    
    def action_cancel(self, cr, uid, ids, context={}):
        ok = True
        sale_order_line_obj = self.pool.get('sale.order.line')
        for sale in self.browse(cr, uid, ids):
            for pick in sale.picking_ids:
                if pick.state not in ('draft', 'cancel'):
                    raise osv.except_osv(
                        _('Could not cancel sale order !'),
                        _('You must first cancel all packing attached to this sale order.'))
            for r in self.read(cr, uid, ids, ['picking_ids']):
                for pick in r['picking_ids']:
                    wf_service = netsvc.LocalService("workflow")
                    wf_service.trg_validate(uid, 'stock.picking', pick, 'button_cancel', cr)
            for inv in sale.invoice_ids:
                if inv.state not in ('draft', 'cancel'):
                    raise osv.except_osv(
                        _('Could not cancel this sale order !'),
                        _('You must first cancel all invoices attached to this sale order.'))
            for r in self.read(cr, uid, ids, ['invoice_ids']):
                for inv in r['invoice_ids']:
                    wf_service = netsvc.LocalService("workflow")
                    wf_service.trg_validate(uid, 'account.invoice', inv, 'invoice_cancel', cr)
            sale_order_line_obj.write(cr, uid, [l.id for l in  sale.order_line],
                    {'state': 'cancel'})
        self.write(cr, uid, ids, {'state': 'cancel'})
        return True

    def action_wait(self, cr, uid, ids, *args):
        event_p = self.pool.get('res.partner.event.type').check(cr, uid, 'sale_open')
        event_obj = self.pool.get('res.partner.event')
        for o in self.browse(cr, uid, ids):
            if event_p:
                event_obj.create(cr, uid, {'name': 'Sale Order: '+ o.name,\
                        'partner_id': o.partner_id.id,\
                        'date': time.strftime('%Y-%m-%d %H:%M:%S'),\
                        'user_id': (o.user_id and o.user_id.id) or uid,\
                        'partner_type': 'customer', 'probability': 1.0,\
                        'planned_revenue': o.amount_untaxed})
            if (o.order_policy == 'manual'):
                self.write(cr, uid, [o.id], {'state': 'manual'})
            else:
                self.write(cr, uid, [o.id], {'state': 'progress'})
            self.pool.get('sale.order.line').button_confirm(cr, uid, [x.id for x in o.order_line])

    def procurement_lines_get(self, cr, uid, ids, *args):
        res = []
        for order in self.browse(cr, uid, ids, context={}):
            for line in order.order_line:
                if line.procurement_id:
                    res.append(line.procurement_id.id)
        return res
        
    # if mode == 'finished':
    #   returns True if all lines are done, False otherwise
    # if mode == 'canceled':
    #   returns True if there is at least one canceled line, False otherwise
    def test_state(self, cr, uid, ids, mode, *args):
        assert mode in ('finished', 'canceled'), _("invalid mode for test_state")
        finished = True
        canceled = False
        notcanceled = False
        write_done_ids = []
        write_cancel_ids = []
        for order in self.browse(cr, uid, ids, context={}):
            for line in order.order_line:
                if (not line.procurement_id) or (line.procurement_id.state=='done'):
                    if line.state != 'done':
                        write_done_ids.append(line.id)
                else:
                    finished = False
                if line.procurement_id:
                    if (line.procurement_id.state == 'cancel'):
                        canceled = True
                        if line.state != 'exception':
                            write_cancel_ids.append(line.id)
                    else:
                        notcanceled = True
        if write_done_ids:
            self.pool.get('sale.order.line').write(cr, uid, write_done_ids, {'state': 'done'})
        if write_cancel_ids:
            self.pool.get('sale.order.line').write(cr, uid, write_cancel_ids, {'state': 'exception'})

        if mode == 'finished':
            return finished
        elif mode == 'canceled':
            return canceled
            if notcanceled:
                return False
            return canceled

    def action_ship_create(self, cr, uid, ids, *args):
        picking_id = False
        company = self.pool.get('res.users').browse(cr, uid, uid).company_id
        for order in self.browse(cr, uid, ids, context={}):
            output_id = order.shop_id.warehouse_id.lot_output_id.id
            picking_id = False
            for line in order.order_line:
                proc_id = False
                date_planned = DateTime.now() + DateTime.DateTimeDeltaFromDays(line.delay or 0.0)
                date_planned = (date_planned - DateTime.DateTimeDeltaFromDays(company.security_lead)).strftime('%Y-%m-%d %H:%M:%S')
                if line.state == 'done':
                    continue
                if line.product_id and line.product_id.product_tmpl_id.type in ('product', 'consu'):
                    location_id = order.shop_id.warehouse_id.lot_stock_id.id
                    if not picking_id:
                        loc_dest_id = order.partner_id.property_stock_customer.id
                        picking_id = self.pool.get('stock.picking').create(cr, uid, {
                            'origin': order.name,
                            'type': 'out',
                            'state': 'auto',
                            'move_type': order.picking_policy,
                            'sale_id': order.id,
                            'address_id': order.partner_shipping_id.id,
                            'note': order.note,
                            'invoice_state': (order.order_policy=='picking' and '2binvoiced') or 'none',

                        })

                    move_id = self.pool.get('stock.move').create(cr, uid, {
                        'name': line.name[:64],
                        'picking_id': picking_id,
                        'product_id': line.product_id.id,
                        'date_planned': date_planned,
                        'product_qty': line.product_uom_qty,
                        'product_uom': line.product_uom.id,
                        'product_uos_qty': line.product_uos_qty,
                        'product_uos': (line.product_uos and line.product_uos.id)\
                                or line.product_uom.id,
                        'product_packaging': line.product_packaging.id,
                        'address_id': line.address_allotment_id.id or order.partner_shipping_id.id,
                        'location_id': location_id,
                        'location_dest_id': output_id,
                        'sale_line_id': line.id,
                        'tracking_id': False,
                        'state': 'draft',
                        #'state': 'waiting',
                        'note': line.notes,
                    })
                    proc_id = self.pool.get('mrp.procurement').create(cr, uid, {
                        'name': order.name,
                        'origin': order.name,
                        'date_planned': date_planned,
                        'product_id': line.product_id.id,
                        'product_qty': line.product_uom_qty,
                        'product_uom': line.product_uom.id,
                        'product_uos_qty': (line.product_uos and line.product_uos_qty)\
                                or line.product_uom_qty,
                        'product_uos': (line.product_uos and line.product_uos.id)\
                                or line.product_uom.id,
                        'location_id': order.shop_id.warehouse_id.lot_stock_id.id,
                        'procure_method': line.type,
                        'move_id': move_id,
                        'property_ids': [(6, 0, [x.id for x in line.property_ids])],
                    })
                    wf_service = netsvc.LocalService("workflow")
                    wf_service.trg_validate(uid, 'mrp.procurement', proc_id, 'button_confirm', cr)
                    self.pool.get('sale.order.line').write(cr, uid, [line.id], {'procurement_id': proc_id})
                elif line.product_id and line.product_id.product_tmpl_id.type == 'service':
                    proc_id = self.pool.get('mrp.procurement').create(cr, uid, {
                        'name': line.name,
                        'origin': order.name,
                        'date_planned': date_planned,
                        'product_id': line.product_id.id,
                        'product_qty': line.product_uom_qty,
                        'product_uom': line.product_uom.id,
                        'location_id': order.shop_id.warehouse_id.lot_stock_id.id,
                        'procure_method': line.type,
                        'property_ids': [(6, 0, [x.id for x in line.property_ids])],
                    })
                    self.pool.get('sale.order.line').write(cr, uid, [line.id], {'procurement_id': proc_id})
                    wf_service = netsvc.LocalService("workflow")
                    wf_service.trg_validate(uid, 'mrp.procurement', proc_id, 'button_confirm', cr)
                else:
                    #
                    # No procurement because no product in the sale.order.line.
                    #
                    pass

            val = {}
            if picking_id:
                wf_service = netsvc.LocalService("workflow")
                wf_service.trg_validate(uid, 'stock.picking', picking_id, 'button_confirm', cr)

            if order.state == 'shipping_except':
                val['state'] = 'progress'

                if (order.order_policy == 'manual'):
                    for line in order.order_line:
                        if (not line.invoiced) and (line.state not in ('cancel', 'draft')):
                            val['state'] = 'manual'
                            break
            self.write(cr, uid, [order.id], val)

        return True

    def action_ship_end(self, cr, uid, ids, context={}):
        for order in self.browse(cr, uid, ids):
            val = {'shipped': True}
            if order.state == 'shipping_except':
                val['state'] = 'progress'
                if (order.order_policy == 'manual'):
                    for line in order.order_line:
                        if (not line.invoiced) and (line.state not in ('cancel', 'draft')):
                            val['state'] = 'manual'
                            break
            for line in order.order_line:
                towrite = []
                if line.state == 'exception':
                    towrite.append(line.id)
                if towrite:
                    self.pool.get('sale.order.line').write(cr, uid, towrite, {'state': 'done'}, context=context)
            self.write(cr, uid, [order.id], val)
        return True

    def _log_event(self, cr, uid, ids, factor=0.7, name='Open Order'):
        invs = self.read(cr, uid, ids, ['date_order', 'partner_id', 'amount_untaxed'])
        for inv in invs:
            part = inv['partner_id'] and inv['partner_id'][0]
            pr = inv['amount_untaxed'] or 0.0
            partnertype = 'customer'
            eventtype = 'sale'
            event = {
                'name': 'Order: '+name,
                'som': False,
                'description': 'Order '+str(inv['id']),
                'document': '',
                'partner_id': part,
                'date': time.strftime('%Y-%m-%d'),
                'canal_id': False,
                'user_id': uid,
                'partner_type': partnertype,
                'probability': 1.0,
                'planned_revenue': pr,
                'planned_cost': 0.0,
                'type': eventtype
            }
            self.pool.get('res.partner.event').create(cr, uid, event)

    def has_stockable_products(self, cr, uid, ids, *args):
        for order in self.browse(cr, uid, ids):
            for order_line in order.order_line:
                if order_line.product_id and order_line.product_id.product_tmpl_id.type in ('product', 'consu'):
                    return True
        return False
sale_order()

# TODO add a field price_unit_uos
# - update it on change product and unit price
# - use it in report if there is a uos
class sale_order_line(osv.osv):
    def _amount_line_net(self, cr, uid, ids, field_name, arg, context):
        res = {}
        for line in self.browse(cr, uid, ids):
            res[line.id] = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
        return res

    def _amount_line(self, cr, uid, ids, field_name, arg, context):
        res = {}
        cur_obj = self.pool.get('res.currency')
        for line in self.browse(cr, uid, ids):
            res[line.id] = line.price_unit * line.product_uom_qty * (1 - (line.discount or 0.0) / 100.0)
            cur = line.order_id.pricelist_id.currency_id
            res[line.id] = cur_obj.round(cr, uid, cur, res[line.id])
        return res

    def _number_packages(self, cr, uid, ids, field_name, arg, context):
        res = {}
        for line in self.browse(cr, uid, ids):
            try:
                res[line.id] = int(line.product_uom_qty / line.product_packaging.qty)
            except:
                res[line.id] = 1
        return res

    _name = 'sale.order.line'
    _description = 'Sale Order line'
    _columns = {
        'order_id': fields.many2one('sale.order', 'Order Ref', required=True, ondelete='cascade', select=True, readonly=True, states={'draft':[('readonly',False)]}),
        'name': fields.char('Description', size=256, required=True, select=True, readonly=True, states={'draft':[('readonly',False)]}),
        'sequence': fields.integer('Sequence'),
        'delay': fields.float('Delivery Lead Time', required=True, help="Number of days between the order confirmation the the shipping of the products to the customer", readonly=True, states={'draft':[('readonly',False)]}),
        'product_id': fields.many2one('product.product', 'Product', domain=[('sale_ok', '=', True)], change_default=True),
        'invoice_lines': fields.many2many('account.invoice.line', 'sale_order_line_invoice_rel', 'order_line_id', 'invoice_id', 'Invoice Lines', readonly=True),
        'invoiced': fields.boolean('Invoiced', readonly=True),
        'procurement_id': fields.many2one('mrp.procurement', 'Procurement'),
        'price_unit': fields.float('Unit Price', required=True, digits=(16, int(config['price_accuracy'])), readonly=True, states={'draft':[('readonly',False)]}),
        'price_net': fields.function(_amount_line_net, method=True, string='Net Price', digits=(16, int(config['price_accuracy']))),
        'price_subtotal': fields.function(_amount_line, method=True, string='Subtotal', digits=(16, int(config['price_accuracy']))),
        'tax_id': fields.many2many('account.tax', 'sale_order_tax', 'order_line_id', 'tax_id', 'Taxes', readonly=True, states={'draft':[('readonly',False)]}),
        'type': fields.selection([('make_to_stock', 'from stock'), ('make_to_order', 'on order')], 'Procure Method', required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'property_ids': fields.many2many('mrp.property', 'sale_order_line_property_rel', 'order_id', 'property_id', 'Properties', readonly=True, states={'draft':[('readonly',False)]}),
        'address_allotment_id': fields.many2one('res.partner.address', 'Allotment Partner'),
        'product_uom_qty': fields.float('Quantity (UoM)', digits=(16, 2), required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'product_uom': fields.many2one('product.uom', 'Product UoM', required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'product_uos_qty': fields.float('Quantity (UoS)', readonly=True, states={'draft':[('readonly',False)]}),
        'product_uos': fields.many2one('product.uom', 'Product UoS'),
        'product_packaging': fields.many2one('product.packaging', 'Packaging'),
        'move_ids': fields.one2many('stock.move', 'sale_line_id', 'Inventory Moves', readonly=True),
        'discount': fields.float('Discount (%)', digits=(16, 2), readonly=True, states={'draft':[('readonly',False)]}),
        'number_packages': fields.function(_number_packages, method=True, type='integer', string='Number Packages'),
        'notes': fields.text('Notes'),
        'th_weight': fields.float('Weight', readonly=True, states={'draft':[('readonly',False)]}),
        'state': fields.selection([('draft', 'Draft'), ('confirmed', 'Confirmed'), ('done', 'Done'), ('cancel', 'Cancelled'), ('exception', 'Exception')], 'Status', required=True, readonly=True),
        'order_partner_id': fields.related('order_id', 'partner_id', type='many2one', relation='res.partner', string='Customer')
    }
    _order = 'sequence, id'
    _defaults = {
        'discount': lambda *a: 0.0,
        'delay': lambda *a: 0.0,
        'product_uom_qty': lambda *a: 1,
        'product_uos_qty': lambda *a: 1,
        'sequence': lambda *a: 10,
        'invoiced': lambda *a: 0,
        'state': lambda *a: 'draft',
        'type': lambda *a: 'make_to_stock',
        'product_packaging': lambda *a: False
    }

    def invoice_line_create(self, cr, uid, ids, context={}):
        def _get_line_qty(line):
            if (line.order_id.invoice_quantity=='order') or not line.procurement_id:
                if line.product_uos:
                    return line.product_uos_qty or 0.0
                return line.product_uom_qty
            else:
                return self.pool.get('mrp.procurement').quantity_get(cr, uid,
                        line.procurement_id.id, context)

        def _get_line_uom(line):
            if (line.order_id.invoice_quantity=='order') or not line.procurement_id:
                if line.product_uos:
                    return line.product_uos.id
                return line.product_uom.id
            else:
                return self.pool.get('mrp.procurement').uom_get(cr, uid,
                        line.procurement_id.id, context)

        create_ids = []
        sales = {}
        for line in self.browse(cr, uid, ids, context):
            if not line.invoiced:
                if line.product_id:
                    a = line.product_id.product_tmpl_id.property_account_income.id
                    if not a:
                        a = line.product_id.categ_id.property_account_income_categ.id
                    if not a:
                        raise osv.except_osv(_('Error !'),
                                _('There is no income account defined ' \
                                        'for this product: "%s" (id:%d)') % \
                                        (line.product_id.name, line.product_id.id,))
                else:
                    a = self.pool.get('ir.property').get(cr, uid,
                            'property_account_income_categ', 'product.category',
                            context=context)
                uosqty = _get_line_qty(line)
                uos_id = _get_line_uom(line)
                pu = 0.0
                if uosqty:
                    pu = round(line.price_unit * line.product_uom_qty / uosqty,
                            int(config['price_accuracy']))
                fpos = line.order_id.fiscal_position or False
                a = self.pool.get('account.fiscal.position').map_account(cr, uid, fpos, a)
                if not a:
                    raise osv.except_osv(_('Error !'),
                                _('There is no income category account defined in default Properties for Product Category or Fiscal Position is not defined !'))
                inv_id = self.pool.get('account.invoice.line').create(cr, uid, {
                    'name': line.name,
                    'origin': line.order_id.name,
                    'account_id': a,
                    'price_unit': pu,
                    'quantity': uosqty,
                    'discount': line.discount,
                    'uos_id': uos_id,
                    'product_id': line.product_id.id or False,
                    'invoice_line_tax_id': [(6, 0, [x.id for x in line.tax_id])],
                    'note': line.notes,
                    'account_analytic_id': line.order_id.project_id and line.order_id.project_id.id or False,
                })
                cr.execute('insert into sale_order_line_invoice_rel (order_line_id,invoice_id) values (%s,%s)', (line.id, inv_id))
                self.write(cr, uid, [line.id], {'invoiced': True})

                sales[line.order_id.id] = True
                create_ids.append(inv_id)

        # Trigger workflow events
        wf_service = netsvc.LocalService("workflow")
        for sid in sales.keys():
            wf_service.trg_write(uid, 'sale.order', sid, cr)
        return create_ids

    def button_cancel(self, cr, uid, ids, context={}):
        for line in self.browse(cr, uid, ids, context=context):
            if line.invoiced:
                raise osv.except_osv(_('Invalid action !'), _('You cannot cancel a sale order line that has already been invoiced !'))
        return self.write(cr, uid, ids, {'state': 'cancel'})

    def button_confirm(self, cr, uid, ids, context={}):
        return self.write(cr, uid, ids, {'state': 'confirmed'})

    def button_done(self, cr, uid, ids, context={}):
        wf_service = netsvc.LocalService("workflow")
        res = self.write(cr, uid, ids, {'state': 'done'})
        for line in self.browse(cr, uid, ids, context):
            wf_service.trg_write(uid, 'sale.order', line.order_id.id, cr)

        return res

    def uos_change(self, cr, uid, ids, product_uos, product_uos_qty=0, product_id=None):
        product_obj = self.pool.get('product.product')
        if not product_id:
            return {'value': {'product_uom': product_uos,
                'product_uom_qty': product_uos_qty}, 'domain': {}}

        product = product_obj.browse(cr, uid, product_id)
        value = {
            'product_uom': product.uom_id.id,
        }
        # FIXME must depend on uos/uom of the product and not only of the coeff.
        try:
            value.update({
                'product_uom_qty': product_uos_qty / product.uos_coeff,
                'th_weight': product_uos_qty / product.uos_coeff * product.weight
            })
        except ZeroDivisionError:
            pass
        return {'value': value}

    def copy_data(self, cr, uid, id, default=None, context={}):
        if not default:
            default = {}
        default.update({'state': 'draft', 'move_ids': [], 'invoiced': False, 'invoice_lines': []})
        return super(sale_order_line, self).copy_data(cr, uid, id, default, context)

    def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False):
        if not  partner_id:
            raise osv.except_osv(_('No Customer Defined !'), _('You have to select a customer in the sale form !\nPlease set one customer before choosing a product.'))
        warning = {}
        product_uom_obj = self.pool.get('product.uom')
        partner_obj = self.pool.get('res.partner')
        product_obj = self.pool.get('product.product')
        if partner_id:
            lang = partner_obj.browse(cr, uid, partner_id).lang
        context = {'lang': lang, 'partner_id': partner_id}
        if not product:
            return {'value': {'th_weight': 0, 'product_packaging': False,
                'product_uos_qty': qty}, 'domain': {'product_uom': [],
                   'product_uos': []}}

        if not date_order:
            date_order = time.strftime('%Y-%m-%d')

        result = {}
        product_obj = product_obj.browse(cr, uid, product, context=context)
        if not packaging and product_obj.packaging:
            packaging = product_obj.packaging[0].id
            result['product_packaging'] = packaging

        if packaging:
            default_uom = product_obj.uom_id and product_obj.uom_id.id
            pack = self.pool.get('product.packaging').browse(cr, uid, packaging, context)
            q = product_uom_obj._compute_qty(cr, uid, uom, pack.qty, default_uom)
#            qty = qty - qty % q + q
            if qty and (q and not (qty % q) == 0):
                ean = pack.ean
                qty_pack = pack.qty
                type_ul = pack.ul
                warn_msg = _("You selected a quantity of %d Units.\nBut it's not compatible with the selected packaging.\nHere is a proposition of quantities according to the packaging: ") % (qty)
                warn_msg = warn_msg + "\n\n" + _("EAN: ") + str(ean) + _(" Quantity: ") + str(qty_pack) + _(" Type of ul: ") + str(type_ul.name)
                warning = {
                    'title': _('Packing Information !'),
                    'message': warn_msg
                    }
            result['product_uom_qty'] = qty

        if uom:
            uom2 = product_uom_obj.browse(cr, uid, uom)
            if product_obj.uom_id.category_id.id != uom2.category_id.id:
                uom = False

        if uos:
            if product_obj.uos_id:
                uos2 = product_uom_obj.browse(cr, uid, uos)
                if product_obj.uos_id.category_id.id != uos2.category_id.id:
                    uos = False
            else:
                uos = False
        result.update({'type': product_obj.procure_method})
        if product_obj.description_sale:
            result['notes'] = product_obj.description_sale
        fpos = fiscal_position and self.pool.get('account.fiscal.position').browse(cr, uid, fiscal_position) or False
        if update_tax: #The quantity only have changed
            result['delay'] = (product_obj.sale_delay or 0.0)
            partner = partner_obj.browse(cr, uid, partner_id)
            result['tax_id'] = self.pool.get('account.fiscal.position').map_tax(cr, uid, fpos, product_obj.taxes_id)
        if not flag:
            result['name'] = self.pool.get('product.product').name_get(cr, uid, [product_obj.id], context=context)[0][1]
        domain = {}
        if (not uom) and (not uos):
            result['product_uom'] = product_obj.uom_id.id
            if product_obj.uos_id:
                result['product_uos'] = product_obj.uos_id.id
                result['product_uos_qty'] = qty * product_obj.uos_coeff
                uos_category_id = product_obj.uos_id.category_id.id
            else:
                result['product_uos'] = False
                result['product_uos_qty'] = qty
                uos_category_id = False
            result['th_weight'] = qty * product_obj.weight
            domain = {'product_uom':
                        [('category_id', '=', product_obj.uom_id.category_id.id)],
                        'product_uos':
                        [('category_id', '=', uos_category_id)]}

        elif uos and not uom: # only happens if uom is False
            result['product_uom'] = product_obj.uom_id and product_obj.uom_id.id
            result['product_uom_qty'] = qty_uos / product_obj.uos_coeff
            result['th_weight'] = result['product_uom_qty'] * product_obj.weight
        elif uom: # whether uos is set or not
            default_uom = product_obj.uom_id and product_obj.uom_id.id
            q = product_uom_obj._compute_qty(cr, uid, uom, qty, default_uom)
            if product_obj.uos_id:
                result['product_uos'] = product_obj.uos_id.id
                result['product_uos_qty'] = qty * product_obj.uos_coeff
            else:
                result['product_uos'] = False
                result['product_uos_qty'] = qty
            result['th_weight'] = q * product_obj.weight        # Round the quantity up

        # get unit price

        if not pricelist:
            warning = {
                'title': 'No Pricelist !',
                'message':
                    'You have to select a pricelist in the sale form !\n'
                    'Please set one before choosing a product.'
                }
        else:
            price = self.pool.get('product.pricelist').price_get(cr, uid, [pricelist],
                    product, qty or 1.0, partner_id, {
                        'uom': uom,
                        'date': date_order,
                        })[pricelist]
            if price is False:
                warning = {
                    'title': 'No valid pricelist line found !',
                    'message':
                        "Couldn't find a pricelist line matching this product and quantity.\n"
                        "You have to change either the product, the quantity or the pricelist."
                    }
            else:
                result.update({'price_unit': price})
        return {'value': result, 'domain': domain, 'warning': warning}

    def product_uom_change(self, cursor, user, ids, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False):
        res = self.product_id_change(cursor, user, ids, pricelist, product,
                qty=qty, uom=uom, qty_uos=qty_uos, uos=uos, name=name,
                partner_id=partner_id, lang=lang, update_tax=update_tax,
                date_order=date_order)
        if 'product_uom' in res['value']:
            del res['value']['product_uom']
        if not uom:
            res['value']['price_unit'] = 0.0
        return res

    def unlink(self, cr, uid, ids, context={}):
        """Allows to delete sale order lines in draft,cancel states"""
        for rec in self.browse(cr, uid, ids, context=context):
            if rec.state not in ['draft', 'cancel']:
                raise osv.except_osv(_('Invalid action !'), _('Cannot delete a sale order line which is %s !')%(rec.state,))
        return super(sale_order_line, self).unlink(cr, uid, ids, context=context)

sale_order_line()


class sale_config_picking_policy(osv.osv_memory):
    _name = 'sale.config.picking_policy'
    _columns = {
        'name': fields.char('Name', size=64),
        'picking_policy': fields.selection([
            ('direct', 'Direct Delivery'),
            ('one', 'All at Once')
        ], 'Packing Default Policy', required=True),
        'order_policy': fields.selection([
            ('manual', 'Invoice Based on Sales Orders'),
            ('picking', 'Invoice Based on Deliveries'),
        ], 'Shipping Default Policy', required=True),
        'step': fields.selection([
            ('one', 'Delivery Order Only'),
            ('two', 'Packing List & Delivery Order')
        ], 'Steps To Deliver a Sale Order', required=True,
           help="By default, Open ERP is able to manage complex routing and paths "\
           "of products in your warehouse and partner locations. This will configure "\
           "the most common and simple methods to deliver products to the customer "\
           "in one or two operations by the worker.")
    }
    _defaults = {
        'picking_policy': lambda *a: 'direct',
        'order_policy': lambda *a: 'picking',
        'step': lambda *a: 'one'
    }

    def set_default(self, cr, uid, ids, context=None):
        for o in self.browse(cr, uid, ids, context=context):
            ir_values_obj = self.pool.get('ir.values')
            ir_values_obj.set(cr, uid, 'default', False, 'picking_policy', ['sale.order'], o.picking_policy)
            ir_values_obj.set(cr, uid, 'default', False, 'order_policy', ['sale.order'], o.order_policy)

            if o.step == 'one':
                md = self.pool.get('ir.model.data')
                group_id = md._get_id(cr, uid, 'base', 'group_no_one')
                group_id = md.browse(cr, uid, group_id, context).res_id
                menu_id = md._get_id(cr, uid, 'stock', 'menu_action_picking_tree_delivery')
                menu_id = md.browse(cr, uid, menu_id, context).res_id
                self.pool.get('ir.ui.menu').write(cr, uid, [menu_id], {'groups_id': [(6, 0, [group_id])]})

                location_id = md._get_id(cr, uid, 'stock', 'stock_location_output')
                location_id = md.browse(cr, uid, location_id, context).res_id
                self.pool.get('stock.location').write(cr, uid, [location_id], {'chained_auto_packing': 'transparent'})

        return {
                'view_type': 'form',
                "view_mode": 'form',
                'res_model': 'ir.actions.configuration.wizard',
                'type': 'ir.actions.act_window',
                'target': 'new',
         }

    def action_cancel(self, cr, uid, ids, context=None):
        return {
                'view_type': 'form',
                "view_mode": 'form',
                'res_model': 'ir.actions.configuration.wizard',
                'type': 'ir.actions.act_window',
                'target': 'new',
         }

sale_config_picking_policy()

