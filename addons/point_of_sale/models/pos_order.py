# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime
import logging
import time

from functools import partial

from openerp import api, fields, models, tools, _
from openerp.tools import float_is_zero
from openerp.exceptions import UserError

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _name = "pos.order"
    _description = "Point of Sale"
    _order = "id desc"

    def _amount_line_tax(self, line):
        taxes = line.product_id.taxes_id.filtered(lambda t: t.company_id.id == line.order_id.company_id.id)
        price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
        taxes = taxes.compute_all(price, line.order_id.pricelist_id.currency_id, line.qty, product=line.product_id, partner=line.order_id.partner_id or False)['taxes']
        val = 0.0
        for tax in taxes:
            val += tax.get('amount', 0.0)
        return val

    @api.model
    def _order_fields(self, ui_order):
        process_line = partial(self.env['pos.order.line']._order_line_fields)
        return {
            'name':         ui_order['name'],
            'user_id':      ui_order['user_id'] or False,
            'session_id':   ui_order['pos_session_id'],
            'lines':        [process_line(l) for l in ui_order['lines']] if ui_order['lines'] else False,
            'pos_reference': ui_order['name'],
            'partner_id':   ui_order['partner_id'] or False,
            'date_order':   ui_order['creation_date']
        }

    def _payment_fields(self, ui_paymentline):
        return {
            'amount':       ui_paymentline['amount'] or 0.0,
            'payment_date': ui_paymentline['name'],
            'statement_id': ui_paymentline['statement_id'],
            'payment_name': ui_paymentline.get('note', False),
            'journal':      ui_paymentline['journal_id'],
        }

    def _get_rescue_session(self, order):
        """ Find or generate a rescue session """
        PosSession = self.env['pos.session']
        date = order.get('creation_date', time.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT))
        closed_session = PosSession.browse(order['pos_session_id'])
        rescue_session = PosSession.search([
            ('rescue', '=', True), (
                'config_id', '=', closed_session.config_id.id),
            ('start_at', '<=', date), ('state', '=', 'opened')
        ], limit=1).id
        if not rescue_session:
            return closed_session.copy(default={'rescue': True})
        return rescue_session

    @api.model
    def _process_order(self, order):
        pos_session = self.env['pos.session'].browse(order['pos_session_id'])
        if pos_session.state == 'closed':
            rescue_session = self._get_rescue_session(order)
            order['pos_session_id'] = rescue_session.id
            pos_session = rescue_session
        order = self.create(self._order_fields(order))
        journal_ids = set()
        for payments in order['statement_ids']:
            order.add_payment(self._payment_fields(payments[2]))
            journal_ids.add(payments[2]['journal_id'])

        if pos_session.sequence_number <= order['sequence_number']:
            pos_session.write({'sequence_number': order['sequence_number'] + 1})
            pos_session.refresh()

        if not float_is_zero(order['amount_return'], self.env['decimal.precision'].precision_get('Account')):
            cash_journal_id = pos_session.cash_journal_id.id
            if not cash_journal_id:
                # Select for change one of the cash journals used in this
                # payment
                cash_journal = self.env['account.journal'].search([
                    ('type', '=', 'cash'),
                    ('id', 'in', list(journal_ids)),
                ], limit=1)
                if not cash_journal:
                    # If none, select for change one of the cash journals of the POS
                    # This is used for example when a customer pays by credit card
                    # an amount higher than total amount of the order and gets cash back
                    cash_journal = [statement.journal_id for statement in pos_session.statement_ids if statement.journal_id.type == 'cash']
                    if not cash_journal:
                        raise UserError(_("No cash statement found for this session. Unable to record returned cash."))
                cash_journal_id = cash_journal[0].id
            order.add_payment({
                'amount': -order['amount_return'],
                'payment_date': time.strftime('%Y-%m-%d %H:%M:%S'),
                'payment_name': _('return'),
                'journal': cash_journal_id,
            })
        return order

    def _prepare_analytic_account(self, line):
        '''This method is designed to be inherited in a custom module'''
        return False

    def _create_account_move(self, dt, ref, journal_id, company_id):
        start_at_datetime = datetime.strptime(dt, tools.DEFAULT_SERVER_DATETIME_FORMAT)
        date_tz_user = fields.Datetime.context_timestamp(self, start_at_datetime)
        date_tz_user = date_tz_user.strftime(tools.DEFAULT_SERVER_DATE_FORMAT)
        return self.env['account.move'].sudo().create({'ref': ref, 'journal_id': journal_id, 'date': date_tz_user})

    def _create_account_move_line(self, session=None, move=None):
        # Tricky, via the workflow, we only have one id in the ids variable
        """Create a account move line of order grouped by products or not."""
        IrProperty = self.env['ir.property']
        ResPartner = self.env['res.partner']

        if session and not all(session.id == order.session_id.id for order in self):
            raise UserError(_('Selected orders do not have the same session!'))

        grouped_data = {}
        have_to_group_by = session and session.config_id.group_by or False

        for order in self:
            if order.account_move:
                continue
            if order.state != 'paid':
                continue
            current_company = order.sale_journal.company_id
            account_def = IrProperty.get(
                'property_account_receivable_id', 'res.partner')
            order_account = order.partner_id and \
                order.partner_id.property_account_receivable_id and \
                order.partner_id.property_account_receivable_id.id or \
                account_def and account_def.id
            if move is None:
                # Create an entry for the sale
                move = self._create_account_move(
                    order.session_id.start_at, order.name, order.sale_journal.id, order.company_id.id)

            def insert_data(data_type, values):
                # if have_to_group_by:
                sale_journal_id = order.sale_journal.id
                values.update({
                    'ref': order.name,
                    'partner_id': order.partner_id and ResPartner._find_accounting_partner(order.partner_id).id or False,
                    'journal_id': sale_journal_id,
                    'date': fields.Date.context_today(self),
                    'move_id': move.id,
                    'company_id': current_company.id,
                })

                if data_type == 'product':
                    key = ('product', values['partner_id'], (values['product_id'], values['name']), values[
                           'analytic_account_id'], values['debit'] > 0)
                elif data_type == 'tax':
                    key = ('tax', values['partner_id'], values[
                           'tax_line_id'], values['debit'] > 0)
                elif data_type == 'counter_part':
                    key = ('counter_part', values['partner_id'], values[
                           'account_id'], values['debit'] > 0)
                else:
                    return

                grouped_data.setdefault(key, [])

                if have_to_group_by:
                    if not grouped_data[key]:
                        grouped_data[key].append(values)
                    else:
                        for line in grouped_data[key]:
                            if line.get('tax_code_id') == values.get('tax_code_id'):
                                current_value = line
                                current_value['quantity'] = current_value.get(
                                    'quantity', 0.0) + values.get('quantity', 0.0)
                                current_value['credit'] = current_value.get(
                                    'credit', 0.0) + values.get('credit', 0.0)
                                current_value['debit'] = current_value.get(
                                    'debit', 0.0) + values.get('debit', 0.0)
                                break
                        else:
                            grouped_data[key].append(values)
                else:
                    grouped_data[key].append(values)

            # because of the weird way the pos order is written, we need to make sure there is at least one line,
            # because just after the 'for' loop there are references to 'line' and 'income_account' variables (that
            # are set inside the for loop)
            # TOFIX: a deep refactoring of this method (and class!) is needed
            # in order to get rid of this stupid hack
            assert order.lines, _(
                'The POS order must have lines when calling this method')
            # Create an move for each order line

            cur = order.pricelist_id.currency_id
            for line in order.lines:
                amount = line.price_subtotal

                # Search for the income account
                if line.product_id.property_account_income_id.id:
                    income_account = line.product_id.property_account_income_id.id
                elif line.product_id.categ_id.property_account_income_categ_id.id:
                    income_account = line.product_id.categ_id.property_account_income_categ_id.id
                else:
                    raise UserError(_('Please define income '
                                      'account for this product: "%s" (id:%d).')
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
                    'analytic_account_id': self._prepare_analytic_account(line),
                    'credit': ((amount > 0) and amount) or 0.0,
                    'debit': ((amount < 0) and -amount) or 0.0,
                    'partner_id': order.partner_id and ResPartner._find_accounting_partner(order.partner_id).id or False
                })

                # Create the tax lines
                taxes = []
                for tax in line.product_id.taxes_id.filtered(lambda t: t.company_id.id == current_company.id):
                    taxes.append(tax.id)
                if not taxes:
                    continue
                for tax in self.env['account.tax'].browse(taxes).compute_all(line.price_unit * (100.0 - line.discount) / 100.0, cur, line.qty)['taxes']:
                    insert_data('tax', {
                        'name': _('Tax') + ' ' + tax['name'],
                        'product_id': line.product_id.id,
                        'quantity': line.qty,
                        'account_id': tax['account_id'] or income_account,
                        'credit': ((tax['amount'] > 0) and tax['amount']) or 0.0,
                        'debit': ((tax['amount'] < 0) and -tax['amount']) or 0.0,
                        'tax_line_id': tax['id'],
                        'partner_id': order.partner_id and ResPartner._find_accounting_partner(order.partner_id).id or False
                    })

            # counterpart
            insert_data('counter_part', {
                'name': _("Trade Receivables"),  # order.name,
                'account_id': order_account,
                'credit': ((order.amount_total < 0) and -order.amount_total) or 0.0,
                'debit': ((order.amount_total > 0) and order.amount_total) or 0.0,
                'partner_id': order.partner_id and ResPartner._find_accounting_partner(order.partner_id).id or False
            })

            order.write({'state': 'done', 'account_move': move.id})

        all_lines = []
        for group_key, group_data in grouped_data.iteritems():
            for value in group_data:
                all_lines.append((0, 0, value),)
        if move:  # In case no order was changed
            move.sudo().write({'line_ids': all_lines})
            move.sudo().post()

        return True

    def _default_session(self):
        return self.env['pos.session'].search([('state', '=', 'opened'), ('user_id', '=', self.env.uid)])

    def _default_pricelist(self):
        session = self._default_session()
        if session:
            return session.config_id.pricelist_id and session.config_id.pricelist_id.id or False

    name = fields.Char(string='Order Ref', required=True, readonly=True, copy=False, default='/')
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, default=lambda self: self.env.user.company_id)
    date_order = fields.Datetime(string='Order Date', readonly=True, index=True, default=lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'))
    user_id = fields.Many2one('res.users', string='Salesman', help="Person who uses the cash register. It can be a reliever, a student or an interim employee.", default=lambda self: self.env.uid)
    amount_tax = fields.Float(compute='_amount_all', string='Taxes', digits=0)
    amount_total = fields.Float(compute='_amount_all', string='Total', digits=0)
    amount_paid = fields.Float(compute='_amount_all', string='Paid', states={'draft': [('readonly', False)]}, readonly=True, digits=0)
    amount_return = fields.Float(compute='_amount_all', string='Returned', digits=0)
    lines = fields.One2many('pos.order.line', 'order_id', string='Order Lines', states={'draft': [('readonly', False)]}, readonly=True, copy=True)
    statement_ids = fields.One2many('account.bank.statement.line', 'pos_statement_id', string='Payments', states={'draft': [('readonly', False)]}, readonly=True)
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist', required=True, states={
                                   'draft': [('readonly', False)]}, readonly=True, default=_default_pricelist)
    partner_id = fields.Many2one('res.partner', string='Customer', change_default=True, index=True, states={'draft': [('readonly', False)], 'paid': [('readonly', False)]})
    sequence_number = fields.Integer(string='Sequence Number', help='A session-unique sequence number for the order', default=1)

    session_id = fields.Many2one(
        'pos.session', string='Session', required=True, index=True,
        domain="[('state', '=', 'opened')]", states={'draft': [('readonly', False)]},
        readonly=True, default=_default_session)
    config_id = fields.Many2one('pos.config', related='session_id.config_id', string="Point of Sale")
    state = fields.Selection(
        [('draft', 'New'), ('cancel', 'Cancelled'), ('paid', 'Paid'), ('done', 'Posted'), ('invoiced', 'Invoiced')],
        'Status', readonly=True, copy=False, default='draft')

    invoice_id = fields.Many2one('account.invoice', string='Invoice', copy=False)
    account_move = fields.Many2one('account.move', string='Journal Entry', readonly=True, copy=False)
    picking_id = fields.Many2one('stock.picking', string='Picking', readonly=True, copy=False)
    picking_type_id = fields.Many2one('stock.picking.type', related='session_id.config_id.picking_type_id', string="Picking Type")
    location_id = fields.Many2one('stock.location', related='session_id.config_id.stock_location_id', string="Location", store=True)
    note = fields.Text(string='Internal Notes')
    nb_print = fields.Integer(string='Number of Print', readonly=True, copy=False, default=0)
    pos_reference = fields.Char(string='Receipt Ref', readonly=True, copy=False)
    sale_journal = fields.Many2one('account.journal', related='session_id.config_id.journal_id', string='Sale Journal', store=True, readonly=True)

    @api.depends('amount_tax', 'amount_paid', 'amount_return', 'amount_total', 'statement_ids', 'lines.price_subtotal')
    def _amount_all(self):
        for order in self:
            order.amount_paid = 0.0
            order.amount_return = 0.0
            order.amount_tax = 0.0
            val1 = val2 = 0.0
            currency = order.pricelist_id.currency_id
            for payment in order.statement_ids:
                order.amount_paid += payment.amount
                order.amount_return += (payment.amount < 0 and payment.amount or 0)
            for line in order.lines:
                val1 += self._amount_line_tax(line)
                val2 += line.price_subtotal
            order.amount_tax = currency.round(val1)
            amount_untaxed = currency.round(val2)
            order.amount_total = order.amount_tax + amount_untaxed

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id:
            self.pricelist = self.partner_id.property_product_pricelist.id

    @api.multi
    def write(self, vals):
        res = super(PosOrder, self).write(vals)
        # If you change the partner of the PoS order, change also the partner of the associated bank statement lines
        if 'partner_id' in vals:
            for pos_order in self:
                if pos_order.invoice_id:
                    raise UserError(_("You cannot change the partner of a POS order for which an invoice has already been issued."))
                if vals['partner_id']:
                    partner = self.env['res.partner'].browse(vals['partner_id'])
                    partner_id = self.env['res.partner']._find_accounting_partner(partner).id
                else:
                    partner_id = False
                pos_order.statement_ids.write({'partner_id': partner_id})
        return res

    @api.multi
    def unlink(self):
        for pos_order in self.filtered(lambda pos_order: pos_order.state not in ['draft', 'cancel']):
            raise UserError(_('In order to delete a sale, it must be new or cancelled.'))
        return super(PosOrder, self).unlink()

    @api.model
    def create(self, values):
        if values.get('session_id'):
            # set name based on the sequence specified on the config
            session = self.env['pos.session'].browse(values['session_id'])
            values['name'] = session.config_id.sequence_id._next()
            values.setdefault('session_id', session.config_id.pricelist_id.id)
        else:
            # fallback on any pos.order sequence
            values['name'] = self.env['ir.sequence'].next_by_code('pos.order')
        return super(PosOrder, self).create(values)

    @api.multi
    def action_invoice_state(self):
        return self.write({'state': 'invoiced'})

    @api.multi
    def action_invoice(self):
        Invoice = self.env['account.invoice']
        InvoiceLine = self.env['account.invoice.line']

        for order in self:
            # Force company for all SUPERUSER_ID action
            company_id = order.company_id.id
            local_context = dict(self.env.context, force_company=company_id, company_id=company_id)
            if order.invoice_id:
                Invoice += order.invoice_id
                continue

            if not order.partner_id:
                raise UserError(_('Please provide a partner for the sale.'))

            account_id = order.partner_id.property_account_receivable_id.id
            inv = {
                'name': order.name,
                'origin': order.name,
                'account_id': account_id,
                'journal_id': order.sale_journal.id or None,
                'type': 'out_invoice',
                'reference': order.name,
                'partner_id': order.partner_id.id,
                'comment': order.note or '',
                # considering partner's sale pricelist's currency
                'currency_id': order.pricelist_id.currency_id.id,
            }
            invoice = Invoice.new(inv)
            invoice._onchange_partner_id()

            inv = invoice._convert_to_write(invoice._cache)
            if not inv.get('account_id', None):
                inv['account_id'] = account_id
            new_invoice = Invoice.with_context(local_context).sudo().create(inv)

            order.write({'invoice_id': new_invoice.id, 'state': 'invoiced'})
            Invoice += new_invoice
            for line in order.lines:
                inv_name = line.product_id.with_context(
                    local_context).name_get()[0][1]
                inv_line = {
                    'invoice_id': new_invoice.id,
                    'product_id': line.product_id.id,
                    'quantity': line.qty,
                    'account_analytic_id': self.with_context(local_context)._prepare_analytic_account(line),
                    'name': inv_name,
                }

                # Oldlin trick

                invoice_line = InvoiceLine.with_context(
                    local_context).sudo().new(inv_line)
                invoice_line._onchange_product_id()
                invoice_line.invoice_line_tax_ids = [tax.id for tax in invoice_line.invoice_line_tax_ids if tax.company_id.id == company_id]
                # We convert a new id object back to a dictionary to write to
                # bridge between old and new api
                inv_line = invoice_line._convert_to_write(invoice_line._cache)
                inv_line.update(price_unit=line.price_unit, discount=line.discount)
                InvoiceLine.with_context(local_context).sudo().create(inv_line)
            new_invoice.with_context(local_context).sudo().compute_taxes()
            order.sudo().signal_workflow('invoice')
            new_invoice.sudo().signal_workflow('validate')

        if not Invoice:
            return {}

        return {
            'name': _('Customer Invoice'),
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref('account.invoice_form').id,
            'res_model': 'account.invoice',
            'context': "{'type':'out_invoice'}",
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
            'res_id': Invoice and Invoice.ids[0] or False,
        }

    @api.multi
    def action_paid(self):
        self.write({'state': 'paid'})
        self.create_picking()
        return True

    @api.multi
    def action_cancel(self):
        self.write({'state': 'cancel'})
        return True

    @api.multi
    def action_done(self):
        self.create_account_move()
        return True

    @api.model
    def create_from_ui(self, orders):
        # Keep only new orders
        submitted_references = [o['data']['name'] for o in orders]
        pos_order = self.search([('pos_reference', 'in', submitted_references)])
        existing_orders = pos_order.read(['pos_reference'])
        existing_references = set([o['pos_reference'] for o in existing_orders])
        orders_to_save = [o for o in orders if o['data']['name'] not in existing_references]
        order_ids = []

        for tmp_order in orders_to_save:
            to_invoice = tmp_order['to_invoice']
            order = tmp_order['data']
            pos_order = self._process_order(order)
            order_ids.append(pos_order.id)

            try:
                pos_order.signal_workflow('paid')
            except Exception as e:
                _logger.error('Could not fully process the POS Order: %s', tools.ustr(e))

            if to_invoice:
                pos_order.action_invoice()
                pos_order.invoice_id.sudo().signal_workflow('invoice_open')
        return order_ids

    def test_paid(self):
        """A Point of Sale is paid when the sum
        @return: True
        """
        for order in self:
            if order.lines and not order.amount_total:
                return True
            if (not order.lines) or (not order.statement_ids) or (abs(order.amount_total - order.amount_paid) > 0.00001):
                return False
        return True

    def create_picking(self):
        """Create a picking for each order and validate it."""
        Picking = self.env['stock.picking']
        Partner = self.env['res.partner']
        Move = self.env['stock.move']

        for order in self:
            addr = order.partner_id and order.partner_id.address_get(['delivery']) or {}
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
                destination_id = Partner.default_get(['property_stock_customer'])['property_stock_customer']
            if picking_type:
                picking_id = Picking.create({
                    'origin': order.name,
                    'partner_id': addr.get('delivery', False),
                    'date_done': order.date_order,
                    'picking_type_id': picking_type.id,
                    'company_id': order.company_id.id,
                    'move_type': 'direct',
                    'note': order.note or "",
                    'location_id': location_id,
                    'location_dest_id': destination_id,
                })
                order.write({'picking_id': picking_id.id})

            move_list = []
            for line in order.lines:
                if line.product_id and line.product_id.type not in ['product', 'consu']:
                    continue

                move_list.append(Move.create({
                    'name': line.name,
                    'product_uom': line.product_id.uom_id.id,
                    'picking_id': picking_id.id,
                    'picking_type_id': picking_type.id,
                    'product_id': line.product_id.id,
                    'product_uom_qty': abs(line.qty),
                    'state': 'draft',
                    'location_id': location_id if line.qty >= 0 else destination_id,
                    'location_dest_id': destination_id if line.qty >= 0 else location_id,
                }).id)

            if picking_id:
                picking_id.action_confirm()
                picking_id.force_assign()
                picking_id.action_done()
            elif move_list:
                Move.action_confirm(move_list)
                Move.force_assign(move_list)
                Move.action_done(move_list)
        return True

    def add_payment(self, data):
        """Create a new payment for the order"""
        args = {
            'amount': data['amount'],
            'date': data.get('payment_date', time.strftime('%Y-%m-%d')),
            'name': self.name + ': ' + (data.get('payment_name', '') or ''),
            'partner_id': self.partner_id and self.env["res.partner"]._find_accounting_partner(self.partner_id).id or False,
        }

        journal_id = data.get('journal', False)
        statement_id = data.get('statement_id', False)
        assert journal_id or statement_id, "No statement_id or journal_id passed to the method!"

        journal = self.env['account.journal'].browse(journal_id)
        # use the company of the journal and not of the current user
        company_cxt = dict(self.env.context, force_company=journal.company_id.id)
        account_def = self.env['ir.property'].with_context(company_cxt).get('property_account_receivable_id', 'res.partner')
        args['account_id'] = (self.partner_id and self.partner_id.property_account_receivable_id and self.partner_id.property_account_receivable_id.id) or (
            account_def and account_def.id) or False

        if not args['account_id']:
            if not args['partner_id']:
                msg = _('There is no receivable account defined to make payment.')
            else:
                msg = _('There is no receivable account defined to make payment for the partner: "%s" (id:%d).') % (
                    self.partner_id.name, self.partner_id.id,)
            raise UserError(msg)

        context = dict(self.env.context)
        context.pop('pos_session_id', False)
        for statement in self.session_id.statement_ids:
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
            'pos_statement_id': self.id,
            'journal_id': journal_id,
            'ref': self.session_id.name,
        })
        self.env['account.bank.statement.line'].with_context(context).create(args)
        return statement_id

    @api.multi
    def refund(self):
        """Create a copy of order  for refund order"""
        clones = self.env['pos.order']

        for order in self:
            current_session = self.env['pos.session'].search([('state', '!=', 'closed'), ('user_id', '=', self.env.uid)], limit=1)
            if not current_session:
                raise UserError(_('To return product(s), you need to open a session that will be used to register the refund.'))

            clone = order.copy({
                # ot used, name forced by create
                'name': order.name + _(' REFUND'),
                'session_id': current_session.id,
                'date_order': time.strftime('%Y-%m-%d %H:%M:%S'),
            })
            clones += clone

        for clone in clones:
            for order_line in clone.lines:
                order_line.write({'qty': -order_line.qty})
        return {
            'name': _('Return Products'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'pos.order',
            'res_id': clones.ids[0],
            'view_id': False,
            'context': self.env.context,
            'type': 'ir.actions.act_window',
            'target': 'current',
        }

    @api.multi
    def create_account_move(self):
        return self._create_account_move_line()


class PosOrderLine(models.Model):
    _name = "pos.order.line"
    _description = "Lines of Point of Sale"
    _rec_name = "product_id"

    def _order_line_fields(self, line):
        if line and 'tax_ids' not in line[2]:
            product = self.env['product.product'].browse(line[2]['product_id'])
            line[2]['tax_ids'] = [(6, 0, [x.id for x in product.taxes_id])]
        return line

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    name = fields.Char(string='Line No', required=True, copy=False, default=lambda self: self.env['ir.sequence'].next_by_code('pos.order.line'))
    notice = fields.Char(string='Discount Notice')
    product_id = fields.Many2one('product.product', string='Product', domain=[('sale_ok', '=', True)], required=True, change_default=True)
    price_unit = fields.Float(string='Unit Price', digits=0)
    qty = fields.Float(string='Quantity', digits=0, default=1.0)
    price_subtotal = fields.Float(compute='_amount_line_all', digits=0, string='Subtotal w/o Tax', store=True)
    price_subtotal_incl = fields.Float(compute='_amount_line_all', digits=0, string='Subtotal', store=True)
    discount = fields.Float(string='Discount (%)', digits=0, default=0.0)
    order_id = fields.Many2one('pos.order', string='Order Ref', ondelete='cascade')
    create_date = fields.Datetime(string='Creation Date', readonly=True)
    tax_ids = fields.Many2many('account.tax', string='Taxes', readonly=True)

    @api.depends('price_subtotal', 'price_unit', 'tax_ids', 'qty', 'discount', 'product_id')
    def _amount_line_all(self):
        AccountTax = self.env['account.tax']
        for line in self:
            currency = line.order_id.pricelist_id.currency_id
            taxes_ids = [tax.id for tax in line.product_id.taxes_id if tax.company_id.id == line.order_id.company_id.id]
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            line.price_subtotal = line.price_subtotal_incl = price * line.qty
            if taxes_ids:
                taxes = AccountTax.browse(taxes_ids).compute_all(
                    price, currency, line.qty, product=line.product_id, partner=line.order_id.partner_id or False)
                line.price_subtotal = taxes['total_excluded']
                line.price_subtotal_incl = taxes['total_included']

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            if not self.order_id.pricelist_id:
                raise UserError(
                    _('You have to select a pricelist in the sale form !\n'
                      'Please set one before choosing a product.'))
            price = self.order_id.pricelist_id.price_get(
                self.product_id.id, self.qty or 1.0, self.order_id.partner_id.id)[self.order_id.pricelist_id.id]
            self.onchange_qty()
            self.price_unit = price

    @api.onchange('qty', 'discount', 'price_unit', 'tax_ids')
    def onchange_qty(self):
        if self.product_id:
            if not self.order_id.pricelist_id:
                raise UserError(_('You have to select a pricelist in the sale form !'))

            price = self.price_unit * (1 - (self.discount or 0.0) / 100.0)
            self.price_subtotal = self.price_subtotal_incl = price * self.qty
            if (self.product_id.taxes_id):
                taxes = self.product_id.taxes_id.compute_all(
                    price, self.order_id.pricelist_id.currency_id, self.qty, product=self.product_id, partner=False)
                self.price_subtotal = taxes['total_excluded']
                self.price_subtotal_incl = taxes['total_included']
