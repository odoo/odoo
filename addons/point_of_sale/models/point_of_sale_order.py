# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime
import logging
import time

from functools import partial

from openerp import tools, SUPERUSER_ID
from openerp.osv import fields, osv
from openerp.tools import float_is_zero
from openerp.tools.translate import _
from openerp.exceptions import UserError

_logger = logging.getLogger(__name__)

class pos_order(osv.osv):
    _name = "pos.order"
    _description = "Point of Sale"
    _order = "id desc"

    def _amount_line_tax(self, cr, uid, line, context=None):
        taxes = line.product_id.taxes_id.filtered(lambda t: t.company_id.id == line.order_id.company_id.id)
        price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
        cur = line.order_id.pricelist_id.currency_id
        taxes = taxes.compute_all(price, cur, line.qty, product=line.product_id, partner=line.order_id.partner_id or False)['taxes']
        val = 0.0
        for c in taxes:
            val += c.get('amount', 0.0)
        return val

    def _order_fields(self, cr, uid, ui_order, context=None):
        process_line = partial(self.pool['pos.order.line']._order_line_fields, cr, uid, context=context)
        return {
            'name':         ui_order['name'],
            'user_id':      ui_order['user_id'] or False,
            'session_id':   ui_order['pos_session_id'],
            'lines':        [process_line(l) for l in ui_order['lines']] if ui_order['lines'] else False,
            'pos_reference':ui_order['name'],
            'partner_id':   ui_order['partner_id'] or False,
            'date_order':   ui_order['creation_date']
        }

    def _payment_fields(self, cr, uid, ui_paymentline, context=None):
        return {
            'amount':       ui_paymentline['amount'] or 0.0,
            'payment_date': ui_paymentline['name'],
            'statement_id': ui_paymentline['statement_id'],
            'payment_name': ui_paymentline.get('note',False),
            'journal':      ui_paymentline['journal_id'],
        }

    def _get_rescue_session(self, cr, uid, order, context=None):
        """ Find or generate a rescue session """
        pos_session = self.pool['pos.session']
        date = order.get('creation_date', time.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT))
        closed_session = pos_session.browse(cr, uid, order['pos_session_id'], context=context)
        rescue_session_ids = pos_session.search(cr, uid, [
            ('rescue', '=', True), ('config_id', '=', closed_session.config_id.id),
            ('start_at', '<=', date), ('state', '=', 'opened')
        ], limit=1, context=context)
        if not rescue_session_ids:
            return pos_session.copy(cr, uid, order['pos_session_id'], default={
                'rescue': True,
            }, context=context)
        return rescue_session_ids[0]

    def _process_order(self, cr, uid, order, context=None):
        session = self.pool['pos.session'].browse(cr, uid, order['pos_session_id'], context=context)
        if session.state == 'closed':
            rescue_session_id = self._get_rescue_session(cr, uid, order, context=context)
            order['pos_session_id'] = rescue_session_id
            session = self.pool['pos.session'].browse(cr, uid, rescue_session_id, context=context)
        order_id = self.create(cr, uid, self._order_fields(cr, uid, order, context=context),context)
        journal_ids = set()
        for payments in order['statement_ids']:
            self.add_payment(cr, uid, order_id, self._payment_fields(cr, uid, payments[2], context=context), context=context)
            journal_ids.add(payments[2]['journal_id'])

        if session.sequence_number <= order['sequence_number']:
            session.write({'sequence_number': order['sequence_number'] + 1})
            session.refresh()

        if not float_is_zero(order['amount_return'], self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')):
            cash_journal = session.cash_journal_id.id
            if not cash_journal:
                # Select for change one of the cash journals used in this payment
                cash_journal_ids = self.pool['account.journal'].search(cr, uid, [
                    ('type', '=', 'cash'),
                    ('id', 'in', list(journal_ids)),
                ], limit=1, context=context)
                if not cash_journal_ids:
                    # If none, select for change one of the cash journals of the POS
                    # This is used for example when a customer pays by credit card
                    # an amount higher than total amount of the order and gets cash back
                    cash_journal_ids = [statement.journal_id.id for statement in session.statement_ids
                                        if statement.journal_id.type == 'cash']
                    if not cash_journal_ids:
                        raise UserError(_("No cash statement found for this session. Unable to record returned cash."))
                cash_journal = cash_journal_ids[0]
            self.add_payment(cr, uid, order_id, {
                'amount': -order['amount_return'],
                'payment_date': time.strftime('%Y-%m-%d %H:%M:%S'),
                'payment_name': _('return'),
                'journal': cash_journal,
            }, context=context)
        return order_id

    def create_from_ui(self, cr, uid, orders, context=None):
        # Keep only new orders
        submitted_references = [o['data']['name'] for o in orders]
        existing_order_ids = self.search(cr, uid, [('pos_reference', 'in', submitted_references)], context=context)
        existing_orders = self.read(cr, uid, existing_order_ids, ['pos_reference'], context=context)
        existing_references = set([o['pos_reference'] for o in existing_orders])
        orders_to_save = [o for o in orders if o['data']['name'] not in existing_references]

        order_ids = []

        for tmp_order in orders_to_save:
            to_invoice = tmp_order['to_invoice']
            order = tmp_order['data']
            order_id = self._process_order(cr, uid, order, context=context)
            order_ids.append(order_id)

            try:
                self.signal_workflow(cr, uid, [order_id], 'paid')
            except Exception as e:
                _logger.error('Could not fully process the POS Order: %s', tools.ustr(e))

            if to_invoice:
                self.action_invoice(cr, uid, [order_id], context)
                order_obj = self.browse(cr, uid, order_id, context)
                self.pool['account.invoice'].signal_workflow(cr, SUPERUSER_ID, [order_obj.invoice_id.id], 'invoice_open')

        return order_ids

    def write(self, cr, uid, ids, vals, context=None):
        res = super(pos_order, self).write(cr, uid, ids, vals, context=context)
        #If you change the partner of the PoS order, change also the partner of the associated bank statement lines
        partner_obj = self.pool.get('res.partner')
        bsl_obj = self.pool.get("account.bank.statement.line")
        if 'partner_id' in vals:
            for posorder in self.browse(cr, uid, ids, context=context):
                if posorder.invoice_id:
                    raise UserError(_("You cannot change the partner of a POS order for which an invoice has already been issued."))
                if vals['partner_id']:
                    p_id = partner_obj.browse(cr, uid, vals['partner_id'], context=context)
                    part_id = partner_obj._find_accounting_partner(p_id).id
                else:
                    part_id = False
                bsl_ids = [x.id for x in posorder.statement_ids]
                bsl_obj.write(cr, uid, bsl_ids, {'partner_id': part_id}, context=context)
        return res

    def unlink(self, cr, uid, ids, context=None):
        for rec in self.browse(cr, uid, ids, context=context):
            if rec.state not in ('draft','cancel'):
                raise UserError(_('In order to delete a sale, it must be new or cancelled.'))
        return super(pos_order, self).unlink(cr, uid, ids, context=context)

    def onchange_partner_id(self, cr, uid, ids, part=False, context=None):
        if not part:
            return {'value': {}}
        pricelist = self.pool.get('res.partner').browse(cr, uid, part, context=context).property_product_pricelist.id
        return {'value': {'pricelist_id': pricelist}}

    def _amount_all(self, cr, uid, ids, name, args, context=None):
        cur_obj = self.pool.get('res.currency')
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = {
                'amount_paid': 0.0,
                'amount_return':0.0,
                'amount_tax':0.0,
            }
            val1 = val2 = 0.0
            cur = order.pricelist_id.currency_id
            for payment in order.statement_ids:
                res[order.id]['amount_paid'] +=  payment.amount
                res[order.id]['amount_return'] += (payment.amount < 0 and payment.amount or 0)
            for line in order.lines:
                val1 += self._amount_line_tax(cr, uid, line, context=context)
                val2 += line.price_subtotal
            res[order.id]['amount_tax'] = cur_obj.round(cr, uid, cur, val1)
            amount_untaxed = cur_obj.round(cr, uid, cur, val2)
            res[order.id]['amount_total'] = res[order.id]['amount_tax'] + amount_untaxed
        return res

    _columns = {
        'name': fields.char('Order Ref', required=True, readonly=True, copy=False),
        'company_id':fields.many2one('res.company', 'Company', required=True, readonly=True),
        'date_order': fields.datetime('Order Date', readonly=True, select=True),
        'user_id': fields.many2one('res.users', 'Salesman', help="Person who uses the cash register. It can be a reliever, a student or an interim employee."),
        'amount_tax': fields.function(_amount_all, string='Taxes', digits=0, multi='all'),
        'amount_total': fields.function(_amount_all, string='Total', digits=0,  multi='all'),
        'amount_paid': fields.function(_amount_all, string='Paid', states={'draft': [('readonly', False)]}, readonly=True, digits=0, multi='all'),
        'amount_return': fields.function(_amount_all, string='Returned', digits=0, multi='all'),
        'lines': fields.one2many('pos.order.line', 'order_id', 'Order Lines', states={'draft': [('readonly', False)]}, readonly=True, copy=True),
        'statement_ids': fields.one2many('account.bank.statement.line', 'pos_statement_id', 'Payments', states={'draft': [('readonly', False)]}, readonly=True),
        'pricelist_id': fields.many2one('product.pricelist', 'Pricelist', required=True, states={'draft': [('readonly', False)]}, readonly=True),
        'partner_id': fields.many2one('res.partner', 'Customer', change_default=True, select=1, states={'draft': [('readonly', False)], 'paid': [('readonly', False)]}),
        'sequence_number': fields.integer('Sequence Number', help='A session-unique sequence number for the order'),

        'session_id' : fields.many2one('pos.session', 'Session', 
                                        required=True,
                                        select=1,
                                        domain="[('state', '=', 'opened')]",
                                        states={'draft' : [('readonly', False)]},
                                        readonly=True),

        'state': fields.selection([('draft', 'New'),
                                   ('cancel', 'Cancelled'),
                                   ('paid', 'Paid'),
                                   ('done', 'Posted'),
                                   ('invoiced', 'Invoiced')],
                                  'Status', readonly=True, copy=False),

        'invoice_id': fields.many2one('account.invoice', 'Invoice', copy=False),
        'account_move': fields.many2one('account.move', 'Journal Entry', readonly=True, copy=False),
        'picking_id': fields.many2one('stock.picking', 'Picking', readonly=True, copy=False),
        'picking_type_id': fields.related('session_id', 'config_id', 'picking_type_id', string="Picking Type", type='many2one', relation='stock.picking.type'),
        'location_id': fields.related('session_id', 'config_id', 'stock_location_id', string="Location", type='many2one', store=True, relation='stock.location'),
        'note': fields.text('Internal Notes'),
        'nb_print': fields.integer('Number of Print', readonly=True, copy=False),
        'pos_reference': fields.char('Receipt Ref', readonly=True, copy=False),
        'sale_journal': fields.related('session_id', 'config_id', 'journal_id', relation='account.journal', type='many2one', string='Sale Journal', store=True, readonly=True),
    }

    def _default_session(self, cr, uid, context=None):
        so = self.pool.get('pos.session')
        session_ids = so.search(cr, uid, [('state','=', 'opened'), ('user_id','=',uid)], context=context)
        return session_ids and session_ids[0] or False

    def _default_pricelist(self, cr, uid, context=None):
        session_ids = self._default_session(cr, uid, context) 
        if session_ids:
            session_record = self.pool.get('pos.session').browse(cr, uid, session_ids, context=context)
            return session_record.config_id.pricelist_id and session_record.config_id.pricelist_id.id or False
        return False

    def _get_out_picking_type(self, cr, uid, context=None):
        return self.pool.get('ir.model.data').xmlid_to_res_id(
                    cr, uid, 'point_of_sale.picking_type_posout', context=context)

    _defaults = {
        'user_id': lambda self, cr, uid, context: uid,
        'state': 'draft',
        'name': '/', 
        'date_order': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'nb_print': 0,
        'sequence_number': 1,
        'session_id': _default_session,
        'company_id': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id,
        'pricelist_id': _default_pricelist,
    }

    def create(self, cr, uid, values, context=None):
        if values.get('session_id'):
            # set name based on the sequence specified on the config
            session = self.pool['pos.session'].browse(cr, uid, values['session_id'], context=context)
            values['name'] = session.config_id.sequence_id._next()
            values.setdefault('session_id', session.config_id.pricelist_id.id)
        else:
            # fallback on any pos.order sequence
            values['name'] = self.pool.get('ir.sequence').next_by_code(cr, uid, 'pos.order', context=context)
        return super(pos_order, self).create(cr, uid, values, context=context)

    def test_paid(self, cr, uid, ids, context=None):
        """A Point of Sale is paid when the sum
        @return: True
        """
        for order in self.browse(cr, uid, ids, context=context):
            if order.lines and not order.amount_total:
                return True
            if (not order.lines) or (not order.statement_ids) or \
                (abs(order.amount_total-order.amount_paid) > 0.00001):
                return False
        return True

    def create_picking(self, cr, uid, ids, context=None):
        """Create a picking for each order and validate it."""
        picking_obj = self.pool.get('stock.picking')
        partner_obj = self.pool.get('res.partner')
        move_obj = self.pool.get('stock.move')

        for order in self.browse(cr, uid, ids, context=context):
            if all(t == 'service' for t in order.lines.mapped('product_id.type')):
                continue
            addr = order.partner_id and partner_obj.address_get(cr, uid, [order.partner_id.id], ['delivery']) or {}
            picking_type = order.picking_type_id
            picking_id = False
            location_id = order.location_id.id
            if order.partner_id:
                destination_id = order.partner_id.property_stock_customer.id
            elif picking_type:
                if not picking_type.default_location_dest_id:
                    raise UserError(_('Missing source or destination location for picking type %s. Please configure those fields and try again.' % (picking_type.name,)))
                destination_id = picking_type.default_location_dest_id.id
            else:
                destination_id = partner_obj.default_get(cr, uid, ['property_stock_customer'], context=context)['property_stock_customer']
            if picking_type:
                picking_id = picking_obj.create(cr, uid, {
                    'origin': order.name,
                    'partner_id': addr.get('delivery',False),
                    'date_done' : order.date_order,
                    'picking_type_id': picking_type.id,
                    'company_id': order.company_id.id,
                    'move_type': 'direct',
                    'note': order.note or "",
                    'invoice_state': 'none',
                    'location_id': location_id,
                    'location_dest_id': destination_id,
                }, context=context)
                self.write(cr, uid, [order.id], {'picking_id': picking_id}, context=context)

            move_list = []
            for line in order.lines:
                if line.product_id and line.product_id.type == 'service':
                    continue

                move_list.append(move_obj.create(cr, uid, {
                    'name': line.name,
                    'product_uom': line.product_id.uom_id.id,
                    'product_uos': line.product_id.uom_id.id,
                    'picking_id': picking_id,
                    'picking_type_id': picking_type.id, 
                    'product_id': line.product_id.id,
                    'product_uos_qty': abs(line.qty),
                    'product_uom_qty': abs(line.qty),
                    'state': 'draft',
                    'location_id': location_id if line.qty >= 0 else destination_id,
                    'location_dest_id': destination_id if line.qty >= 0 else location_id,
                }, context=context))
                
            if picking_id:
                picking_obj.action_confirm(cr, uid, [picking_id], context=context)
                picking_obj.force_assign(cr, uid, [picking_id], context=context)
                picking_obj.action_done(cr, uid, [picking_id], context=context)
            elif move_list:
                move_obj.action_confirm(cr, uid, move_list, context=context)
                move_obj.force_assign(cr, uid, move_list, context=context)
                move_obj.action_done(cr, uid, move_list, context=context)
        return True

    def cancel_order(self, cr, uid, ids, context=None):
        """ Changes order state to cancel
        @return: True
        """
        stock_picking_obj = self.pool.get('stock.picking')
        for order in self.browse(cr, uid, ids, context=context):
            stock_picking_obj.action_cancel(cr, uid, [order.picking_id.id])
            if stock_picking_obj.browse(cr, uid, order.picking_id.id, context=context).state <> 'cancel':
                raise UserError(_('Unable to cancel the picking.'))
        self.write(cr, uid, ids, {'state': 'cancel'}, context=context)
        return True

    def add_payment(self, cr, uid, order_id, data, context=None):
        """Create a new payment for the order"""
        context = dict(context or {})
        statement_line_obj = self.pool.get('account.bank.statement.line')
        property_obj = self.pool.get('ir.property')
        order = self.browse(cr, uid, order_id, context=context)
        date = data.get('payment_date', time.strftime('%Y-%m-%d'))
        if len(date) > 10:
            timestamp = datetime.strptime(date, tools.DEFAULT_SERVER_DATETIME_FORMAT)
            ts = fields.datetime.context_timestamp(cr, uid, timestamp, context)
            date = ts.strftime(tools.DEFAULT_SERVER_DATE_FORMAT)
        args = {
            'amount': data['amount'],
            'date': date,
            'name': order.name + ': ' + (data.get('payment_name', '') or ''),
            'partner_id': order.partner_id and self.pool.get("res.partner")._find_accounting_partner(order.partner_id).id or False,
        }

        journal_id = data.get('journal', False)
        statement_id = data.get('statement_id', False)
        assert journal_id or statement_id, "No statement_id or journal_id passed to the method!"

        journal = self.pool['account.journal'].browse(cr, uid, journal_id, context=context)
        # use the company of the journal and not of the current user
        company_cxt = dict(context, force_company=journal.company_id.id)
        account_def = property_obj.get(cr, uid, 'property_account_receivable_id', 'res.partner', context=company_cxt)
        args['account_id'] = (order.partner_id and order.partner_id.property_account_receivable_id \
                             and order.partner_id.property_account_receivable_id.id) or (account_def and account_def.id) or False

        if not args['account_id']:
            if not args['partner_id']:
                msg = _('There is no receivable account defined to make payment.')
            else:
                msg = _('There is no receivable account defined to make payment for the partner: "%s" (id:%d).') % (order.partner_id.name, order.partner_id.id,)
            raise UserError(msg)

        context.pop('pos_session_id', False)

        for statement in order.session_id.statement_ids:
            if statement.id == statement_id:
                journal_id = statement.journal_id.id
                break
            elif statement.journal_id.id == journal_id:
                statement_id = statement.id
                break

        if not statement_id:
            raise UserError(_('You have to open at least one cashbox.'))

        args.update({
            'statement_id': statement_id,
            'pos_statement_id': order_id,
            'journal_id': journal_id,
            'ref': order.session_id.name,
        })

        statement_line_obj.create(cr, uid, args, context=context)

        return statement_id

    def refund(self, cr, uid, ids, context=None):
        """Create a copy of order  for refund order"""
        clone_list = []
        line_obj = self.pool.get('pos.order.line')
        
        for order in self.browse(cr, uid, ids, context=context):
            current_session_ids = self.pool.get('pos.session').search(cr, uid, [
                ('state', '!=', 'closed'),
                ('user_id', '=', uid)], context=context)
            if not current_session_ids:
                raise UserError(_('To return product(s), you need to open a session that will be used to register the refund.'))

            clone_id = self.copy(cr, uid, order.id, {
                'name': order.name + ' REFUND', # not used, name forced by create
                'session_id': current_session_ids[0],
                'date_order': time.strftime('%Y-%m-%d %H:%M:%S'),
            }, context=context)
            clone_list.append(clone_id)

        for clone in self.browse(cr, uid, clone_list, context=context):
            for order_line in clone.lines:
                line_obj.write(cr, uid, [order_line.id], {
                    'qty': -order_line.qty
                }, context=context)

        abs = {
            'name': _('Return Products'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'pos.order',
            'res_id':clone_list[0],
            'view_id': False,
            'context':context,
            'type': 'ir.actions.act_window',
            'target': 'current',
        }
        return abs

    def action_invoice_state(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'invoiced'}, context=context)

    def action_invoice(self, cr, uid, ids, context=None):
        inv_ref = self.pool.get('account.invoice')
        inv_line_ref = self.pool.get('account.invoice.line')
        product_obj = self.pool.get('product.product')
        inv_ids = []

        for order in self.pool.get('pos.order').browse(cr, uid, ids, context=context):
            # Force company for all SUPERUSER_ID action
            company_id = order.company_id.id
            local_context = dict(context or {}, force_company=company_id, company_id=company_id)
            if order.invoice_id:
                inv_ids.append(order.invoice_id.id)
                continue

            if not order.partner_id:
                raise UserError(_('Please provide a partner for the sale.'))

            acc = order.partner_id.property_account_receivable_id.id
            inv = {
                'name': order.name,
                'origin': order.name,
                'account_id': acc,
                'journal_id': order.sale_journal.id or None,
                'type': 'out_invoice',
                'reference': order.name,
                'partner_id': order.partner_id.id,
                'comment': order.note or '',
                'currency_id': order.pricelist_id.currency_id.id, # considering partner's sale pricelist's currency
                'company_id': company_id,
            }
            invoice = inv_ref.new(cr, uid, inv)
            invoice._onchange_partner_id()

            inv = invoice._convert_to_write(invoice._cache)
            if not inv.get('account_id', None):
                inv['account_id'] = acc
            inv_id = inv_ref.create(cr, SUPERUSER_ID, inv, context=local_context)

            self.write(cr, uid, [order.id], {'invoice_id': inv_id, 'state': 'invoiced'}, context=local_context)
            inv_ids.append(inv_id)
            for line in order.lines:
                inv_name = product_obj.name_get(cr, uid, [line.product_id.id], context=local_context)[0][1]
                inv_line = {
                    'invoice_id': inv_id,
                    'product_id': line.product_id.id,
                    'quantity': line.qty,
                    'account_analytic_id': self._prepare_analytic_account(cr, uid, line, context=local_context),
                    'name': inv_name,
                }

                #Oldlin trick
                invoice_line = inv_line_ref.new(cr, SUPERUSER_ID, inv_line, context=local_context)
                invoice_line._onchange_product_id()
                invoice_line.invoice_line_tax_ids = [tax.id for tax in invoice_line.invoice_line_tax_ids if tax.company_id.id == company_id]
                # We convert a new id object back to a dictionary to write to bridge between old and new api
                inv_line = invoice_line._convert_to_write(invoice_line._cache)
                inv_line_ref.create(cr, SUPERUSER_ID, inv_line, context=local_context)
            inv_ref.compute_taxes(cr, SUPERUSER_ID, [inv_id], context=local_context)
            self.signal_workflow(cr, uid, [order.id], 'invoice')
            inv_ref.signal_workflow(cr, SUPERUSER_ID, [inv_id], 'validate')

        if not inv_ids: return {}

        mod_obj = self.pool.get('ir.model.data')
        res = mod_obj.get_object_reference(cr, uid, 'account', 'invoice_form')
        res_id = res and res[1] or False
        return {
            'name': _('Customer Invoice'),
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': [res_id],
            'res_model': 'account.invoice',
            'context': "{'type':'out_invoice'}",
            'type': 'ir.actions.act_window',
            'target': 'current',
            'res_id': inv_ids and inv_ids[0] or False,
        }

    def create_account_move(self, cr, uid, ids, context=None):
        return self._create_account_move_line(cr, uid, ids, None, None, context=context)

    def _prepare_analytic_account(self, cr, uid, line, context=None):
        '''This method is designed to be inherited in a custom module'''
        return False

    def _create_account_move(self, cr, uid, dt, ref, journal_id, company_id, context=None):
        start_at_datetime = datetime.strptime(dt, tools.DEFAULT_SERVER_DATETIME_FORMAT)
        date_tz_user = fields.datetime.context_timestamp(cr, uid, start_at_datetime, context=context)
        date_tz_user = date_tz_user.strftime(tools.DEFAULT_SERVER_DATE_FORMAT)
        return self.pool['account.move'].create(cr, SUPERUSER_ID, {'ref': ref, 'journal_id': journal_id, 'date': date_tz_user}, context=context)

    def _create_account_move_line(self, cr, uid, ids, session=None, move_id=None, context=None):
        # Tricky, via the workflow, we only have one id in the ids variable
        """Create a account move line of order grouped by products or not."""
        account_move_obj = self.pool.get('account.move')
        account_tax_obj = self.pool.get('account.tax')
        property_obj = self.pool.get('ir.property')
        cur_obj = self.pool.get('res.currency')

        #session_ids = set(order.session_id for order in self.browse(cr, uid, ids, context=context))

        if session and not all(session.id == order.session_id.id for order in self.browse(cr, uid, ids, context=context)):
            raise UserError(_('Selected orders do not have the same session!'))

        grouped_data = {}
        have_to_group_by = session and session.config_id.group_by or False

        for order in self.browse(cr, uid, ids, context=context):
            if order.account_move:
                continue
            if order.state != 'paid':
                continue

            current_company = order.sale_journal.company_id

            group_tax = {}
            account_def = property_obj.get(cr, uid, 'property_account_receivable_id', 'res.partner', context=context)

            order_account = order.partner_id and \
                            order.partner_id.property_account_receivable_id and \
                            order.partner_id.property_account_receivable_id.id or \
                            account_def and account_def.id

            if move_id is None:
                # Create an entry for the sale
                move_id = self._create_account_move(cr, uid, order.session_id.start_at, order.name, order.sale_journal.id, order.company_id.id, context=context)

            move = account_move_obj.browse(cr, SUPERUSER_ID, move_id, context=context)

            def insert_data(data_type, values):
                # if have_to_group_by:

                sale_journal_id = order.sale_journal.id

                # 'quantity': line.qty,
                # 'product_id': line.product_id.id,
                values.update({
                    'ref': order.name,
                    'partner_id': order.partner_id and self.pool.get("res.partner")._find_accounting_partner(order.partner_id).id or False,
                    'journal_id' : sale_journal_id,
                    'date' : fields.date.context_today(self, cr, uid, context=context),
                    'move_id' : move_id,
                    'company_id': current_company.id,
                })

                if data_type == 'product':
                    key = ('product', values['partner_id'], (values['product_id'], values['name']), values['analytic_account_id'], values['debit'] > 0)
                elif data_type == 'tax':
                    key = ('tax', values['partner_id'], values['tax_line_id'], values['debit'] > 0)
                elif data_type == 'counter_part':
                    key = ('counter_part', values['partner_id'], values['account_id'], values['debit'] > 0)
                else:
                    return

                grouped_data.setdefault(key, [])

                # if not have_to_group_by or (not grouped_data[key]):
                #     grouped_data[key].append(values)
                # else:
                #     pass

                if have_to_group_by:
                    if not grouped_data[key]:
                        grouped_data[key].append(values)
                    else:
                        for line in grouped_data[key]:
                            if line.get('tax_code_id') == values.get('tax_code_id'):
                                current_value = line
                                current_value['quantity'] = current_value.get('quantity', 0.0) +  values.get('quantity', 0.0)
                                current_value['credit'] = current_value.get('credit', 0.0) + values.get('credit', 0.0)
                                current_value['debit'] = current_value.get('debit', 0.0) + values.get('debit', 0.0)
                                break
                        else:
                            grouped_data[key].append(values)
                else:
                    grouped_data[key].append(values)

            #because of the weird way the pos order is written, we need to make sure there is at least one line, 
            #because just after the 'for' loop there are references to 'line' and 'income_account' variables (that 
            #are set inside the for loop)
            #TOFIX: a deep refactoring of this method (and class!) is needed in order to get rid of this stupid hack
            assert order.lines, _('The POS order must have lines when calling this method')
            # Create an move for each order line

            cur = order.pricelist_id.currency_id
            for line in order.lines:
                amount = line.price_subtotal

                # Search for the income account
                if  line.product_id.property_account_income_id.id:
                    income_account = line.product_id.property_account_income_id.id
                elif line.product_id.categ_id.property_account_income_categ_id.id:
                    income_account = line.product_id.categ_id.property_account_income_categ_id.id
                else:
                    raise UserError(_('Please define income '\
                        'account for this product: "%s" (id:%d).') \
                        % (line.product_id.name, line.product_id.id))

                name = line.product_id.name
                if line.notice:
                    # add discount reason in move
                    name = name + ' (' + line.notice + ')'

                # Create a move for the line for the order line
                insert_data('product', {
                    'name': name,
                    'quantity': line.qty,
                    'product_id': line.product_id.id,
                    'account_id': income_account,
                    'analytic_account_id': self._prepare_analytic_account(cr, uid, line, context=context),
                    'credit': ((amount>0) and amount) or 0.0,
                    'debit': ((amount<0) and -amount) or 0.0,
                    'partner_id': order.partner_id and self.pool.get("res.partner")._find_accounting_partner(order.partner_id).id or False
                })

                # Create the tax lines
                taxes = []
                for t in line.product_id.taxes_id:
                    if t.company_id.id == current_company.id:
                        taxes.append(t.id)
                if not taxes:
                    continue
                for tax in account_tax_obj.browse(cr,uid, taxes, context=context).compute_all(line.price_unit * (100.0-line.discount) / 100.0, cur, line.qty)['taxes']:
                    insert_data('tax', {
                        'name': _('Tax') + ' ' + tax['name'],
                        'product_id': line.product_id.id,
                        'quantity': line.qty,
                        'account_id': tax['account_id'] or income_account,
                        'credit': ((tax['amount']>0) and tax['amount']) or 0.0,
                        'debit': ((tax['amount']<0) and -tax['amount']) or 0.0,
                        'tax_line_id': tax['id'],
                        'partner_id': order.partner_id and self.pool.get("res.partner")._find_accounting_partner(order.partner_id).id or False
                    })

            # counterpart
            insert_data('counter_part', {
                'name': _("Trade Receivables"), #order.name,
                'account_id': order_account,
                'credit': ((order.amount_total < 0) and -order.amount_total) or 0.0,
                'debit': ((order.amount_total > 0) and order.amount_total) or 0.0,
                'partner_id': order.partner_id and self.pool.get("res.partner")._find_accounting_partner(order.partner_id).id or False
            })

            order.write({'state':'done', 'account_move': move_id})

        all_lines = []
        for group_key, group_data in grouped_data.iteritems():
            for value in group_data:
                all_lines.append((0, 0, value),)
        if move_id: #In case no order was changed
            self.pool.get("account.move").write(cr, SUPERUSER_ID, [move_id], {'line_ids':all_lines}, context=context)
            self.pool.get("account.move").post(cr, SUPERUSER_ID, [move_id], context=context)

        return True

    def action_payment(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'payment'}, context=context)

    def action_paid(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'paid'}, context=context)
        self.create_picking(cr, uid, ids, context=context)
        return True

    def action_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'cancel'}, context=context)
        return True

    def action_done(self, cr, uid, ids, context=None):
        self.create_account_move(cr, uid, ids, context=context)
        return True


