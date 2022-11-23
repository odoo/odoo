# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from datetime import timedelta
from functools import partial
from itertools import groupby
from collections import defaultdict

import psycopg2
import pytz
import re

from odoo import api, fields, models, tools, _, Command
from odoo.tools import float_is_zero, float_round, float_repr, float_compare, frozendict
from odoo.exceptions import ValidationError, UserError
from odoo.osv.expression import AND
import base64

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _name = "pos.order"
    _inherit = ["portal.mixin"]
    _description = "Point of Sale Orders"
    _order = "date_order desc, name desc, id desc"

    @api.model
    def _amount_line_tax(self, line, fiscal_position_id):
        taxes = line.tax_ids.filtered(lambda t: t.company_id.id == line.order_id.company_id.id)
        taxes = fiscal_position_id.map_tax(taxes)
        price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
        taxes = taxes.compute_all(price, line.order_id.pricelist_id.currency_id, line.qty, product=line.product_id, partner=line.order_id.partner_id or False)['taxes']
        return sum(tax.get('amount', 0.0) for tax in taxes)

    @api.model
    def _order_fields(self, ui_order):
        process_line = partial(self.env['pos.order.line']._order_line_fields, session_id=ui_order['pos_session_id'])
        return {
            'user_id':      ui_order['user_id'] or False,
            'session_id':   ui_order['pos_session_id'],
            'lines':        [process_line(l) for l in ui_order['lines']] if ui_order['lines'] else False,
            'pos_reference': ui_order['name'],
            'sequence_number': ui_order['sequence_number'],
            'partner_id':   ui_order['partner_id'] or False,
            'date_order':   ui_order['creation_date'].replace('T', ' ')[:19],
            'fiscal_position_id': ui_order['fiscal_position_id'],
            'pricelist_id': ui_order['pricelist_id'],
            'amount_paid':  ui_order['amount_paid'],
            'amount_total':  ui_order['amount_total'],
            'amount_tax':  ui_order['amount_tax'],
            'amount_return':  ui_order['amount_return'],
            'company_id': self.env['pos.session'].browse(ui_order['pos_session_id']).company_id.id,
            'to_invoice': ui_order['to_invoice'] if "to_invoice" in ui_order else False,
            'to_ship': ui_order['to_ship'] if "to_ship" in ui_order else False,
            'is_tipped': ui_order.get('is_tipped', False),
            'tip_amount': ui_order.get('tip_amount', 0),
            'access_token': ui_order.get('access_token', ''),
            'tax_details': ui_order.get('tax_details'),
        }

    @api.model
    def _payment_fields(self, order, ui_paymentline):
        return {
            'amount': ui_paymentline['amount'] or 0.0,
            'payment_date': ui_paymentline['name'],
            'payment_method_id': ui_paymentline['payment_method_id'],
            'card_type': ui_paymentline.get('card_type'),
            'cardholder_name': ui_paymentline.get('cardholder_name'),
            'transaction_id': ui_paymentline.get('transaction_id'),
            'payment_status': ui_paymentline.get('payment_status'),
            'ticket': ui_paymentline.get('ticket'),
            'pos_order_id': order.id,
        }

    # This deals with orders that belong to a closed session. In order
    # to recover from this situation we create a new rescue session,
    # making it obvious that something went wrong.
    # A new, separate, rescue session is preferred for every such recovery,
    # to avoid adding unrelated orders to live sessions.
    def _get_valid_session(self, order):
        PosSession = self.env['pos.session']
        closed_session = PosSession.browse(order['pos_session_id'])

        _logger.warning('session %s (ID: %s) was closed but received order %s (total: %s) belonging to it',
                        closed_session.name,
                        closed_session.id,
                        order['name'],
                        order['amount_total'])
        rescue_session = PosSession.search([
            ('state', 'not in', ('closed', 'closing_control')),
            ('rescue', '=', True),
            ('config_id', '=', closed_session.config_id.id),
        ], limit=1)
        if rescue_session:
            _logger.warning('reusing recovery session %s for saving order %s', rescue_session.name, order['name'])
            return rescue_session

        _logger.warning('attempting to create recovery session for saving order %s', order['name'])
        new_session = PosSession.create({
            'config_id': closed_session.config_id.id,
            'name': _('(RESCUE FOR %(session)s)') % {'session': closed_session.name},
            'rescue': True,  # avoid conflict with live sessions
        })
        # bypass opening_control (necessary when using cash control)
        new_session.action_pos_session_open()

        return new_session

    @api.model
    def _process_order(self, order, draft, existing_order):
        """Create or update an pos.order from a given dictionary.

        :param dict order: dictionary representing the order.
        :param bool draft: Indicate that the pos_order is not validated yet.
        :param existing_order: order to be updated or False.
        :type existing_order: pos.order.
        :returns: id of created/updated pos.order
        :rtype: int
        """
        order = order['data']
        pos_session = self.env['pos.session'].browse(order['pos_session_id'])
        if pos_session.state == 'closing_control' or pos_session.state == 'closed':
            order['pos_session_id'] = self._get_valid_session(order).id

        if not existing_order:
            pos_order = self.create(self._order_fields(order))
        else:
            pos_order = existing_order
            pos_order.lines.unlink()
            order['user_id'] = pos_order.user_id.id
            pos_order.write(self._order_fields(order))

        pos_order = pos_order.with_company(pos_order.company_id)
        self = self.with_company(pos_order.company_id)
        self._process_payment_lines(order, pos_order, pos_session, draft)

        if not draft:
            try:
                pos_order.action_pos_order_paid()
            except psycopg2.DatabaseError:
                # do not hide transactional errors, the order(s) won't be saved!
                raise
            except Exception as e:
                _logger.error('Could not fully process the POS Order: %s', tools.ustr(e))
            pos_order._create_order_picking()
            pos_order._compute_total_cost_in_real_time()

        if pos_order.to_invoice and pos_order.state == 'paid':
            pos_order._generate_pos_order_invoice()

        return pos_order.id

    def _process_payment_lines(self, pos_order, order, pos_session, draft):
        """Create account.bank.statement.lines from the dictionary given to the parent function.

        If the payment_line is an updated version of an existing one, the existing payment_line will first be
        removed before making a new one.
        :param pos_order: dictionary representing the order.
        :type pos_order: dict.
        :param order: Order object the payment lines should belong to.
        :type order: pos.order
        :param pos_session: PoS session the order was created in.
        :type pos_session: pos.session
        :param draft: Indicate that the pos_order is not validated yet.
        :type draft: bool.
        """
        prec_acc = order.pricelist_id.currency_id.decimal_places

        order_bank_statement_lines= self.env['pos.payment'].search([('pos_order_id', '=', order.id)])
        order_bank_statement_lines.unlink()
        for payments in pos_order['statement_ids']:
            order.add_payment(self._payment_fields(order, payments[2]))

        order.amount_paid = sum(order.payment_ids.mapped('amount'))

        if not draft and not float_is_zero(pos_order['amount_return'], prec_acc):
            cash_payment_method = pos_session.payment_method_ids.filtered('is_cash_count')[:1]
            if not cash_payment_method:
                raise UserError(_("No cash payment method found for this session. Unable to record returned cash."))
            return_payment_vals = {
                'name': _('return'),
                'pos_order_id': order.id,
                'amount': -pos_order['amount_return'],
                'payment_date': fields.Datetime.now(),
                'payment_method_id': cash_payment_method.id,
                'is_change': True,
            }
            order.add_payment(return_payment_vals)

    def _get_pos_anglo_saxon_price_unit(self, product, partner_id, quantity):
        moves = self.filtered(lambda o: o.partner_id.id == partner_id)\
            .mapped('picking_ids.move_ids')\
            ._filter_anglo_saxon_moves(product)\
            .sorted(lambda x: x.date)
        price_unit = product.with_company(self.company_id)._compute_average_price(0, quantity, moves)
        return price_unit

    name = fields.Char(string='Order Ref', required=True, readonly=True, copy=False, default='/')
    date_order = fields.Datetime(string='Date', readonly=True, index=True, default=fields.Datetime.now)
    user_id = fields.Many2one(
        comodel_name='res.users', string='Responsible',
        help="Person who uses the cash register. It can be a reliever, a student or an interim employee.",
        default=lambda self: self.env.uid,
        states={'done': [('readonly', True)], 'invoiced': [('readonly', True)]},
    )
    amount_tax = fields.Float(string='Taxes', digits=0, readonly=True, required=True)
    tax_details = fields.Json(string='Tax amount per tax id', readonly=True)
    amount_total = fields.Float(string='Total', digits=0, readonly=True, required=True)
    amount_paid = fields.Float(string='Paid', states={'draft': [('readonly', False)]},
        readonly=True, digits=0, required=True)
    amount_return = fields.Float(string='Returned', digits=0, required=True, readonly=True)
    margin = fields.Monetary(string="Margin", compute='_compute_margin')
    margin_percent = fields.Float(string="Margin (%)", compute='_compute_margin', digits=(12, 4))
    is_total_cost_computed = fields.Boolean(compute='_compute_is_total_cost_computed',
        help="Allows to know if all the total cost of the order lines have already been computed")
    lines = fields.One2many('pos.order.line', 'order_id', string='Order Lines', states={'draft': [('readonly', False)]}, readonly=True, copy=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True)
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist', required=True, states={
                                   'draft': [('readonly', False)]}, readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer', change_default=True, index='btree_not_null', states={'draft': [('readonly', False)], 'paid': [('readonly', False)]})
    sequence_number = fields.Integer(string='Sequence Number', help='A session-unique sequence number for the order', default=1)

    session_id = fields.Many2one(
        'pos.session', string='Session', required=True, index=True,
        domain="[('state', '=', 'opened')]", states={'draft': [('readonly', False)]},
        readonly=True)
    config_id = fields.Many2one('pos.config', related='session_id.config_id', string="Point of Sale", readonly=False)
    currency_id = fields.Many2one('res.currency', related='config_id.currency_id', string="Currency")
    currency_rate = fields.Float("Currency Rate", compute='_compute_currency_rate', compute_sudo=True, store=True, digits=0, readonly=True,
        help='The rate of the currency to the currency of rate applicable at the date of the order')

    state = fields.Selection(
        [('draft', 'New'), ('cancel', 'Cancelled'), ('paid', 'Paid'), ('done', 'Posted'), ('invoiced', 'Invoiced')],
        'Status', readonly=True, copy=False, default='draft')

    account_move = fields.Many2one('account.move', string='Invoice', readonly=True, copy=False, index=True)
    picking_ids = fields.One2many('stock.picking', 'pos_order_id')
    picking_count = fields.Integer(compute='_compute_picking_count')
    failed_pickings = fields.Boolean(compute='_compute_picking_count')
    picking_type_id = fields.Many2one('stock.picking.type', related='session_id.config_id.picking_type_id', string="Operation Type", readonly=False)
    procurement_group_id = fields.Many2one('procurement.group', 'Procurement Group', copy=False)

    note = fields.Text(string='Internal Notes')
    nb_print = fields.Integer(string='Number of Print', readonly=True, copy=False, default=0)
    pos_reference = fields.Char(string='Receipt Number', readonly=True, copy=False)
    sale_journal = fields.Many2one('account.journal', related='session_id.config_id.journal_id', string='Sales Journal', store=True, readonly=True, ondelete='restrict')
    fiscal_position_id = fields.Many2one(
        comodel_name='account.fiscal.position', string='Fiscal Position',
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    payment_ids = fields.One2many('pos.payment', 'pos_order_id', string='Payments', readonly=True)
    session_move_id = fields.Many2one('account.move', string='Session Journal Entry', related='session_id.move_id', readonly=True, copy=False)
    to_invoice = fields.Boolean('To invoice', copy=False)
    to_ship = fields.Boolean('To ship')
    is_invoiced = fields.Boolean('Is Invoiced', compute='_compute_is_invoiced')
    is_tipped = fields.Boolean('Is this already tipped?', readonly=True)
    tip_amount = fields.Float(string='Tip Amount', digits=0, readonly=True)
    refund_orders_count = fields.Integer('Number of Refund Orders', compute='_compute_refund_related_fields')
    is_refunded = fields.Boolean(compute='_compute_refund_related_fields')
    refunded_order_ids = fields.Many2many('pos.order', compute='_compute_refund_related_fields')
    has_refundable_lines = fields.Boolean('Has Refundable Lines', compute='_compute_has_refundable_lines')
    refunded_orders_count = fields.Integer(compute='_compute_refund_related_fields')

    @api.depends('lines.refund_orderline_ids', 'lines.refunded_orderline_id')
    def _compute_refund_related_fields(self):
        for order in self:
            order.refund_orders_count = len(order.mapped('lines.refund_orderline_ids.order_id'))
            order.is_refunded = order.refund_orders_count > 0
            order.refunded_order_ids = order.mapped('lines.refunded_orderline_id.order_id')
            order.refunded_orders_count = len(order.refunded_order_ids)

    @api.depends('lines.refunded_qty', 'lines.qty')
    def _compute_has_refundable_lines(self):
        digits = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for order in self:
            order.has_refundable_lines = any([float_compare(line.qty, line.refunded_qty, digits) > 0 for line in order.lines])

    @api.depends('account_move')
    def _compute_is_invoiced(self):
        for order in self:
            order.is_invoiced = bool(order.account_move)

    @api.depends('picking_ids', 'picking_ids.state')
    def _compute_picking_count(self):
        for order in self:
            order.picking_count = len(order.picking_ids)
            order.failed_pickings = bool(order.picking_ids.filtered(lambda p: p.state != 'done'))

    @api.depends('date_order', 'company_id', 'currency_id', 'company_id.currency_id')
    def _compute_currency_rate(self):
        for order in self:
            order.currency_rate = self.env['res.currency']._get_conversion_rate(order.company_id.currency_id, order.currency_id, order.company_id, order.date_order)

    @api.depends('lines.is_total_cost_computed')
    def _compute_is_total_cost_computed(self):
        for order in self:
            order.is_total_cost_computed = not False in order.lines.mapped('is_total_cost_computed')

    def _compute_total_cost_in_real_time(self):
        """
        Compute the total cost of the order when it's processed by the server. It will compute the total cost of all the lines
        if it's possible. If a margin of one of the order's lines cannot be computed (because of session_id.update_stock_at_closing),
        then the margin of said order is not computed (it will be computed when closing the session).
        """
        for order in self:
            lines = order.lines
            if not order._should_create_picking_real_time():
                storable_fifo_avco_lines = lines.filtered(lambda l: l._is_product_storable_fifo_avco())
                lines -= storable_fifo_avco_lines
            stock_moves = order.picking_ids.move_ids
            lines._compute_total_cost(stock_moves)

    def _compute_total_cost_at_session_closing(self, stock_moves):
        """
        Compute the margin at the end of the session. This method should be called to compute the remaining lines margin
        containing a storable product with a fifo/avco cost method and then compute the order margin
        """
        for order in self:
            storable_fifo_avco_lines = order.lines.filtered(lambda l: l._is_product_storable_fifo_avco())
            storable_fifo_avco_lines._compute_total_cost(stock_moves)

    @api.depends('lines.margin', 'is_total_cost_computed')
    def _compute_margin(self):
        for order in self:
            if order.is_total_cost_computed:
                order.margin = sum(order.lines.mapped('margin'))
                amount_untaxed = order.currency_id.round(sum(line.price_subtotal for line in order.lines))
                order.margin_percent = not float_is_zero(amount_untaxed, order.currency_id.rounding) and order.margin / amount_untaxed or 0
            else:
                order.margin = 0
                order.margin_percent = 0

    @api.onchange('payment_ids', 'lines')
    def _onchange_amount_all(self):
        for order in self:
            if not order.pricelist_id.currency_id:
                raise UserError(_("You can't: create a pos order from the backend interface, or unset the pricelist, or create a pos.order in a python test with Form tool, or edit the form view in studio if no PoS order exist"))
            currency = order.pricelist_id.currency_id
            order.amount_paid = sum(payment.amount for payment in order.payment_ids)
            order.amount_return = sum(payment.amount < 0 and payment.amount or 0 for payment in order.payment_ids)
            order.amount_tax = currency.round(sum(self._amount_line_tax(line, order.fiscal_position_id) for line in order.lines))
            amount_untaxed = currency.round(sum(line.price_subtotal for line in order.lines))
            order.amount_total = order.amount_tax + amount_untaxed

    def _compute_batch_amount_all(self):
        """
        Does essentially the same thing as `_onchange_amount_all` but only for actually existing records
        It is intended as a helper method , not as a business one
        Practical to be used for migrations
        """
        amounts = {order_id: {'paid': 0, 'return': 0, 'taxed': 0, 'taxes': 0} for order_id in self.ids}
        for order in self.env['pos.payment'].read_group([('pos_order_id', 'in', self.ids)], ['pos_order_id', 'amount'], ['pos_order_id']):
            amounts[order['pos_order_id'][0]]['paid'] = order['amount']
        for order in self.env['pos.payment'].read_group(['&', ('pos_order_id', 'in', self.ids), ('amount', '<', 0)], ['pos_order_id', 'amount'], ['pos_order_id']):
            amounts[order['pos_order_id'][0]]['return'] = order['amount']
        for order in self.env['pos.order.line'].read_group([('order_id', 'in', self.ids)], ['order_id', 'price_subtotal', 'price_subtotal_incl'], ['order_id']):
            amounts[order['order_id'][0]]['taxed'] = order['price_subtotal_incl']
            amounts[order['order_id'][0]]['taxes'] = order['price_subtotal_incl'] - order['price_subtotal']

        for order in self:
            currency = order.pricelist_id.currency_id
            order.write({
                'amount_paid': amounts[order.id]['paid'],
                'amount_return': amounts[order.id]['return'],
                'amount_tax': currency.round(amounts[order.id]['taxes']),
                'amount_total': currency.round(amounts[order.id]['taxed'])
            })

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.pricelist_id = self.partner_id.property_product_pricelist.id

    @api.ondelete(at_uninstall=False)
    def _unlink_except_draft_or_cancel(self):
        for pos_order in self.filtered(lambda pos_order: pos_order.state not in ['draft', 'cancel']):
            raise UserError(_('In order to delete a sale, it must be new or cancelled.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            session = self.env['pos.session'].browse(vals['session_id'])
            vals = self._complete_values_from_session(session, vals)
        return super().create(vals_list)

    @api.model
    def _complete_values_from_session(self, session, values):
        if values.get('state') and values['state'] == 'paid':
            values['name'] = self._compute_order_name()
        values.setdefault('pricelist_id', session.config_id.pricelist_id.id)
        values.setdefault('fiscal_position_id', session.config_id.default_fiscal_position_id.id)
        values.setdefault('company_id', session.config_id.company_id.id)
        return values

    def write(self, vals):
        for order in self:
            if vals.get('state') and vals['state'] == 'paid' and order.name == '/':
                vals['name'] = self._compute_order_name()
        return super(PosOrder, self).write(vals)

    def _compute_order_name(self):
        if len(self.refunded_order_ids) != 0:
            return ','.join(self.refunded_order_ids.mapped('name')) + _(' REFUND')
        else:
            return self.session_id.config_id.sequence_id._next()

    def action_stock_picking(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('stock.action_picking_tree_ready')
        action['context'] = {}
        action['domain'] = [('id', 'in', self.picking_ids.ids)]
        return action

    def action_view_invoice(self):
        return {
            'name': _('Customer Invoice'),
            'view_mode': 'form',
            'view_id': self.env.ref('account.view_move_form').id,
            'res_model': 'account.move',
            'context': "{'move_type':'out_invoice'}",
            'type': 'ir.actions.act_window',
            'res_id': self.account_move.id,
        }

    def action_view_refund_orders(self):
        return {
            'name': _('Refund Orders'),
            'view_mode': 'tree,form',
            'res_model': 'pos.order',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.mapped('lines.refund_orderline_ids.order_id').ids)],
        }

    def action_view_refunded_orders(self):
        return {
            'name': _('Refunded Orders'),
            'view_mode': 'tree,form',
            'res_model': 'pos.order',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.refunded_order_ids.ids)],
        }

    def _is_pos_order_paid(self):
        return float_is_zero(self._get_rounded_amount(self.amount_total) - self.amount_paid, precision_rounding=self.currency_id.rounding)

    def _get_rounded_amount(self, amount):
        if self.config_id.cash_rounding:
            amount = float_round(amount, precision_rounding=self.config_id.rounding_method.rounding, rounding_method=self.config_id.rounding_method.rounding_method)
        currency = self.currency_id
        return currency.round(amount) if currency else amount

    def _create_invoice(self):
        self.ensure_one()
        invoice = self.env['account.move'].sudo().create(self._prepare_invoice_vals())
        message = _(
            "This invoice has been created from the point of sale session: %s",
            self._get_html_link(),
        )
        invoice.message_post(body=message)

        # Avoid a different tax computation between js/python.
        amls_values_list_per_nature = self._prepare_aml_values_list_per_nature()
        line_ids_commands = []
        for tax_aml_vals in amls_values_list_per_nature['tax']:
            tax_aml = invoice.line_ids.filtered(lambda x: x.tax_repartition_line_id.id == tax_aml_vals['tax_repartition_line_id'])
            if len(tax_aml) > 1:
                continue
            if not self.currency_id.is_zero(tax_aml.amount_currency - tax_aml_vals['amount_currency']):
                line_ids_commands.append((1, tax_aml.id, {
                    'amount_currency': tax_aml_vals['amount_currency'],
                    'balance': tax_aml_vals['balance'],
                }))
        if line_ids_commands:
            invoice.line_ids = line_ids_commands

        return invoice

    def action_pos_order_paid(self):
        self.ensure_one()

        # TODO: add support for mix of cash and non-cash payments when both cash_rounding and only_round_cash_method are True
        if not self.config_id.cash_rounding \
           or self.config_id.only_round_cash_method \
           and not any(p.payment_method_id.is_cash_count for p in self.payment_ids):
            total = self.amount_total
        else:
            total = float_round(self.amount_total, precision_rounding=self.config_id.rounding_method.rounding, rounding_method=self.config_id.rounding_method.rounding_method)

        isPaid = float_is_zero(total - self.amount_paid, precision_rounding=self.currency_id.rounding)

        if not isPaid and not self.config_id.cash_rounding:
            raise UserError(_("Order %s is not fully paid.", self.name))
        elif not isPaid and self.config_id.cash_rounding:
            currency = self.currency_id
            if self.config_id.rounding_method.rounding_method == "HALF-UP":
                maxDiff = currency.round(self.config_id.rounding_method.rounding / 2)
            else:
                maxDiff = currency.round(self.config_id.rounding_method.rounding)

            diff = currency.round(self.amount_total - self.amount_paid)
            if not abs(diff) <= maxDiff:
                raise UserError(_("Order %s is not fully paid.", self.name))

        self.write({'state': 'paid'})

        return True

    def _prepare_invoice_vals(self):
        self.ensure_one()

        vals = {
            'invoice_origin': self.name,
            'journal_id': self.session_id.config_id.invoice_journal_id.id,
            'move_type': 'out_invoice' if self.amount_total >= 0 else 'out_refund',
            'ref': self.name,
            'partner_id': self.partner_id.id,
            # considering partner's sale pricelist's currency
            'currency_id': self.pricelist_id.currency_id.id,
            'invoice_user_id': self.user_id.id,
            'invoice_date': self.date_order,
            'fiscal_position_id': self.fiscal_position_id.id,
            'invoice_payment_term_id': self.partner_id.property_payment_term_id.id or False,
            'invoice_line_ids': [],
        }

        if self.note:
            vals['narration'] = self.note

        amls_values_list_per_nature = self._prepare_aml_values_list_per_nature()
        sequence = 11
        for order_line, aml_vals in zip(self.lines, amls_values_list_per_nature['product']):
            vals['invoice_line_ids'].append(Command.create({
                **aml_vals,
                'product_id': order_line.product_id.id,
                'quantity': order_line.qty if self.amount_total >= 0 else -order_line.qty,
                'discount': order_line.discount,
                'price_unit': order_line.price_unit,
                'product_uom_id': order_line.product_uom_id.id,
                'display_type': 'product',
                'sequence': sequence,
            }))
            sequence += 1

            has_without_discount_pricelist = order_line.order_id.pricelist_id.discount_policy == 'without_discount'
            if has_without_discount_pricelist and order_line.price_unit != order_line.product_id.lst_price:
                vals['invoice_line_ids'].append(Command.create({
                    'name': _(
                        "Price discount from %s -> %s",
                        float_repr(order_line.product_id.lst_price, self.currency_id.decimal_places),
                        float_repr(order_line.price_unit, self.currency_id.decimal_places),
                    ),
                    'display_type': 'line_note',
                    'sequence': sequence,
                }))
                sequence += 1

            if order_line.customer_note:
                vals['invoice_line_ids'].append(Command.create({
                    'name': order_line.customer_note,
                    'display_type': 'line_note',
                    'sequence': sequence,
                }))
                sequence += 1

        for aml_vals in amls_values_list_per_nature['cash_rounding']:
            vals['invoice_line_ids'].append(Command.create({
                **aml_vals,
                'quantity': 1,
                'price_unit': -aml_vals['amount_currency'],
                'display_type': 'product',
                'sequence': sequence,
            }))
            sequence += 1

        return vals

    def _prepare_tax_results(self):
        """ Compute the tax amounts for the current pos order in order to create later the corresponding journal items.

        :return: See '_compute_taxes' on account.tax.
        """
        self.ensure_one()
        commercial_partner = self.partner_id.commercial_partner_id

        base_line_vals_list = []
        for line in self.lines.with_company(self.company_id):
            account = line.product_id._get_product_accounts()['income']
            if not account:
                raise UserError(_(
                    "Please define income account for this product: '%s' (id:%d).",
                    line.product_id.name, line.product_id.id,
                ))

            if self.fiscal_position_id:
                account = self.fiscal_position_id.map_account(account)

            quantity = line.qty
            price_unit = line.price_unit
            is_refund = quantity < 0.0 or price_unit < 0.0
            price_unit_multiplicator = 1 if is_refund else -1
            quantity_multiplicator = 1 if price_unit else price_unit_multiplicator

            base_line_vals_list.append(self.env['account.tax']._convert_to_tax_base_line_dict(
                line,
                partner=commercial_partner,
                currency=self.currency_id,
                product=line.product_id,
                taxes=line.tax_ids_after_fiscal_position,
                price_unit=abs(price_unit) * price_unit_multiplicator,
                # To stay consistent with the js-code, we can't reverse the sign of quantity due to the fixed tax.
                # The inversion is made to get the right accounting sign to ease the creation of the accounting
                # journal items.
                quantity=abs(quantity) * quantity_multiplicator,
                discount=line.discount,
                account=account,
                is_refund=is_refund,
            ))

        tax_results = self.env['account.tax']._compute_taxes(base_line_vals_list)

        # Avoid a different tax computation between js/python.
        tax_details_per_tax_rep = {}
        if self.tax_details:
            for key, tax_amount in self.tax_details.items():
                key_split = key.split(',')
                is_refund = key_split[0] == 'true'
                tax_id = int(key_split[1])
                tax = self.env['account.tax'].browse(tax_id)
                precision_rounding = self.env['account.tax']\
                    ._get_tax_computation_precision_rounding(self.company_id, self.currency_id)
                rep_line_amount = tax._distribute_tax_amount(tax_amount, is_refund, self.currency_id, precision_rounding)
                for repartition_line, line_amount in rep_line_amount:
                    tax_details_per_tax_rep[repartition_line] = -line_amount

            for tax_line_vals in tax_results['tax_lines_to_add']:
                tax_rep = self.env['account.tax.repartition.line'].browse(tax_line_vals['tax_repartition_line_id'])

                if tax_details_per_tax_rep.get(tax_rep):
                    tax_line_vals['tax_amount'] = tax_details_per_tax_rep[tax_rep]

        return tax_results

    def _prepare_aml_values_list_per_nature(self):
        """ Prepare the dictionaries representing the journal items to be created for this sale orders.
        Also, those are split by nature (tax, product, payment_terms, cash_rounding...).

        :return: A dictionary having tax/product/payment_terms/cash_rounding/stock as keys and a list of dictionaries
        as values.
        """
        self.ensure_one()
        commercial_partner = self.partner_id.commercial_partner_id
        company_currency = self.company_id.currency_id
        rate = self.currency_id\
            ._get_conversion_rate(self.currency_id, company_currency, self.company_id, self.date_order)

        total_balance = 0.0
        total_amount_currency = 0.0
        aml_vals_list_per_nature = defaultdict(list)

        # Create the tax lines
        tax_results = self._prepare_tax_results()
        for tax_line_vals in tax_results['tax_lines_to_add']:
            tax_rep = self.env['account.tax.repartition.line'].browse(tax_line_vals['tax_repartition_line_id'])

            amount_currency = tax_line_vals['tax_amount']
            balance = company_currency.round(amount_currency * rate)
            aml_vals_list_per_nature['tax'].append({
                'name': tax_rep.tax_id.name,
                'account_id': tax_line_vals['account_id'],
                'partner_id': tax_line_vals['partner_id'],
                'currency_id': tax_line_vals['currency_id'],
                'tax_repartition_line_id': tax_line_vals['tax_repartition_line_id'],
                'tax_ids': tax_line_vals['tax_ids'],
                'tax_tag_ids': tax_line_vals['tax_tag_ids'],
                'group_tax_id': None if tax_rep.tax_id.id == tax_line_vals['tax_id'] else tax_line_vals['tax_id'],
                'amount_currency': amount_currency,
                'balance': balance,
                'tax_base_amount': abs(tax_line_vals['base_amount']),
            })
            total_amount_currency += amount_currency
            total_balance += balance

        # Create the aml values for order lines.
        for base_line_vals, update_base_line_vals in tax_results['base_lines_to_update']:
            order_line = base_line_vals['record']
            amount_currency = update_base_line_vals['price_subtotal']
            balance = company_currency.round(amount_currency * rate)
            aml_vals_list_per_nature['product'].append({
                'name': order_line.full_product_name or order_line.product_id.display_name,
                'account_id': base_line_vals['account'].id,
                'partner_id': base_line_vals['partner'].id,
                'currency_id': base_line_vals['currency'].id,
                'tax_ids': [(6, 0, base_line_vals['taxes'].ids)],
                'tax_tag_ids': update_base_line_vals['tax_tag_ids'],
                'amount_currency': amount_currency,
                'balance': balance,
            })
            total_amount_currency += amount_currency
            total_balance += balance

        # Cash Rounding difference.
        cash_rounding = self.config_id.rounding_method
        if cash_rounding:
            amount_currency = -self.currency_id.round(self.amount_paid - self.amount_total)
            if not self.currency_id.is_zero(amount_currency):
                balance = company_currency.round(amount_currency * rate)
                if amount_currency > 0.0 and cash_rounding.loss_account_id:
                    account = cash_rounding.loss_account_id
                else:
                    account = cash_rounding.profit_account_id

                aml_vals_list_per_nature['cash_rounding'].append({
                    'name': cash_rounding.name,
                    'account_id': account.id,
                    'partner_id': commercial_partner.id,
                    'currency_id': self.currency_id.id,
                    'amount_currency': amount_currency,
                    'balance': balance,
                })
                total_amount_currency += amount_currency
                total_balance += balance

        # Stock.
        if self.company_id.anglo_saxon_accounting and self.picking_ids.ids:
            stock_moves = self.env['stock.move'].sudo().search([
                ('picking_id', 'in', self.picking_ids.ids),
                ('product_id.categ_id.property_valuation', '=', 'real_time')
            ])
            for stock_move in stock_moves:
                expense_account = stock_move.product_id._get_product_accounts()['expense']
                stock_output_account = stock_move.product_id.categ_id.property_stock_account_output_categ_id
                balance = -sum(stock_move.stock_valuation_layer_ids.mapped('value'))
                aml_vals_list_per_nature['stock'].append({
                    'name': _("Stock input for %s", stock_move.product_id.name),
                    'account_id': expense_account.id,
                    'partner_id': commercial_partner.id,
                    'currency_id': self.company_id.currency_id.id,
                    'amount_currency': balance,
                    'balance': balance,
                })
                aml_vals_list_per_nature['stock'].append({
                    'name': _("Stock output for %s", stock_move.product_id.name),
                    'account_id': stock_output_account.id,
                    'partner_id': commercial_partner.id,
                    'currency_id': self.company_id.currency_id.id,
                    'amount_currency': -balance,
                    'balance': -balance,
                })

        # Payment terms.
        pos_receivable_account = self.company_id.account_default_pos_receivable_account_id
        aml_vals_list_per_nature['payment_terms'].append({
            'name': f"{pos_receivable_account.code} {pos_receivable_account.code}",
            'account_id': pos_receivable_account.id,
            'currency_id': self.currency_id.id,
            'amount_currency': -total_amount_currency,
            'balance': -total_balance,
        })

        return aml_vals_list_per_nature

    def action_pos_order_invoice(self):
        self.write({'to_invoice': True})
        res = self._generate_pos_order_invoice()
        if self.company_id.anglo_saxon_accounting and self.session_id.update_stock_at_closing:
            self._create_order_picking()
        return res

    def _generate_pos_order_invoice(self):
        """ Invoice the current orders.

        :return Action opening the newly created invoices.
        """
        moves = self.env['account.move']

        orders_per_session = defaultdict(lambda: self.env['pos.order'])

        for order in self:

            if order.account_move:
                moves += order.account_move
                continue

            if not order.partner_id:
                raise UserError(_('Please provide a partner for the sale.'))

            invoice = order._create_invoice()

            order.write({'account_move': invoice.id, 'state': 'invoiced'})
            invoice.sudo().action_post()
            moves += invoice

            orders_per_session[order.session_id] |= order

        for orders in orders_per_session.values():
            results = orders._prepare_pos_order_accounting_items_generation()

            if results['reverse_closing_entry_vals']:

                # Migrate the cash statement lines from the closing to the newly created invoice.
                orders._process_st_lines_after_reverse(results)

                # Reverse the bank journal entries.
                orders._process_reverse_bank_journal_entries(results)

                # Reverse the closing entry.
                orders._process_reverse_closing_journal_entry(results)

            # Create the accounting payments.
            orders._process_create_account_payments(results)

            # Create the cash statement lines.
            orders._process_create_cash_statement_lines(results)

        if not moves:
            return {}

        return {
            'name': _('Customer Invoice'),
            'view_mode': 'form',
            'view_id': self.env.ref('account.view_move_form').id,
            'res_model': 'account.move',
            'context': "{'move_type':'out_invoice'}",
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
            'res_id': moves and moves.ids[0] or False,
        }

    def _process_st_lines_after_reverse(self, results):
        """ Process 'reverse_st_lines_to_reconcile' in results.
        Move the statement lines reconciled with the first closing entry to the invoices created after the closing
        of the pos session.

        :param results: The results of '_prepare_pos_order_accounting_items_generation' in 'pos.order'.
        """
        for invoice, st_line in results['reverse_st_lines_to_reconcile'].items():
            st_line.action_undo_reconciliation()
            st_line.move_id.button_draft()

            # The partner could be not set on the cash transaction since he could be unknown until he asks
            # for an invoice.
            if not st_line.partner_id:
                st_line.partner_id = invoice.partner_id

            # Reconcile the statement line with the invoice.
            receivable_account = invoice.partner_id.with_company(invoice.company_id).property_account_receivable_id
            _liquidity_line, suspense_lines, _other_lines = st_line._seek_for_lines()
            suspense_lines.write({'account_id': receivable_account.id})
            st_line.move_id.action_post()
            receivable_amls = invoice.line_ids.filtered(lambda x: x.account_id.account_type == 'asset_receivable')
            (receivable_amls + suspense_lines).reconcile()

    def _process_reverse_bank_journal_entries(self, results):
        """ Process 'reverse_closing_bank_entry_per_pay_method' in results.
        Reverse the closing journal entries made for 'bank' payment methods.

        :param results: The results of '_prepare_pos_order_accounting_items_generation' in 'pos.order'.
        """
        session = self.session_id
        session.ensure_one()

        for payment_method, res_entry in results['reverse_closing_bank_entry_per_pay_method'].items():
            if not res_entry.get('bank_entry_vals'):
                continue

            # Create the reverse bank journal entry.
            reverse_bank_move = self.env['account.move'] \
                .with_context(skip_invoice_sync=True) \
                .create(res_entry['bank_entry_vals'])
            reverse_bank_move.action_post()

            # Break the current reconciliation with the closing entry.
            existing_bank_move = res_entry['closing_bank_entry']
            reconciled_amls = existing_bank_move.line_ids.matched_debit_ids.debit_move_id \
                              + existing_bank_move.line_ids.matched_credit_ids.credit_move_id
            reconciled_amls.filtered(lambda x: x.move_id == session.move_id).remove_move_reconcile()

            # Reconcile it with the existing bank journal entry.
            (reverse_bank_move + existing_bank_move).line_ids \
                .filtered(lambda x: x.pos_payment_method_id == payment_method) \
                .reconcile()

    def _process_reverse_closing_journal_entry(self, results):
        """ Process 'reverse_closing_entry_vals' in results.
        Reverse the closing journal entry with the invoiced pos orders.

        :param results: The results of '_prepare_pos_order_accounting_items_generation' in 'pos.order'.
        """
        session = self.session_id
        session.ensure_one()

        reverse_closing_move = self.env['account.move'] \
            .with_context(skip_invoice_sync=True) \
            .create(results['reverse_closing_entry_vals'])
        reverse_closing_move.action_post()

        # Reconcile the reverse closing entry with the existing closing entry.
        for pos_payment_method in reverse_closing_move.line_ids.pos_payment_method_id:
            (session.move_id + reverse_closing_move).line_ids \
                .filtered(lambda x: x.pos_payment_method_id == pos_payment_method and not x.reconciled) \
                .reconcile()

    def _process_create_account_payments(self, results):
        """ Process 'closing_payment_vals_list' in results.
        The payments made with the 'bank' payment methods was added to a bank journal entry at the closing. Now the
        orders have been invoiced, this bank journal entry has been reversed (see _process_reverse_bank_journal_entries)
        and is replaced by accounting payments.

        :param results: The results of '_prepare_pos_order_accounting_items_generation' in 'pos.order'.
        """
        pos_payments = self.env['pos.payment']
        payment_vals_list = []
        for pos_payment, payment_vals in results['closing_payment_vals_list']:
            pos_payments |= pos_payment
            payment_vals_list.append(payment_vals)

        if payment_vals_list:
            payments = self.env['account.payment'].create(payment_vals_list)
            payments.action_post()

            for pos_payment, payment in zip(pos_payments, payments):
                # Link the pos payments to the newly created account payments.
                pos_payment.account_move_id = payment.move_id

                # Reconcile.
                (payment.move_id + pos_payment.pos_order_id.account_move).line_ids \
                    .filtered(lambda x: x.account_id.account_type == 'asset_receivable' and not x.reconciled) \
                    .reconcile()

    def _process_create_cash_statement_lines(self, results):
        """ Process 'closing_st_line_vals_list' in results.
        There are the cash statement lines to be created because an invoice has been claimed by the customer but
        the session is not closed so the closing journal entry is not yet there.

        :param results: The results of '_prepare_pos_order_accounting_items_generation' in 'pos.order'.
        """
        pos_payments = self.env['pos.payment']
        st_lines_vals_list = []
        for pos_payment, st_line_vals in results['closing_st_line_vals_list']:
            pos_payments |= pos_payment
            st_lines_vals_list.append(st_line_vals)

        if st_lines_vals_list:
            st_lines = self.env['account.bank.statement.line'] \
                .with_context(skip_invoice_sync=True) \
                .create(st_lines_vals_list)

            for pos_payment, st_line in zip(pos_payments, st_lines):
                # Link the pos payments to the newly created statement lines.
                pos_payment.statement_line_id = st_line

                # Reconcile.
                (st_line.move_id + pos_payment.pos_order_id.account_move).line_ids \
                    .filtered(lambda x: x.account_id.account_type == 'asset_receivable' and not x.reconciled) \
                    .reconcile()

            # Special case:
            # Suppose you choose to pay 100 in bank instead of the expected 30. This is a way to retrieve 70 in cash.
            # When the pos order is invoiced, the invoice is reconciled with the payment but the statement line has to
            # be reconciled with the payment too, not with the invoice.
            for pos_payment, st_line in zip(pos_payments, st_lines):
                st_line_amls = st_line.move_id.line_ids \
                    .filtered(lambda x: x.account_id.account_type == 'asset_receivable' and not x.reconciled)

                # The reconciliation is missing. Look to the bank journal entries.
                if st_line_amls:
                    pos_entry_amls = pos_payment.pos_order_id.payment_ids.account_move_id.line_ids \
                        .filtered(lambda x: x.account_id.account_type == 'asset_receivable' and not x.reconciled)
                    (st_line_amls + pos_entry_amls).reconcile()

    def _prepare_pos_order_accounting_items_generation(self):
        session = self.session_id
        session.ensure_one()

        res = {
            'closing_entry_vals': None,
            'closing_bank_entry_per_pay_method': defaultdict(lambda: {
                'pos_payments': self.env['pos.payment'],
                'amls_values_list': [],
            }),
            'closing_payment_vals_list': [],
            'closing_st_line_vals_list': [],

            'reverse_closing_entry_vals': None,
            'reverse_closing_bank_entry_per_pay_method': defaultdict(lambda: {
                'pos_payments': self.env['pos.payment'],
                'amls_values_list': [],
                'closing_bank_entry': None,
            }),
            'reverse_st_lines_to_reconcile': defaultdict(lambda: self.env['account.bank.statement.line']),
        }

        closing_amls_per_nature = {
            'product': [],
            'tax': [],
            'cash_rounding': [],
            'stock': [],
            'payment': [],
        }
        reverse_closing_amls_per_nature = {
            'product': [],
            'tax': [],
            'cash_rounding': [],
            'stock': [],
            'payment': [],
        }

        # When the orders are not fully paid, we need to create an additional line to balance the journal entry.
        open_amount_currency = 0.0
        open_balance = 0.0
        reverse_open_amount_currency = 0.0
        reverse_open_balance = 0.0

        for order in self:
            is_session_closed = order.session_id.state == 'closed'

            if not order.is_invoiced or is_session_closed:
                order_aml_values_list_per_nature = order._prepare_aml_values_list_per_nature()

                # Remove the partner to squash everything on the minimal number of journal items.
                for amls_values_list in order_aml_values_list_per_nature.values():
                    for aml_values in amls_values_list:
                        aml_values['partner_id'] = False
            else:
                order_aml_values_list_per_nature = {}

            # Collect the order's amls except the payment terms.
            if not order.is_invoiced:

                # Prepare journal items for this order to be part of the closing entry.
                for nature, amls_values_list in order_aml_values_list_per_nature.items():
                    if nature == 'payment_terms':
                        for aml_vals in amls_values_list:
                            open_balance += aml_vals['balance']
                            open_amount_currency += aml_vals['amount_currency']
                    elif nature in closing_amls_per_nature:
                        closing_amls_per_nature[nature] += amls_values_list

            elif is_session_closed:
                # Reverse the existing journal items for this order in case of a closed session.
                for nature, amls_values_list in order_aml_values_list_per_nature.items():
                    if nature == 'payment_terms':
                        for aml_vals in amls_values_list:
                            reverse_open_balance -= aml_vals['balance']
                            reverse_open_amount_currency -= aml_vals['amount_currency']
                    elif nature in reverse_closing_amls_per_nature:
                        reverse_closing_amls_per_nature[nature] += [
                            {
                                **x,
                                'amount_currency': -x['amount_currency'],
                                'balance': -x['balance'],
                            }
                            for x in amls_values_list
                        ]

            closing_st_line_vals_mapping = {}
            for payment in order.payment_ids:

                if payment.currency_id.is_zero(payment.amount):
                    continue

                payment_method = payment.payment_method_id
                payment_amls_values_list_per_nature = payment._prepare_aml_values_list_per_nature()

                # Remove the partner to squash everything on the minimal number of journal items.
                if not order.is_invoiced and payment_method.type != 'pay_later' and not payment_method.split_transactions:
                    for aml_vals in payment_amls_values_list_per_nature.values():
                        aml_vals['partner_id'] = False

                # Receivable line that will be reconciled to the payment / statement lines / bank journal entry.
                counterpart_aml_vals = payment_amls_values_list_per_nature['counterpart_receivable']
                closing_amls_per_nature['payment'].append(counterpart_aml_vals)

                open_balance -= counterpart_aml_vals['balance']
                open_amount_currency -= counterpart_aml_vals['amount_currency']

                if payment_method.type == 'cash':
                    if order.is_invoiced and is_session_closed and payment.statement_line_id:

                        # Track the existing statement lines to be reconciled with the newly created move.
                        existing_st_line = payment.statement_line_id
                        res['reverse_st_lines_to_reconcile'][order.account_move] |= existing_st_line

                        # Prepare the cash journal items for the reverse entry.
                        _liquidity_line, _suspense_lines, other_lines = existing_st_line._seek_for_lines()
                        for other_line in other_lines:
                            reverse_closing_amls_per_nature['payment'].append({
                                'name': _("Reverse: %s", other_line.name),
                                'partner_id': False,
                                'currency_id': other_line.currency_id.id,
                                'account_id': other_line.account_id.id,
                                'pos_payment_method_id': payment_method.id,
                                'amount_currency': other_line.amount_currency,
                                'balance': other_line.balance,
                            })
                            reverse_open_balance -= other_line.balance
                            reverse_open_amount_currency -= other_line.amount_currency
                    elif not is_session_closed:
                        bank_stmt_line_vals = {
                            'date': payment.payment_date,
                            'journal_id': payment.payment_method_id.journal_id.id,
                            'pos_session_id': self.session_id.id,
                            'partner_id': payment.partner_id.id,
                            'payment_ref': _("Payment of '%s' using '%s'", order.name, payment_method.name),
                        }

                        # Remove the partner since we consider him as unknown except when invoiced.
                        if not order.is_invoiced and not payment_method.split_transactions:
                            bank_stmt_line_vals['partner_id'] = False

                        grouping_key = frozendict({
                            'date': bank_stmt_line_vals['date'],
                            'partner_id': bank_stmt_line_vals['partner_id'],
                            'pos_payment_method_id': payment_method.id,
                        })
                        res_entry = closing_st_line_vals_mapping.setdefault(grouping_key, {
                            'st_line_vals': bank_stmt_line_vals,
                            'payment_method': payment_method,
                            'payments': self.env['pos.payment'],
                            'amount': 0.0,
                            'date': bank_stmt_line_vals['date'],
                        })
                        res_entry['amount'] += payment.amount
                        res_entry['payments'] |= payment

                elif payment_method.type == 'bank':
                    if order.is_invoiced:
                        res['closing_payment_vals_list'].append((payment, payment._prepare_account_payment_values()))

                        if is_session_closed:
                            res_entry = res['reverse_closing_bank_entry_per_pay_method'][payment_method]
                            res_entry['pos_payments'] |= payment
                            res_entry['closing_bank_entry'] = payment.account_move_id

                            # Add the journal item to reverse the closing journal entry.
                            reverse_closing_amls_per_nature['payment'].append({
                                **counterpart_aml_vals,
                                'partner_id': False,
                                'amount_currency': -counterpart_aml_vals['amount_currency'],
                                'balance': -counterpart_aml_vals['balance'],
                            })
                            reverse_open_balance += counterpart_aml_vals['balance']
                            reverse_open_amount_currency += counterpart_aml_vals['amount_currency']

                            # Add the journal items to reverse the bank journal entry.
                            res['reverse_closing_bank_entry_per_pay_method'][payment_method]['amls_values_list'] += [
                                {
                                    **payment_amls_values_list_per_nature['outstanding'],
                                    'partner_id': False,
                                    'amount_currency': -payment_amls_values_list_per_nature['outstanding']['amount_currency'],
                                    'balance': -payment_amls_values_list_per_nature['outstanding']['balance'],
                                },
                                {
                                    **payment_amls_values_list_per_nature['receivable'],
                                    'partner_id': False,
                                    'amount_currency': -payment_amls_values_list_per_nature['receivable']['amount_currency'],
                                    'balance': -payment_amls_values_list_per_nature['receivable']['balance'],
                                }
                            ]

                    else:
                        res_entry = res['closing_bank_entry_per_pay_method'][payment_method]
                        res_entry['pos_payments'] |= payment
                        res_entry['amls_values_list'] += [
                            payment_amls_values_list_per_nature['outstanding'],
                            payment_amls_values_list_per_nature['receivable'],
                        ]
                elif payment_method.type == 'pay_later' and order.is_invoiced and is_session_closed:

                    # Add the journal item to reverse the closing journal entry.
                    reverse_closing_amls_per_nature['payment'].append({
                        **counterpart_aml_vals,
                        'amount_currency': -counterpart_aml_vals['amount_currency'],
                        'balance': -counterpart_aml_vals['balance'],
                    })
                    reverse_open_balance += counterpart_aml_vals['balance']
                    reverse_open_amount_currency += counterpart_aml_vals['amount_currency']

            # Create the statement lines.
            for res_entry in closing_st_line_vals_mapping.values():

                st_line_vals = res_entry['st_line_vals']
                payment_method = res_entry['payment_method']

                # Compute amounts.
                journal = payment_method.journal_id
                journal_currency = journal.currency_id or journal.company_id.currency_id
                if session.currency_id == journal_currency:
                    amount_currency = 0.0
                    foreign_currency_id = None
                    amount = res_entry['amount']
                else:
                    amount_currency = res_entry['amount']
                    foreign_currency_id = session.currency_id.id
                    amount = session.currency_id\
                        ._convert(amount_currency, journal_currency, journal.company_id, res_entry['date'])

                # Force the counterpart account to reconcile the statement line directly.
                if st_line_vals['partner_id']:
                    partner = self.env['res.partner'].browse(st_line_vals['partner_id'])
                else:
                    partner = self.env['res.partner']
                counterpart_account = partner.with_company(journal.company_id).property_account_receivable_id \
                                      or payment_method.receivable_account_id \
                                      or journal.company_id.account_default_pos_receivable_account_id

                st_line_vals.update({
                    'foreign_currency_id': foreign_currency_id,
                    'amount': amount,
                    'amount_currency': amount_currency,
                    'counterpart_account_id': counterpart_account.id,
                })

                # Deduce the payment owning the statement lines.
                # In case the customer is paying 100 in cash and has 20 as returned amount, the payment of 100 will be
                # linked to the statement line. However, if the customer is paying the 100 in bank, then the payment
                # of 20 will be linked to the statement line since it's the only one cash transaction.
                payment = res_entry['payments'].sorted('is_change')[-1]
                res['closing_st_line_vals_list'].append((payment, st_line_vals))

        # Prepare the POS journal entry.
        closing_entry_vals = session._prepare_closing_journal_entry(
            closing_amls_per_nature,
            open_amount_currency,
            open_balance,
        )
        if closing_entry_vals['line_ids']:
            res['closing_entry_vals'] = closing_entry_vals

        # Prepare a journal entry for each bank payment method.
        for payment_method, res_entry in res['closing_bank_entry_per_pay_method'].items():
            res_entry['bank_entry_vals'] = session._prepare_closing_bank_journal_entry(payment_method, res_entry.pop('amls_values_list'))

        # Prepare the reverse POS journal entry.
        reverse_closing_entry_vals = session._prepare_closing_journal_entry(
            reverse_closing_amls_per_nature,
            reverse_open_amount_currency,
            reverse_open_balance,
        )
        if reverse_closing_entry_vals['line_ids']:
            res['reverse_closing_entry_vals'] = reverse_closing_entry_vals

        # Prepare the reverse journal entry for each bank payment method.
        for payment_method, res_entry in res['reverse_closing_bank_entry_per_pay_method'].items():
            res_entry['bank_entry_vals'] = session._prepare_closing_bank_journal_entry(payment_method, res_entry.pop('amls_values_list'))

        return res

    # this method is unused, and so is the state 'cancel'
    def action_pos_order_cancel(self):
        return self.write({'state': 'cancel'})

    @api.model
    def create_from_ui(self, orders, draft=False):
        """ Create and update Orders from the frontend PoS application.

        Create new orders and update orders that are in draft status. If an order already exists with a status
        diferent from 'draft'it will be discareded, otherwise it will be saved to the database. If saved with
        'draft' status the order can be overwritten later by this function.

        :param orders: dictionary with the orders to be created.
        :type orders: dict.
        :param draft: Indicate if the orders are ment to be finalised or temporarily saved.
        :type draft: bool.
        :Returns: list -- list of db-ids for the created and updated orders.
        """
        order_ids = []
        for order in orders:
            existing_order = False
            if 'server_id' in order['data']:
                existing_order = self.env['pos.order'].search(['|', ('id', '=', order['data']['server_id']), ('pos_reference', '=', order['data']['name'])], limit=1)
            if (existing_order and existing_order.state == 'draft') or not existing_order:
                order_ids.append(self._process_order(order, draft, existing_order))

        return self.env['pos.order'].search_read(domain=[('id', 'in', order_ids)], fields=['id', 'pos_reference', 'account_move'], load=False)

    def _should_create_picking_real_time(self):
        return not self.session_id.update_stock_at_closing or (self.company_id.anglo_saxon_accounting and self.to_invoice)

    def _create_order_picking(self):
        self.ensure_one()
        if self.to_ship:
            self.lines._launch_stock_rule_from_pos_order_lines()
        else:
            if self._should_create_picking_real_time():
                picking_type = self.config_id.picking_type_id
                if self.partner_id.property_stock_customer:
                    destination_id = self.partner_id.property_stock_customer.id
                elif not picking_type or not picking_type.default_location_dest_id:
                    destination_id = self.env['stock.warehouse']._get_partner_locations()[0].id
                else:
                    destination_id = picking_type.default_location_dest_id.id

                pickings = self.env['stock.picking']._create_picking_from_pos_order_lines(destination_id, self.lines, picking_type, self.partner_id)
                pickings.write({'pos_session_id': self.session_id.id, 'pos_order_id': self.id, 'origin': self.name})

    def add_payment(self, data):
        """Create a new payment for the order"""
        self.ensure_one()
        self.env['pos.payment'].create(data)
        self.amount_paid = sum(self.payment_ids.mapped('amount'))

    def _prepare_refund_values(self, current_session):
        self.ensure_one()
        return {
            'name': self.name + _(' REFUND'),
            'session_id': current_session.id,
            'date_order': fields.Datetime.now(),
            'pos_reference': self.pos_reference,
            'lines': False,
            'amount_tax': -self.amount_tax,
            'amount_total': -self.amount_total,
            'amount_paid': 0,
            'is_total_cost_computed': False
        }

    def _prepare_mail_values(self, name, client, ticket):
        message = _("<p>Dear %s,<br/>Here is your electronic ticket for the %s. </p>") % (client['name'], name)

        return {
            'subject': _('Receipt %s', name),
            'body_html': message,
            'author_id': self.env.user.partner_id.id,
            'email_from': self.env.company.email or self.env.user.email_formatted,
            'email_to': client['email'],
            'attachment_ids': self._add_mail_attachment(name, ticket),
        }

    def refund(self):
        """Create a copy of order  for refund order"""
        refund_orders = self.env['pos.order']
        for order in self:
            # When a refund is performed, we are creating it in a session having the same config as the original
            # order. It can be the same session, or if it has been closed the new one that has been opened.
            current_session = order.session_id.config_id.current_session_id
            if not current_session:
                raise UserError(_('To return product(s), you need to open a session in the POS %s', order.session_id.config_id.display_name))
            refund_order = order.copy(
                order._prepare_refund_values(current_session)
            )
            for line in order.lines:
                PosOrderLineLot = self.env['pos.pack.operation.lot']
                for pack_lot in line.pack_lot_ids:
                    PosOrderLineLot += pack_lot.copy()
                line.copy(line._prepare_refund_data(refund_order, PosOrderLineLot))
            refund_orders |= refund_order

        return {
            'name': _('Return Products'),
            'view_mode': 'form',
            'res_model': 'pos.order',
            'res_id': refund_orders.ids[0],
            'view_id': False,
            'context': self.env.context,
            'type': 'ir.actions.act_window',
            'target': 'current',
        }

    def _add_mail_attachment(self, name, ticket):
        filename = 'Receipt-' + name + '.jpg'
        receipt = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': ticket,
            'res_model': 'pos.order',
            'res_id': self.ids[0],
            'mimetype': 'image/jpeg',
        })
        attachment = [(4, receipt.id)]

        if self.mapped('account_move'):
            report = self.env['ir.actions.report']._render_qweb_pdf("account.account_invoices", self.account_move.ids[0])
            filename = name + '.pdf'
            invoice = self.env['ir.attachment'].create({
                'name': filename,
                'type': 'binary',
                'datas': base64.b64encode(report[0]),
                'res_model': 'pos.order',
                'res_id': self.ids[0],
                'mimetype': 'application/x-pdf'
            })
            attachment += [(4, invoice.id)]

        return attachment

    def action_receipt_to_customer(self, name, client, ticket):
        if not self:
            return False
        if not client.get('email'):
            return False

        mail = self.env['mail.mail'].sudo().create(self._prepare_mail_values(name, client, ticket))
        mail.send()

    @api.model
    def search_paid_order_ids(self, config_id, domain, limit, offset):
        """Search for 'paid' orders that satisfy the given domain, limit and offset."""
        default_domain = ['&', ('config_id', '=', config_id), '!', '|', ('state', '=', 'draft'), ('state', '=', 'cancelled')]
        real_domain = AND([domain, default_domain])
        ids = self.search(AND([domain, default_domain]), limit=limit, offset=offset).ids
        totalCount = self.search_count(real_domain)
        return {'ids': ids, 'totalCount': totalCount}

    def _export_for_ui(self, order):
        timezone = pytz.timezone(self._context.get('tz') or self.env.user.tz or 'UTC')
        return {
            'lines': [[0, 0, line] for line in order.lines.export_for_ui()],
            'statement_ids': [[0, 0, payment] for payment in order.payment_ids.export_for_ui()],
            'name': order.pos_reference,
            'uid': re.search('([0-9-]){14}', order.pos_reference).group(0),
            'amount_paid': order.amount_paid,
            'amount_total': order.amount_total,
            'amount_tax': order.amount_tax,
            'amount_return': order.amount_return,
            'pos_session_id': order.session_id.id,
            'pricelist_id': order.pricelist_id.id,
            'partner_id': order.partner_id.id,
            'user_id': order.user_id.id,
            'sequence_number': order.sequence_number,
            'creation_date': order.date_order.astimezone(timezone),
            'fiscal_position_id': order.fiscal_position_id.id,
            'to_invoice': order.to_invoice,
            'to_ship': order.to_ship,
            'state': order.state,
            'account_move': order.account_move.id,
            'id': order.id,
            'is_tipped': order.is_tipped,
            'tip_amount': order.tip_amount,
            'access_token': order.access_token,
        }

    def _get_fields_for_order_line(self):
        """This function is here to be overriden"""
        return []

    def export_for_ui(self):
        """ Returns a list of dict with each item having similar signature as the return of
            `export_as_JSON` of models.Order. This is useful for back-and-forth communication
            between the pos frontend and backend.
        """
        return self.mapped(self._export_for_ui) if self else []


class PosOrderLine(models.Model):
    _name = "pos.order.line"
    _description = "Point of Sale Order Lines"
    _rec_name = "product_id"

    def _order_line_fields(self, line, session_id=None):
        if line and 'name' not in line[2]:
            session = self.env['pos.session'].browse(session_id).exists() if session_id else None
            if session and session.config_id.sequence_line_id:
                # set name based on the sequence specified on the config
                line[2]['name'] = session.config_id.sequence_line_id._next()
            else:
                # fallback on any pos.order.line sequence
                line[2]['name'] = self.env['ir.sequence'].next_by_code('pos.order.line')

        if line and 'tax_ids' not in line[2]:
            product = self.env['product.product'].browse(line[2]['product_id'])
            line[2]['tax_ids'] = [(6, 0, [x.id for x in product.taxes_id])]
        # Clean up fields sent by the JS
        line = [
            line[0], line[1], {k: v for k, v in line[2].items() if k in self.env['pos.order.line']._fields}
        ]
        return line

    company_id = fields.Many2one('res.company', string='Company', related="order_id.company_id", store=True)
    name = fields.Char(string='Line No', required=True, copy=False)
    notice = fields.Char(string='Discount Notice')
    product_id = fields.Many2one('product.product', string='Product', domain=[('sale_ok', '=', True)], required=True, change_default=True)
    price_unit = fields.Float(string='Unit Price', digits=0)
    qty = fields.Float('Quantity', digits='Product Unit of Measure', default=1)
    price_subtotal = fields.Float(string='Subtotal w/o Tax', digits=0,
        readonly=True, required=True)
    price_subtotal_incl = fields.Float(string='Subtotal', digits=0,
        readonly=True, required=True)
    price_extra = fields.Float(string="Price extra")
    margin = fields.Monetary(string="Margin", compute='_compute_margin')
    margin_percent = fields.Float(string="Margin (%)", compute='_compute_margin', digits=(12, 4))
    total_cost = fields.Float(string='Total cost', digits='Product Price', readonly=True)
    is_total_cost_computed = fields.Boolean(help="Allows to know if the total cost has already been computed or not")
    discount = fields.Float(string='Discount (%)', digits=0, default=0.0)
    order_id = fields.Many2one('pos.order', string='Order Ref', ondelete='cascade', required=True, index=True)
    tax_ids = fields.Many2many('account.tax', string='Taxes', readonly=True)
    tax_ids_after_fiscal_position = fields.Many2many('account.tax', compute='_get_tax_ids_after_fiscal_position', string='Taxes to Apply')
    pack_lot_ids = fields.One2many('pos.pack.operation.lot', 'pos_order_line_id', string='Lot/serial Number')
    product_uom_id = fields.Many2one('uom.uom', string='Product UoM', related='product_id.uom_id')
    currency_id = fields.Many2one('res.currency', related='order_id.currency_id')
    full_product_name = fields.Char('Full Product Name')
    customer_note = fields.Char('Customer Note')
    refund_orderline_ids = fields.One2many('pos.order.line', 'refunded_orderline_id', 'Refund Order Lines', help='Orderlines in this field are the lines that refunded this orderline.')
    refunded_orderline_id = fields.Many2one('pos.order.line', 'Refunded Order Line', help='If this orderline is a refund, then the refunded orderline is specified in this field.')
    refunded_qty = fields.Float('Refunded Quantity', compute='_compute_refund_qty', help='Number of items refunded in this orderline.')

    @api.depends('refund_orderline_ids')
    def _compute_refund_qty(self):
        for orderline in self:
            orderline.refunded_qty = -sum(orderline.mapped('refund_orderline_ids.qty'))

    def _prepare_refund_data(self, refund_order, PosOrderLineLot):
        """
        This prepares data for refund order line. Inheritance may inject more data here

        @param refund_order: the pre-created refund order
        @type refund_order: pos.order

        @param PosOrderLineLot: the pre-created Pack operation Lot
        @type PosOrderLineLot: pos.pack.operation.lot

        @return: dictionary of data which is for creating a refund order line from the original line
        @rtype: dict
        """
        self.ensure_one()
        return {
            'name': self.name + _(' REFUND'),
            'qty': -(self.qty - self.refunded_qty),
            'order_id': refund_order.id,
            'price_subtotal': -self.price_subtotal,
            'price_subtotal_incl': -self.price_subtotal_incl,
            'pack_lot_ids': PosOrderLineLot,
            'is_total_cost_computed': False,
            'refunded_orderline_id': self.id,
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('order_id') and not vals.get('name'):
                # set name based on the sequence specified on the config
                config = self.env['pos.order'].browse(vals['order_id']).session_id.config_id
                if config.sequence_line_id:
                    vals['name'] = config.sequence_line_id._next()
            if not vals.get('name'):
                # fallback on any pos.order sequence
                vals['name'] = self.env['ir.sequence'].next_by_code('pos.order.line')
        return super().create(vals_list)

    def write(self, values):
        if values.get('pack_lot_line_ids'):
            for pl in values.get('pack_lot_ids'):
                if pl[2].get('server_id'):
                    pl[2]['id'] = pl[2]['server_id']
                    del pl[2]['server_id']
        return super().write(values)

    @api.onchange('price_unit', 'tax_ids', 'qty', 'discount', 'product_id')
    def _onchange_amount_line_all(self):
        for line in self:
            res = line._compute_amount_line_all()
            line.update(res)

    def _compute_amount_line_all(self):
        self.ensure_one()
        fpos = self.order_id.fiscal_position_id
        tax_ids_after_fiscal_position = fpos.map_tax(self.tax_ids)
        price = self.price_unit * (1 - (self.discount or 0.0) / 100.0)
        taxes = tax_ids_after_fiscal_position.compute_all(price, self.order_id.pricelist_id.currency_id, self.qty, product=self.product_id, partner=self.order_id.partner_id)
        return {
            'price_subtotal_incl': taxes['total_included'],
            'price_subtotal': taxes['total_excluded'],
            'taxes': taxes['taxes']
        }

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            if not self.order_id.pricelist_id:
                raise UserError(
                    _('You have to select a pricelist in the sale form !\n'
                      'Please set one before choosing a product.'))
            price = self.order_id.pricelist_id._get_product_price(
                self.product_id, self.qty or 1.0)
            self.tax_ids = self.product_id.taxes_id.filtered(lambda r: not self.company_id or r.company_id == self.company_id)
            tax_ids_after_fiscal_position = self.order_id.fiscal_position_id.map_tax(self.tax_ids)
            self.price_unit = self.env['account.tax']._fix_tax_included_price_company(price, self.tax_ids, tax_ids_after_fiscal_position, self.company_id)
            self._onchange_qty()

    @api.onchange('qty', 'discount', 'price_unit', 'tax_ids')
    def _onchange_qty(self):
        if self.product_id:
            if not self.order_id.pricelist_id:
                raise UserError(_('You have to select a pricelist in the sale form.'))
            price = self.price_unit * (1 - (self.discount or 0.0) / 100.0)
            self.price_subtotal = self.price_subtotal_incl = price * self.qty
            if (self.tax_ids):
                taxes = self.tax_ids.compute_all(price, self.order_id.pricelist_id.currency_id, self.qty, product=self.product_id, partner=False)
                self.price_subtotal = taxes['total_excluded']
                self.price_subtotal_incl = taxes['total_included']

    @api.depends('order_id', 'order_id.fiscal_position_id')
    def _get_tax_ids_after_fiscal_position(self):
        for line in self:
            line.tax_ids_after_fiscal_position = line.order_id.fiscal_position_id.map_tax(line.tax_ids)

    def _export_for_ui(self, orderline):
        return {
            'qty': orderline.qty,
            'price_unit': orderline.price_unit,
            'price_subtotal': orderline.price_subtotal,
            'price_subtotal_incl': orderline.price_subtotal_incl,
            'product_id': orderline.product_id.id,
            'discount': orderline.discount,
            'tax_ids': [[6, False, orderline.tax_ids.mapped(lambda tax: tax.id)]],
            'id': orderline.id,
            'pack_lot_ids': [[0, 0, lot] for lot in orderline.pack_lot_ids.export_for_ui()],
            'customer_note': orderline.customer_note,
            'refunded_qty': orderline.refunded_qty,
            'price_extra': orderline.price_extra,
        }

    def export_for_ui(self):
        return self.mapped(self._export_for_ui) if self else []

    def _get_procurement_group(self):
        return self.order_id.procurement_group_id

    def _prepare_procurement_group_vals(self):
        return {
            'name': self.order_id.name,
            'move_type': self.order_id.config_id.picking_policy,
            'pos_order_id': self.order_id.id,
            'partner_id': self.order_id.partner_id.id,
        }

    def _prepare_procurement_values(self, group_id=False):
        """ Prepare specific key for moves or other components that will be created from a stock rule
        comming from a sale order line. This method could be override in order to add other custom key that could
        be used in move/po creation.
        """
        self.ensure_one()
        # Use the delivery date if there is else use date_order and lead time
        date_deadline = self.order_id.date_order
        values = {
            'group_id': group_id,
            'date_planned': date_deadline,
            'date_deadline': date_deadline,
            'route_ids': self.order_id.config_id.route_id,
            'warehouse_id': self.order_id.config_id.warehouse_id or False,
            'partner_id': self.order_id.partner_id.id,
            'product_description_variants': self.full_product_name,
            'company_id': self.order_id.company_id,
        }
        return values

    def _launch_stock_rule_from_pos_order_lines(self):

        procurements = []
        for line in self:
            line = line.with_company(line.company_id)
            if not line.product_id.type in ('consu','product'):
                continue

            group_id = line._get_procurement_group()
            if not group_id:
                group_id = self.env['procurement.group'].create(line._prepare_procurement_group_vals())
                line.order_id.procurement_group_id = group_id

            values = line._prepare_procurement_values(group_id=group_id)
            product_qty = line.qty

            procurement_uom = line.product_id.uom_id
            procurements.append(self.env['procurement.group'].Procurement(
                line.product_id, product_qty, procurement_uom,
                line.order_id.partner_id.property_stock_customer,
                line.name, line.order_id.name, line.order_id.company_id, values))
        if procurements:
            self.env['procurement.group'].run(procurements)

        # This next block is currently needed only because the scheduler trigger is done by picking confirmation rather than stock.move confirmation
        orders = self.mapped('order_id')
        for order in orders:
            pickings_to_confirm = order.picking_ids
            if pickings_to_confirm:
                # Trigger the Scheduler for Pickings
                pickings_to_confirm.action_confirm()
                tracked_lines = order.lines.filtered(lambda l: l.product_id.tracking != 'none')
                lines_by_tracked_product = groupby(sorted(tracked_lines, key=lambda l: l.product_id.id), key=lambda l: l.product_id.id)
                for product_id, lines in lines_by_tracked_product:
                    lines = self.env['pos.order.line'].concat(*lines)
                    moves = pickings_to_confirm.move_ids.filtered(lambda m: m.product_id.id == product_id)
                    moves.move_line_ids.unlink()
                    moves._add_mls_related_to_order(lines, are_qties_done=False)
                    moves._recompute_state()
        return True

    def _is_product_storable_fifo_avco(self):
        self.ensure_one()
        return self.product_id.type == 'product' and self.product_id.cost_method in ['fifo', 'average']

    def _compute_total_cost(self, stock_moves):
        """
        Compute the total cost of the order lines.
        :param stock_moves: recordset of `stock.move`, used for fifo/avco lines
        """
        for line in self.filtered(lambda l: not l.is_total_cost_computed):
            product = line.product_id
            if line._is_product_storable_fifo_avco() and stock_moves:
                product_cost = product._compute_average_price(0, line.qty, stock_moves.filtered(lambda ml: ml.product_id == product))
            else:
                product_cost = product.standard_price
            line.total_cost = line.qty * product.cost_currency_id._convert(
                from_amount=product_cost,
                to_currency=line.currency_id,
                company=line.company_id or self.env.company,
                date=line.order_id.date_order or fields.Date.today(),
                round=False,
            )
            line.is_total_cost_computed = True

    @api.depends('price_subtotal', 'total_cost')
    def _compute_margin(self):
        for line in self:
            line.margin = line.price_subtotal - line.total_cost
            line.margin_percent = not float_is_zero(line.price_subtotal, line.currency_id.rounding) and line.margin / line.price_subtotal or 0


class PosOrderLineLot(models.Model):
    _name = "pos.pack.operation.lot"
    _description = "Specify product lot/serial number in pos order line"
    _rec_name = "lot_name"

    pos_order_line_id = fields.Many2one('pos.order.line')
    order_id = fields.Many2one('pos.order', related="pos_order_line_id.order_id", readonly=False)
    lot_name = fields.Char('Lot Name')
    product_id = fields.Many2one('product.product', related='pos_order_line_id.product_id', readonly=False)

    def _export_for_ui(self, lot):
        return {
            'lot_name': lot.lot_name,
        }

    def export_for_ui(self):
        return self.mapped(self._export_for_ui) if self else []

class ReportSaleDetails(models.AbstractModel):

    _name = 'report.point_of_sale.report_saledetails'
    _description = 'Point of Sale Details'


    @api.model
    def get_sale_details(self, date_start=False, date_stop=False, config_ids=False, session_ids=False):
        """ Serialise the orders of the requested time period, configs and sessions.

        :param date_start: The dateTime to start, default today 00:00:00.
        :type date_start: str.
        :param date_stop: The dateTime to stop, default date_start + 23:59:59.
        :type date_stop: str.
        :param config_ids: Pos Config id's to include.
        :type config_ids: list of numbers.
        :param session_ids: Pos Config id's to include.
        :type session_ids: list of numbers.

        :returns: dict -- Serialised sales.
        """
        domain = [('state', 'in', ['paid','invoiced','done'])]

        if (session_ids):
            domain = AND([domain, [('session_id', 'in', session_ids)]])
        else:
            if date_start:
                date_start = fields.Datetime.from_string(date_start)
            else:
                # start by default today 00:00:00
                user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
                today = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
                date_start = today.astimezone(pytz.timezone('UTC'))

            if date_stop:
                date_stop = fields.Datetime.from_string(date_stop)
                # avoid a date_stop smaller than date_start
                if (date_stop < date_start):
                    date_stop = date_start + timedelta(days=1, seconds=-1)
            else:
                # stop by default today 23:59:59
                date_stop = date_start + timedelta(days=1, seconds=-1)

            domain = AND([domain,
                [('date_order', '>=', fields.Datetime.to_string(date_start)),
                ('date_order', '<=', fields.Datetime.to_string(date_stop))]
            ])

            if config_ids:
                domain = AND([domain, [('config_id', 'in', config_ids)]])

        orders = self.env['pos.order'].search(domain)

        user_currency = self.env.company.currency_id

        total = 0.0
        products_sold = {}
        taxes = {}
        for order in orders:
            if user_currency != order.pricelist_id.currency_id:
                total += order.pricelist_id.currency_id._convert(
                    order.amount_total, user_currency, order.company_id, order.date_order or fields.Date.today())
            else:
                total += order.amount_total
            currency = order.session_id.currency_id

            for line in order.lines:
                key = (line.product_id, line.price_unit, line.discount)
                products_sold.setdefault(key, 0.0)
                products_sold[key] += line.qty

                if line.tax_ids_after_fiscal_position:
                    line_taxes = line.tax_ids_after_fiscal_position.sudo().compute_all(line.price_unit * (1-(line.discount or 0.0)/100.0), currency, line.qty, product=line.product_id, partner=line.order_id.partner_id or False)
                    for tax in line_taxes['taxes']:
                        taxes.setdefault(tax['id'], {'name': tax['name'], 'tax_amount':0.0, 'base_amount':0.0})
                        taxes[tax['id']]['tax_amount'] += tax['amount']
                        taxes[tax['id']]['base_amount'] += tax['base']
                else:
                    taxes.setdefault(0, {'name': _('No Taxes'), 'tax_amount':0.0, 'base_amount':0.0})
                    taxes[0]['base_amount'] += line.price_subtotal_incl

        payment_ids = self.env["pos.payment"].search([('pos_order_id', 'in', orders.ids)]).ids
        if payment_ids:
            self.env.cr.execute("""
                SELECT COALESCE(method.name->>%s, method.name->>'en_US') as name, sum(amount) total
                FROM pos_payment AS payment,
                     pos_payment_method AS method
                WHERE payment.payment_method_id = method.id
                    AND payment.id IN %s
                GROUP BY method.name
            """, (self.env.lang, tuple(payment_ids),))
            payments = self.env.cr.dictfetchall()
        else:
            payments = []

        return {
            'date_start': date_start,
            'date_stop': date_stop,
            'currency_precision': user_currency.decimal_places,
            'total_paid': user_currency.round(total),
            'payments': payments,
            'company_name': self.env.company.name,
            'taxes': list(taxes.values()),
            'products': sorted([{
                'product_id': product.id,
                'product_name': product.name,
                'code': product.default_code,
                'quantity': qty,
                'price_unit': price_unit,
                'discount': discount,
                'uom': product.uom_id.name
            } for (product, price_unit, discount), qty in products_sold.items()], key=lambda l: l['product_name'])
        }

    @api.model
    def _get_report_values(self, docids, data=None):
        data = dict(data or {})
        # initialize data keys with their value if provided, else None
        data.update({
            'session_ids': data.get('session_ids') or docids,
            'config_ids': data.get('config_ids'),
            'date_start': data.get('date_start'),
            'date_stop': data.get('date_stop')
        })
        configs = self.env['pos.config'].browse(data['config_ids'])
        data.update(self.get_sale_details(data['date_start'], data['date_stop'], configs.ids, data['session_ids']))
        return data

class AccountCashRounding(models.Model):
    _inherit = 'account.cash.rounding'

    @api.constrains('rounding', 'rounding_method', 'strategy')
    def _check_session_state(self):
        open_session = self.env['pos.session'].search([('config_id.rounding_method', 'in', self.ids), ('state', '!=', 'closed')], limit=1)
        if open_session:
            raise ValidationError(
                _("You are not allowed to change the cash rounding configuration while a pos session using it is already opened."))