class pos_order_line(osv.osv):
    _name = "pos.order.line"
    _description = "Lines of Point of Sale"
    _rec_name = "product_id"

    def _order_line_fields(self, cr, uid, line, context=None):
        if line and 'tax_ids' not in line[2]:
            product = self.pool['product.product'].browse(cr, uid, line[2]['product_id'], context=context)
            line[2]['tax_ids'] = [(6, 0, [x.id for x in product.taxes_id])]
        return line

    def _amount_line_all(self, cr, uid, ids, field_names, arg, context=None):
        res = dict([(i, {}) for i in ids])
        account_tax_obj = self.pool.get('account.tax')
        for line in self.browse(cr, uid, ids, context=context):
            cur = line.order_id.pricelist_id.currency_id
            taxes_ids = [ tax.id for tax in line.product_id.taxes_id if tax.company_id.id == line.order_id.company_id.id ]
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            res[line.id]['price_subtotal'] = res[line.id]['price_subtotal_incl'] = price * line.qty
            if taxes_ids:
                taxes = account_tax_obj.browse(cr, uid, taxes_ids, context).compute_all(price, cur, line.qty, product=line.product_id, partner=line.order_id.partner_id or False)
                res[line.id]['price_subtotal'] = taxes['total_excluded']
                res[line.id]['price_subtotal_incl'] = taxes['total_included']
        return res

    def onchange_product_id(self, cr, uid, ids, pricelist, product_id, qty=0, partner_id=False, context=None):
        context = context or {}
        if not product_id:
           return {}
        if not pricelist:
           raise UserError(
               _('You have to select a pricelist in the sale form !\n' \
               'Please set one before choosing a product.'))

        price = self.pool.get('product.pricelist').price_get(cr, uid, [pricelist],
               product_id, qty or 1.0, partner_id)[pricelist]

        result = self.onchange_qty(cr, uid, ids, pricelist, product_id, 0.0, qty, price, context=context)
        result['value']['price_unit'] = price
        return result

    def onchange_qty(self, cr, uid, ids, pricelist, product, discount, qty, price_unit, context=None):
        result = {}
        if not product:
            return result
        if not pricelist:
           raise UserError(_('You have to select a pricelist in the sale form !'))

        account_tax_obj = self.pool.get('account.tax')

        prod = self.pool.get('product.product').browse(cr, uid, product, context=context)

        price = price_unit * (1 - (discount or 0.0) / 100.0)
        result['price_subtotal'] = result['price_subtotal_incl'] = price * qty
        cur = self.pool.get('product.pricelist').browse(cr, uid, [pricelist], context=context).currency_id
        if (prod.taxes_id):
            taxes = prod.taxes_id.compute_all(price, cur, qty, product=prod, partner=False)
            result['price_subtotal'] = taxes['total_excluded']
            result['price_subtotal_incl'] = taxes['total_included']
        return {'value': result}

    _columns = {
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'name': fields.char('Line No', required=True, copy=False),
        'notice': fields.char('Discount Notice'),
        'product_id': fields.many2one('product.product', 'Product', domain=[('sale_ok', '=', True)], required=True, change_default=True),
        'price_unit': fields.float(string='Unit Price', digits=0),
        'qty': fields.float('Quantity', digits=0),
        'price_subtotal': fields.function(_amount_line_all, multi='pos_order_line_amount', digits=0, string='Subtotal w/o Tax', store=True),
        'price_subtotal_incl': fields.function(_amount_line_all, multi='pos_order_line_amount', digits=0, string='Subtotal', store=True),
        'discount': fields.float('Discount (%)', digits=0),
        'order_id': fields.many2one('pos.order', 'Order Ref', ondelete='cascade'),
        'create_date': fields.datetime('Creation Date', readonly=True),
        'tax_ids': fields.many2many('account.tax', string='Taxes', readonly=True),
    }

    _defaults = {
        'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').next_by_code(cr, uid, 'pos.order.line'),
        'qty': lambda *a: 1,
        'discount': lambda *a: 0.0,
        'company_id': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id,
    }
