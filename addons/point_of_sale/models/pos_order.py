# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from datetime import datetime
from markupsafe import Markup
from itertools import groupby
from collections import defaultdict
from uuid import uuid4

import psycopg2
import pytz

from odoo import api, fields, models, tools, _, Command
from odoo.tools import float_is_zero, float_round, float_repr, float_compare, formatLang
from odoo.exceptions import ValidationError, UserError
from odoo.osv.expression import AND
import base64


_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _name = 'pos.order'
    _inherit = ["portal.mixin", "pos.bus.mixin", "pos.load.mixin", "mail.thread"]
    _description = "Point of Sale Orders"
    _order = "date_order desc, name desc, id desc"

    # This function deals with orders that belong to a closed session. It attempts to find
    # any open session that can be used to capture the order. If no open session is found,
    # an error is raised, asking the user to open a session.
    def _get_valid_session(self, order):
        PosSession = self.env['pos.session']
        closed_session = PosSession.browse(order['session_id'])

        _logger.warning('Session %s (ID: %s) was closed but received order %s (total: %s) belonging to it',
                        closed_session.name,
                        closed_session.id,
                        order['uuid'],
                        order['amount_total'])

        open_session = PosSession.search([
            ('state', 'not in', ('closed', 'closing_control')),
            ('config_id', '=', closed_session.config_id.id)
        ], limit=1)

        if open_session:
            _logger.warning('Using open session %s for saving order %s', open_session.name, order['name'])
            return open_session

        raise UserError(_('No open session available. Please open a new session to capture the order.'))

    @api.model
    def _load_pos_data_domain(self, data):
        return [('state', '=', 'draft'), ('config_id', '=', data['pos.config'][0]['id'])]

    @api.model
    def _process_order(self, order, existing_order):
        """Create or update an pos.order from a given dictionary.

        :param dict order: dictionary representing the order.
        :param existing_order: order to be updated or False.
        :type existing_order: pos.order.
        :returns: id of created/updated pos.order
        :rtype: int
        """
        draft = True if order.get('state') == 'draft' else False
        pos_session = self.env['pos.session'].browse(order['session_id'])
        if pos_session.state == 'closing_control' or pos_session.state == 'closed':
            order['session_id'] = self._get_valid_session(order).id

        if order.get('partner_id'):
            partner_id = self.env['res.partner'].browse(order['partner_id'])
            if not partner_id.exists():
                order.update({
                    "partner_id": False,
                    "to_invoice": False,
                })

        pos_order = False
        combo_child_uuids_by_parent_uuid = self._prepare_combo_line_uuids(order)

        if not existing_order:
            pos_order = self.create({
                **{key: value for key, value in order.items() if key != 'name'},
            })
            pos_order = pos_order.with_company(pos_order.company_id)
        else:
            pos_order = self.env['pos.order'].browse(order.get('id'))

            # Save lines and payments before to avoid exception if a line is deleted
            # when vals change the state to 'paid'
            for field in ['lines', 'payment_ids']:
                if order.get(field):
                    pos_order.write({field: order.get(field)})
                    order[field] = []

            pos_order.write(order)

        pos_order._link_combo_items(combo_child_uuids_by_parent_uuid)
        self = self.with_company(pos_order.company_id)
        self._process_payment_lines(order, pos_order, pos_session, draft)
        return pos_order._process_saved_order(draft)

    def _prepare_combo_line_uuids(self, order_vals):
        acc = {}
        for line in order_vals['lines']:
            if line[0] not in [0, 1]:
                continue

            line = line[2]

            if line.get('combo_line_ids'):
                filtered_lines = list(filter(lambda l: l[0] in [0, 1] and l[2].get('id') and l[2].get('id') in line.get('combo_line_ids'), order_vals['lines']))
                acc[line['uuid']] = [l[2]['uuid'] for l in filtered_lines]

            line['combo_line_ids'] = False
            line['combo_parent_id'] = False

        return acc

    def _link_combo_items(self, combo_child_uuids_by_parent_uuid):
        self.ensure_one()

        for parent_uuid, child_uuids in combo_child_uuids_by_parent_uuid.items():
            parent_line = self.lines.filtered(lambda line: line.uuid == parent_uuid)
            if not parent_line:
                continue
            parent_line.combo_line_ids = [(6, 0, self.lines.filtered(lambda line: line.uuid in child_uuids).ids)]

    def _process_saved_order(self, draft):
        self.ensure_one()
        if not draft:
            try:
                self.action_pos_order_paid()
            except psycopg2.DatabaseError:
                # do not hide transactional errors, the order(s) won't be saved!
                raise
            except Exception as e:
                _logger.error('Could not fully process the POS Order: %s', tools.exception_to_unicode(e))
            self._create_order_picking()
            self._compute_total_cost_in_real_time()

        if self.to_invoice and self.state == 'paid':
            self._generate_pos_order_invoice()

        return self.id

    def _clean_payment_lines(self):
        self.ensure_one()
        self.payment_ids.unlink()

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
        prec_acc = order.currency_id.decimal_places

        # Recompute amount paid because we don't trust the client
        order.amount_paid = sum(order.payment_ids.mapped('amount'))

        if not draft and not float_is_zero(pos_order['amount_return'], prec_acc):
            cash_payment_method = pos_session.payment_method_ids.filtered('is_cash_count')[:1]
            if not cash_payment_method:
                raise UserError(_("No cash statement found for this session. Unable to record returned cash."))
            return_payment_vals = {
                'name': _('return'),
                'pos_order_id': order.id,
                'amount': -pos_order['amount_return'],
                'payment_date': fields.Datetime.now(),
                'payment_method_id': cash_payment_method.id,
                'is_change': True,
            }
            order.add_payment(return_payment_vals)
            order._compute_prices()

    def _prepare_tax_base_line_values(self):
        """ Convert pos order lines into dictionaries that would be used to compute taxes later.

        :param sign: An optional parameter to force the sign of amounts.
        :return: A list of python dictionaries (see '_prepare_base_line_for_taxes_computation' in account.tax).
        """
        self.ensure_one()
        return self.lines._prepare_tax_base_line_values()

    @api.model
    def _get_invoice_lines_values(self, line_values, pos_order_line):
        return {
            'product_id': line_values['product_id'].id,
            'quantity': line_values['quantity'],
            'discount': line_values['discount'],
            'price_unit': line_values['price_unit'],
            'name': line_values['name'],
            'tax_ids': [(6, 0, line_values['tax_ids'].ids)],
            'product_uom_id': line_values['uom_id'].id,
        }

    def _prepare_invoice_lines(self):
        """ Prepare a list of orm commands containing the dictionaries to fill the
        'invoice_line_ids' field when creating an invoice.

        :return: A list of Command.create to fill 'invoice_line_ids' when calling account.move.create.
        """
        line_values_list = self._prepare_tax_base_line_values()
        invoice_lines = []
        for line_values in line_values_list:
            line = line_values['record']
            invoice_lines_values = self._get_invoice_lines_values(line_values, line)
            invoice_lines.append((0, None, invoice_lines_values))
            is_percentage = self.pricelist_id and any(
                self.pricelist_id.item_ids.filtered(
                    lambda rule: rule.compute_price == "percentage")
            )
            if is_percentage and float_compare(line.price_unit, line.product_id.lst_price, precision_rounding=self.currency_id.rounding) < 0:
                invoice_lines.append((0, None, {
                    'name': _('Price discount from %(original_price)s to %(discounted_price)s',
                              original_price=float_repr(line.product_id.lst_price, self.currency_id.decimal_places),
                              discounted_price=float_repr(line.price_unit, self.currency_id.decimal_places)),
                    'display_type': 'line_note',
                }))
            if line.customer_note:
                invoice_lines.append((0, None, {
                    'name': line.customer_note,
                    'display_type': 'line_note',
                }))
        if self.general_customer_note:
            invoice_lines.append((0, None, {
                'name': self.general_customer_note,
                'display_type': 'line_note',
            }))
        return invoice_lines

    def _get_pos_anglo_saxon_price_unit(self, product, partner_id, quantity):
        moves = self.filtered(lambda o: o.partner_id.id == partner_id)\
            .mapped('picking_ids.move_ids')\
            ._filter_anglo_saxon_moves(product)\
            .sorted(lambda x: x.date)
        price_unit = product.with_company(self.company_id)._compute_average_price(0, quantity, moves)
        return price_unit

    name = fields.Char(string='Order Ref', required=True, readonly=True, copy=False, default='/')
    last_order_preparation_change = fields.Char(string='Last preparation change', help="Last printed state of the order")
    date_order = fields.Datetime(string='Date', readonly=True, index=True, default=fields.Datetime.now)
    user_id = fields.Many2one(
        comodel_name='res.users', string='Employee',
        help="Employee who uses the cash register.",
        default=lambda self: self.env.uid,
    )
    amount_difference = fields.Float(string='Difference', digits=0, readonly=True)
    amount_tax = fields.Float(string='Taxes', digits=0, readonly=True, required=True)
    amount_total = fields.Float(string='Total', digits=0, readonly=True, required=True)
    amount_paid = fields.Float(string='Paid', digits=0, required=True)
    amount_return = fields.Float(string='Returned', digits=0, required=True, readonly=True)
    margin = fields.Monetary(string="Margin", compute='_compute_margin')
    margin_percent = fields.Float(string="Margin (%)", compute='_compute_margin', digits=(12, 4))
    is_total_cost_computed = fields.Boolean(compute='_compute_is_total_cost_computed',
        help="Allows to know if all the total cost of the order lines have already been computed")
    lines = fields.One2many('pos.order.line', 'order_id', string='Order Lines', copy=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, index=True)
    country_code = fields.Char(related='company_id.account_fiscal_country_id.code')
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist')
    partner_id = fields.Many2one('res.partner', string='Customer', change_default=True, index='btree_not_null')
    sequence_number = fields.Integer(string='Sequence Number', help='A session-unique sequence number for the order. Negative if generated from the client', default=1)
    session_id = fields.Many2one('pos.session', string='Session', index=True, domain="[('state', '=', 'opened')]")
    config_id = fields.Many2one('pos.config', compute='_compute_order_config_id', string="Point of Sale", readonly=False, store=True)
    currency_id = fields.Many2one('res.currency', related='config_id.currency_id', string="Currency")
    currency_rate = fields.Float("Currency Rate", compute='_compute_currency_rate', compute_sudo=True, store=True, digits=0, readonly=True,
        help='The rate of the currency to the currency of rate applicable at the date of the order')

    state = fields.Selection(
        [('draft', 'New'), ('cancel', 'Cancelled'), ('paid', 'Paid'), ('done', 'Posted'), ('invoiced', 'Invoiced')],
        'Status', readonly=True, copy=False, default='draft', index=True)

    account_move = fields.Many2one('account.move', string='Invoice', readonly=True, copy=False, index="btree_not_null")
    picking_ids = fields.One2many('stock.picking', 'pos_order_id')
    picking_count = fields.Integer(compute='_compute_picking_count')
    failed_pickings = fields.Boolean(compute='_compute_picking_count')
    picking_type_id = fields.Many2one('stock.picking.type', related='session_id.config_id.picking_type_id', string="Operation Type", readonly=False)
    procurement_group_id = fields.Many2one('procurement.group', 'Procurement Group', copy=False)
    preset_id = fields.Many2one('pos.preset', string='Preset')
    floating_order_name = fields.Char(string='Order Name')
    general_customer_note = fields.Text(string='General Customer Note')
    internal_note = fields.Text(string='Internal Note')
    nb_print = fields.Integer(string='Number of Print', readonly=True, copy=False, default=0)
    pos_reference = fields.Char(string='Receipt Number', readonly=True, copy=False, index=True, help="""
        Human readable reference for this order.
            * Format: YYLL-SSS-FOOOO
            * YY is the year
            * LL is the login number (proxy to the device)
            * SSS is the session id
            * F is 1 or 0 (1 if sequence number is generated from client)
            * OOOO is the sequence number.
    """
    )
    sale_journal = fields.Many2one('account.journal', related='session_id.config_id.journal_id', string='Sales Journal', store=True, readonly=True, ondelete='restrict')
    fiscal_position_id = fields.Many2one(
        comodel_name='account.fiscal.position', string='Fiscal Position',
        readonly=False,
    )
    payment_ids = fields.One2many('pos.payment', 'pos_order_id', string='Payments')
    session_move_id = fields.Many2one('account.move', string='Session Journal Entry', related='session_id.move_id', readonly=True, copy=False)
    to_invoice = fields.Boolean('To invoice', copy=False)
    shipping_date = fields.Date('Shipping Date')
    preset_time = fields.Datetime(string='Hour', help="Hour of the day for the order")
    is_invoiced = fields.Boolean('Is Invoiced', compute='_compute_is_invoiced')
    is_tipped = fields.Boolean('Is this already tipped?', readonly=True)
    tip_amount = fields.Float(string='Tip Amount', digits=0, readonly=True)
    refund_orders_count = fields.Integer('Number of Refund Orders', compute='_compute_refund_related_fields', help="Number of orders where items from this order were refunded")
    refunded_order_id = fields.Many2one('pos.order', compute='_compute_refund_related_fields', help="Order from which items were refunded in this order")
    has_refundable_lines = fields.Boolean('Has Refundable Lines', compute='_compute_has_refundable_lines')
    ticket_code = fields.Char(help='5 digits alphanumeric code to be used by portal user to request an invoice')
    tracking_number = fields.Char(string="Order Number", readonly=True, copy=False)
    uuid = fields.Char(string='Uuid', readonly=True, default=lambda self: str(uuid4()), copy=False)
    email = fields.Char(string='Email', compute="_compute_contact_details", readonly=False, store=True)
    mobile = fields.Char(string='Mobile', compute="_compute_contact_details", readonly=False, store=True)
    is_edited = fields.Boolean(string='Edited', compute='_compute_is_edited')
    has_deleted_line = fields.Boolean(string='Has Deleted Line')
    order_edit_tracking = fields.Boolean(related="config_id.order_edit_tracking", readonly=True)
    available_payment_method_ids = fields.Many2many('pos.payment.method', related='config_id.payment_method_ids', string='Available Payment Methods', readonly=True, store=False)
    invoice_status = fields.Selection([
        ('invoiced', 'Fully Invoiced'),
        ('to_invoice', 'To Invoice'),
    ], string='Invoice Status', compute='_compute_invoice_status')

    @api.depends('account_move')
    def _compute_invoice_status(self):
        for order in self:
            order.invoice_status = 'invoiced' if len(order.account_move) else 'to_invoice'

    @api.depends('session_id')
    def _compute_order_config_id(self):
        for order in self:
            if order.session_id:
                order.config_id = order.session_id.config_id

    @api.depends('lines.refund_orderline_ids', 'lines.refunded_orderline_id')
    def _compute_refund_related_fields(self):
        for order in self:
            order.refund_orders_count = len(order.mapped('lines.refund_orderline_ids.order_id'))
            order.refunded_order_id = order.lines.refunded_orderline_id.order_id

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
            order.currency_rate = self.env['res.currency']._get_conversion_rate(order.company_id.currency_id, order.currency_id, order.company_id, order.date_order.date())

    @api.depends('lines.is_total_cost_computed')
    def _compute_is_total_cost_computed(self):
        for order in self:
            order.is_total_cost_computed = not False in order.lines.mapped('is_total_cost_computed')

    @api.depends('partner_id')
    def _compute_contact_details(self):
        for order in self:
            order.email = order.partner_id.email or ""
            order.mobile = order._phone_format(number=order.partner_id.mobile or order.partner_id.phone or "",
                        country=order.partner_id.country_id)

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
                order.margin_percent = not float_is_zero(amount_untaxed, precision_rounding=order.currency_id.rounding) and order.margin / amount_untaxed or 0
            else:
                order.margin = 0
                order.margin_percent = 0

    @api.onchange('payment_ids', 'lines')
    def _onchange_amount_all(self):
        self._compute_prices()

    def _compute_prices(self):
        AccountTax = self.env['account.tax']
        for order in self:
            if not order.currency_id:
                raise UserError(_("You can't: create a pos order from the backend interface, or unset the pricelist, or create a pos.order in a python test with Form tool, or edit the form view in studio if no PoS order exist"))
            order.amount_paid = sum(payment.amount for payment in order.payment_ids)
            order.amount_return = -sum(payment.amount < 0 and payment.amount or 0 for payment in order.payment_ids)

            base_lines = order.lines._prepare_tax_base_line_values()
            AccountTax._add_tax_details_in_base_lines(base_lines, order.company_id)
            AccountTax._round_base_lines_tax_details(base_lines, order.company_id)

            cash_rounding = None
            if (
                order.config_id.cash_rounding
                and not order.config_id.only_round_cash_method
                and order.config_id.rounding_method
            ):
                cash_rounding = order.config_id.rounding_method

            tax_totals = AccountTax._get_tax_totals_summary(
                base_lines=base_lines,
                currency=order.currency_id,
                company=order.company_id,
                cash_rounding=cash_rounding,
            )
            refund_factor = -1 if (order.amount_total < 0.0) else 1
            order.amount_tax = refund_factor * tax_totals['tax_amount_currency']
            order.amount_total = refund_factor * tax_totals['total_amount_currency']
            order.amount_difference = order.amount_paid - order.amount_total

    @api.depends('lines.is_edited', 'has_deleted_line')
    def _compute_is_edited(self):
        for order in self:
            order.is_edited = any(order.lines.mapped('is_edited')) or order.has_deleted_line

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.pricelist_id = self.partner_id.property_product_pricelist.id

    @api.ondelete(at_uninstall=False)
    def _unlink_except_draft_or_cancel(self):
        if any(pos_order.state not in ['draft', 'cancel'] for pos_order in self):
            raise UserError(_('In order to delete a sale, it must be new or cancelled.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            session = self.env['pos.session'].browse(vals['session_id'])
            vals = self._complete_values_from_session(session, vals)
        return super().create(vals_list)

    @api.model
    def _complete_values_from_session(self, session, values):
        if values.get('state') and values['state'] == 'paid' and not values.get('name'):
            values['name'] = self._compute_order_name(session)
        values.setdefault('pricelist_id', session.config_id.pricelist_id.id)
        values.setdefault('fiscal_position_id', session.config_id.default_fiscal_position_id.id)
        values.setdefault('company_id', session.config_id.company_id.id)
        if values.get('tracking_number') is None and values.get('pos_reference') is None and values.get('sequence_number') is None:
            pos_reference, sequence_number, tracking_number = session.get_next_order_refs()
            values['pos_reference'] = pos_reference
            values['sequence_number'] = sequence_number
            values['tracking_number'] = tracking_number
        return values

    def write(self, vals):
        for order in self:
            if vals.get('state') and vals['state'] == 'paid' and order.name == '/':
                session = self.env['pos.session'].browse(vals['session_id']) if not self.session_id and vals.get('session_id') else False
                vals['name'] = self._compute_order_name(session)
            if vals.get('mobile'):
                vals['mobile'] = order._phone_format(number=vals.get('mobile'),
                        country=order.partner_id.country_id or self.env.company.country_id)
            if vals.get('has_deleted_line') is not None and self.has_deleted_line:
                del vals['has_deleted_line']

        list_line = self._create_pm_change_log(vals)
        res = super().write(vals)
        for order in self:
            if vals.get('payment_ids'):
                order._compute_prices()
                totally_paid_or_more = float_compare(order.amount_paid, order.amount_total, precision_rounding=order.currency_id.rounding)
                if totally_paid_or_more < 0 and order.state in ['paid', 'done', 'invoiced']:
                    raise UserError(_('The paid amount is different from the total amount of the order.'))
                elif totally_paid_or_more > 0 and order.state == 'paid':
                    list_line.append(_("Warning, the paid amount is higher than the total amount. (Difference: %s)", formatLang(self.env, order.amount_paid - order.amount_total, currency_obj=order.currency_id)))
                if order.nb_print > 0 and vals.get('payment_ids'):
                    raise UserError(_('You cannot change the payment of a printed order.'))

        if len(list_line) > 0:
            body = _("Payment changes:")
            body += self._markup_list_message(list_line)
            for order in self:
                if vals.get('payment_ids'):
                    order.message_post(body=body)

        return res

    def _create_pm_change_log(self, vals):
        if not vals.get('payment_ids'):
            return []

        message_list = []
        new_pms = vals.get('payment_ids', [])
        for new_pm in new_pms:
            orm_command = new_pm[0]

            if orm_command == 0:
                payment_method_id = self.env['pos.payment.method'].browse(new_pm[2].get('payment_method_id'))
                amount = formatLang(self.env, new_pm[2].get('amount'), currency_obj=self.currency_id)
                message_list.append(_("Added %(payment_method)s with %(amount)s",
                    payment_method=payment_method_id.name,
                    amount=amount))
            elif orm_command == 1:
                pm_id = self.env['pos.payment'].browse(new_pm[1])
                old_pm = pm_id.payment_method_id.name
                old_amount = formatLang(self.env, pm_id.amount, currency_obj=pm_id.currency_id)
                new_amount = False
                new_payment_method = False

                if new_pm[2].get('payment_method_id'):
                    new_payment_method = self.env['pos.payment.method'].browse(new_pm[2].get('payment_method_id'))
                if new_pm[2].get('amount'):
                    new_amount = formatLang(self.env, new_pm[2].get('amount'), currency_obj=pm_id.currency_id)

                if new_payment_method and new_amount:
                    message_list.append(_("%(old_pm)s changed to %(new_pm)s and from %(old_amount)s to %(new_amount)s",
                        old_pm=old_pm,
                        new_pm=new_payment_method.name,
                        old_amount=old_amount,
                        new_amount=new_amount))
                elif new_payment_method:
                    message_list.append(_("%(old_pm)s changed to %(new_pm)s for %(old_amount)s",
                        old_pm=old_pm,
                        new_pm=new_payment_method.name,
                        old_amount=old_amount))
                elif new_amount:
                    message_list.append(_("Amount for %(old_pm)s changed from %(old_amount)s to %(new_amount)s",
                        old_amount=old_amount,
                        new_amount=new_amount,
                        old_pm=old_pm))
            elif orm_command == 2:
                pm_id = self.env['pos.payment'].browse(new_pm[1])
                amount = formatLang(self.env, pm_id.amount, currency_obj=pm_id.currency_id)
                message_list.append(_("Removed %(payment_method)s with %(amount)s",
                    payment_method=pm_id.payment_method_id.name,
                    amount=amount))

        return message_list

    def _markup_list_message(self, message):
        body = Markup("<ul>")
        for line in message:
            body += Markup("<li>")
            body += line
            body += Markup("</li>")
        body += Markup("</ul>")
        return body

    def _compute_order_name(self, session=None):
        session = session or self.session_id
        if self.refunded_order_id.exists():
            return _('%(refunded_order)s REFUND', refunded_order=self.refunded_order_id.name)
        else:
            return session.config_id.sequence_id._next()

    def action_stock_picking(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('stock.action_picking_tree_ready')
        action['display_name'] = _('Pickings')
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

    # the refunded order is the order from which the items were refunded in this order
    def action_view_refunded_order(self):
        return {
            'name': _('Refunded Order'),
            'view_mode': 'form',
            'view_id': self.env.ref('point_of_sale.view_pos_pos_form').id,
            'res_model': 'pos.order',
            'type': 'ir.actions.act_window',
            'res_id': self.refunded_order_id.id,
        }

    # the refund orders are the orders where the items from this order were refunded
    def action_view_refund_orders(self):
        return {
            'name': _('Refund Orders'),
            'view_mode': 'list,form',
            'res_model': 'pos.order',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.mapped('lines.refund_orderline_ids.order_id').ids)],
        }

    def _is_pos_order_paid(self):
        amount_total = self.amount_total
        # If we are checking if a refund was paid and if it was a total refund, we take into account the amount paid on
        # the original order. For a pertial refund, we take into account the value of the items returned.
        if float_is_zero(self.refunded_order_id.amount_total + amount_total, precision_rounding=self.currency_id.rounding):
            amount_total = -self.refunded_order_id.amount_paid
        return float_is_zero(self._get_rounded_amount(amount_total) - self.amount_paid, precision_rounding=self.currency_id.rounding)

    def _get_rounded_amount(self, amount, force_round=False):
        # TODO: add support for mix of cash and non-cash payments when both cash_rounding and only_round_cash_method are True
        if self.config_id.cash_rounding \
           and (force_round or (not self.config_id.only_round_cash_method \
           or any(p.payment_method_id.is_cash_count for p in self.payment_ids))):
            amount = float_round(amount, precision_rounding=self.config_id.rounding_method.rounding, rounding_method=self.config_id.rounding_method.rounding_method)
        currency = self.currency_id
        return currency.round(amount) if currency else amount

    def _get_partner_bank_id(self):
        bank_partner_id = False
        if self.amount_total <= 0 and self.partner_id.bank_ids:
            bank_partner_id = self.partner_id.bank_ids[0].id
        elif self.amount_total >= 0 and self.company_id.partner_id.bank_ids:
            bank_partner_id = self.company_id.partner_id.bank_ids[0].id
        return bank_partner_id

    def _create_invoice(self, move_vals):
        self.ensure_one()
        invoice = self.env['account.move'].sudo()\
            .with_company(self.company_id)\
            .with_context(default_move_type=move_vals['move_type'], linked_to_pos=True)\
            .create(move_vals)

        if self.config_id.cash_rounding:
            line_ids_commands = []
            rate = invoice.invoice_currency_rate
            sign = invoice.direction_sign
            amount_paid = (-1 if self.amount_total < 0.0 else 1) * self.amount_paid
            difference_currency = sign * (amount_paid - invoice.amount_total)
            difference_balance = invoice.company_currency_id.round(difference_currency / rate) if rate else 0.0
            if not self.currency_id.is_zero(difference_currency):
                rounding_line = invoice.line_ids.filtered(lambda line: line.display_type == 'rounding' and not line.tax_line_id)
                if rounding_line:
                    line_ids_commands.append(Command.update(rounding_line.id, {
                        'amount_currency': rounding_line.amount_currency + difference_currency,
                        'balance': rounding_line.balance + difference_balance,
                    }))
                else:
                    if difference_currency > 0.0:
                        account = invoice.invoice_cash_rounding_id.loss_account_id
                    else:
                        account = invoice.invoice_cash_rounding_id.profit_account_id
                    line_ids_commands.append(Command.create({
                        'name': invoice.invoice_cash_rounding_id.name,
                        'amount_currency': difference_currency,
                        'balance': difference_balance,
                        'currency_id': invoice.currency_id.id,
                        'display_type': 'rounding',
                        'account_id': account.id,
                    }))
                existing_terms_line = invoice.line_ids\
                    .filtered(lambda line: line.display_type == 'payment_term')\
                    .sorted(lambda line: -abs(line.amount_currency))[:1]
                line_ids_commands.append(Command.update(existing_terms_line.id, {
                    'amount_currency': existing_terms_line.amount_currency - difference_currency,
                    'balance': existing_terms_line.balance - difference_balance,
                }))
                with self.env['account.move']._check_balanced({'records': invoice}):
                    invoice.with_context(skip_invoice_sync=True).line_ids = line_ids_commands
        invoice.message_post(body=_("This invoice has been created from the point of sale session: %s", self._get_html_link()))
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
        timezone = pytz.timezone(self._context.get('tz') or self.env.user.tz or 'UTC')
        invoice_date = fields.Datetime.now() if self.session_id.state == 'closed' else self.date_order
        pos_refunded_invoice_ids = []
        for orderline in self.lines:
            if orderline.refunded_orderline_id and orderline.refunded_orderline_id.order_id.account_move:
                pos_refunded_invoice_ids.append(orderline.refunded_orderline_id.order_id.account_move.id)

        vals = {
            'invoice_origin': self.name,
            'pos_refunded_invoice_ids': pos_refunded_invoice_ids,
            'journal_id': self.session_id.config_id.invoice_journal_id.id,
            'move_type': 'out_invoice' if self.amount_total >= 0 else 'out_refund',
            'ref': self.name,
            'partner_id': self.partner_id.address_get(['invoice'])['invoice'],
            'partner_bank_id': self._get_partner_bank_id(),
            'currency_id': self.currency_id.id,
            'invoice_user_id': self.user_id.id,
            'invoice_date': invoice_date.astimezone(timezone).date(),
            'fiscal_position_id': self.fiscal_position_id.id,
            'invoice_line_ids': self._prepare_invoice_lines(),
            'invoice_payment_term_id': self.partner_id.property_payment_term_id.id or False,
            'invoice_cash_rounding_id': self.config_id.rounding_method.id,
        }
        if self.refunded_order_id.account_move:
            vals['ref'] = _('Reversal of: %s', self.refunded_order_id.account_move.name)
            vals['reversed_entry_id'] = self.refunded_order_id.account_move.id
        if self.floating_order_name:
            vals.update({'narration': self.floating_order_name})
        return vals

    def _prepare_aml_values_list_per_nature(self):
        self.ensure_one()
        AccountTax = self.env['account.tax']
        sign = 1 if self.amount_total < 0 else -1
        commercial_partner = self.partner_id.commercial_partner_id
        company_currency = self.company_id.currency_id
        rate = self.currency_id._get_conversion_rate(self.currency_id, company_currency, self.company_id, self.date_order)

        # Concert each order line to a dictionary containing business values. Also, prepare for taxes computation.
        base_lines = self._prepare_tax_base_line_values()
        AccountTax._add_tax_details_in_base_lines(base_lines, self.company_id)
        AccountTax._round_base_lines_tax_details(base_lines, self.company_id)
        AccountTax._add_accounting_data_in_base_lines_tax_details(base_lines, self.company_id)
        tax_results = AccountTax._prepare_tax_lines(base_lines, self.company_id)

        total_balance = 0.0
        total_amount_currency = 0.0
        aml_vals_list_per_nature = defaultdict(list)

        # Create the tax lines
        for tax_line in tax_results['tax_lines_to_add']:
            tax_rep = self.env['account.tax.repartition.line'].browse(tax_line['tax_repartition_line_id'])
            aml_vals_list_per_nature['tax'].append({
                **tax_line,
                'tax_tag_invert': tax_rep.document_type == 'invoice',
            })
            total_amount_currency += tax_line['amount_currency']
            total_balance += tax_line['balance']

        # Create the aml values for order lines.
        for base_line_vals, update_base_line_vals in tax_results['base_lines_to_update']:
            order_line = base_line_vals['record']
            amount_currency = update_base_line_vals['amount_currency']
            balance = company_currency.round(amount_currency * rate)
            aml_vals_list_per_nature['product'].append({
                'name': order_line.full_product_name,
                'product_id': order_line.product_id.id,
                'quantity': order_line.qty * sign,
                'account_id': base_line_vals['account_id'].id,
                'partner_id': base_line_vals['partner_id'].id,
                'currency_id': base_line_vals['currency_id'].id,
                'tax_ids': [(6, 0, base_line_vals['tax_ids'].ids)],
                'tax_tag_ids': update_base_line_vals['tax_tag_ids'],
                'amount_currency': amount_currency,
                'balance': balance,
                'tax_tag_invert': not base_line_vals['is_refund'],
            })
            total_amount_currency += amount_currency
            total_balance += balance

        # Cash rounding.
        cash_rounding = self.config_id.rounding_method
        if self.config_id.cash_rounding and cash_rounding and (not self.config_id.only_round_cash_method or any(p.payment_method_id.is_cash_count for p in self.payment_ids)):
            amount_currency = cash_rounding.compute_difference(self.currency_id, total_amount_currency)
            if not self.currency_id.is_zero(amount_currency):
                balance = company_currency.round(amount_currency * rate)

                if cash_rounding.strategy == 'biggest_tax':
                    biggest_tax_aml_vals = None
                    for aml_vals in aml_vals_list_per_nature['tax']:
                        if not biggest_tax_aml_vals or float_compare(-sign * aml_vals['amount_currency'], -sign * biggest_tax_aml_vals['amount_currency'], precision_rounding=self.currency_id.rounding) > 0:
                            biggest_tax_aml_vals = aml_vals
                    if biggest_tax_aml_vals:
                        biggest_tax_aml_vals['amount_currency'] += amount_currency
                        biggest_tax_aml_vals['balance'] += balance
                elif cash_rounding.strategy == 'add_invoice_line':
                    if -sign * amount_currency > 0.0 and cash_rounding.loss_account_id:
                        account_id = cash_rounding.loss_account_id.id
                    else:
                        account_id = cash_rounding.profit_account_id.id
                    aml_vals_list_per_nature['cash_rounding'].append({
                        'name': cash_rounding.name,
                        'account_id': account_id,
                        'partner_id': commercial_partner.id,
                        'currency_id': self.currency_id.id,
                        'amount_currency': amount_currency,
                        'balance': balance,
                        'display_type': 'rounding',
                    })

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

        # sort self.payment_ids by is_split_transaction:
        for payment_id in self.payment_ids:
            is_split_transaction = payment_id.payment_method_id.split_transactions
            if is_split_transaction:
                reversed_move_receivable_account_id = self.partner_id.property_account_receivable_id
            else:
                reversed_move_receivable_account_id = payment_id.payment_method_id.receivable_account_id or self.company_id.account_default_pos_receivable_account_id

            aml_vals_entry_found = [aml_entry for aml_entry in aml_vals_list_per_nature['payment_terms']
                                    if aml_entry['account_id'] == reversed_move_receivable_account_id.id
                                    and not aml_entry['partner_id']]

            if aml_vals_entry_found and not is_split_transaction:
                aml_vals_entry_found[0]['amount_currency'] += self.session_id._amount_converter(payment_id.amount, self.date_order, False)
                aml_vals_entry_found[0]['balance'] += payment_id.amount
            else:
                aml_vals_list_per_nature['payment_terms'].append({
                    'partner_id': commercial_partner.id if is_split_transaction else False,
                    'name': f"{reversed_move_receivable_account_id.code} {reversed_move_receivable_account_id.code}",
                    'account_id': reversed_move_receivable_account_id.id,
                    'currency_id': self.currency_id.id,
                    'amount_currency': payment_id.amount,
                    'balance': self.session_id._amount_converter(payment_id.amount, self.date_order, False),
                })

        return aml_vals_list_per_nature

    def _create_misc_reversal_move(self, payment_moves):
        """ Create a misc move to reverse this POS order and "remove" it from the POS closing entry.
        This is done by taking data from the order and using it to somewhat replicate the resulting entry in order to
        reverse partially the movements done ine the POS closing entry.
        """
        aml_values_list_per_nature = self._prepare_aml_values_list_per_nature()
        move_lines = []
        for aml_values_list in aml_values_list_per_nature.values():
            for aml_values in aml_values_list:
                aml_values['balance'] = -aml_values['balance']
                aml_values['amount_currency'] = -aml_values['amount_currency']
                move_lines.append(aml_values)

        # Make a move with all the lines.
        reversal_entry = self.env['account.move'].with_context(
            default_journal_id=self.config_id.journal_id.id,
            skip_invoice_sync=True,
            skip_invoice_line_sync=True,
        ).create({
            'journal_id': self.config_id.journal_id.id,
            'date': fields.Date.context_today(self),
            'ref': _('Reversal of POS closing entry %(entry)s for order %(order)s from session %(session)s', entry=self.session_move_id.name, order=self.name, session=self.session_id.name),
            'line_ids': [(0, 0, aml_value) for aml_value in move_lines],
            'reversed_pos_order_id': self.id
        })
        reversal_entry.action_post()

        pos_account_receivable = self.company_id.account_default_pos_receivable_account_id
        account_receivable = self.payment_ids.payment_method_id.receivable_account_id
        reversal_entry_receivable = reversal_entry.line_ids.filtered(lambda l: l.account_id in (pos_account_receivable + account_receivable))
        payment_receivable = payment_moves.line_ids.filtered(lambda l: l.account_id in (pos_account_receivable + account_receivable))
        lines_to_reconcile = defaultdict(lambda: self.env['account.move.line'])
        for line in (reversal_entry_receivable | payment_receivable):
            lines_to_reconcile[line.account_id] |= line
        for line in lines_to_reconcile.values():
            line.filtered(lambda l: not l.reconciled).reconcile()

    def action_pos_order_invoice(self):
        if len(self.company_id) > 1:
            raise UserError(_("You cannot invoice orders belonging to different companies."))
        self.write({'to_invoice': True})
        if self.company_id.anglo_saxon_accounting and self.session_id.update_stock_at_closing and self.session_id.state != 'closed':
            self._create_order_picking()
        return self._generate_pos_order_invoice()

    def _generate_pos_order_invoice(self):
        moves = self.env['account.move']

        for order in self:
            # Force company for all SUPERUSER_ID action
            if order.account_move:
                moves += order.account_move
                continue

            if not order.partner_id:
                raise UserError(_('Please provide a partner for the sale.'))

            move_vals = order._prepare_invoice_vals()
            new_move = order._create_invoice(move_vals)

            order.write({'account_move': new_move.id, 'state': 'invoiced'})
            new_move.sudo().with_company(order.company_id).with_context(skip_invoice_sync=True)._post()

            moves += new_move
            payment_moves = order._apply_invoice_payments(order.session_id.state == 'closed')

            # Send and Print
            if self.env.context.get('generate_pdf', True):
                new_move.with_context(skip_invoice_sync=True)._generate_and_send()

            if order.session_id.state == 'closed':  # If the session isn't closed this isn't needed.
                # If a client requires the invoice later, we need to revers the amount from the closing entry, by making a new entry for that.
                order._create_misc_reversal_move(payment_moves)

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

    def action_pos_order_cancel(self):
        if self.env.context.get('active_ids'):
            orders = self.browse(self.env.context.get('active_ids'))
            order_is_in_futur = any(order.preset_time and order.preset_time.date() > fields.Date.today() for order in orders)
            if order_is_in_futur:
                raise UserError(_('The order delivery / pickup date is in the future. You cannot cancel it.'))

        today_orders = self.filtered(lambda order: order.state == 'draft' and (not order.preset_time or order.preset_time.date() == fields.Date.today()))
        next_days_orders = self.filtered(lambda order: order.preset_time and order.preset_time.date() > fields.Date.today() and order.state == 'draft')
        next_days_orders.session_id = False
        today_orders.write({'state': 'cancel'})

    def _apply_invoice_payments(self, is_reverse=False):
        receivable_account = self.env["res.partner"]._find_accounting_partner(self.partner_id).with_company(self.company_id).property_account_receivable_id
        payment_moves = self.payment_ids.sudo().with_company(self.company_id)._create_payment_moves(is_reverse)
        if receivable_account.reconcile:
            invoice_receivables = self.account_move.line_ids.filtered(lambda line: line.account_id == receivable_account and not line.reconciled)
            if invoice_receivables:
                payment_receivables = payment_moves.mapped('line_ids').filtered(lambda line: line.account_id == receivable_account and line.partner_id)
                (invoice_receivables | payment_receivables).sudo().with_company(self.company_id).reconcile()
        return payment_moves

    @api.model
    def sync_from_ui(self, orders):
        """ Create and update Orders from the frontend PoS application.

        Create new orders and update orders that are in draft status. If an order already exists with a status
        different from 'draft' it will be discarded, otherwise it will be saved to the database. If saved with
        'draft' status the order can be overwritten later by this function.

        :param orders: dictionary with the orders to be created.
        :type orders: dict.
        :param draft: Indicate if the orders are meant to be finalized or temporarily saved.
        :type draft: bool.
        :Returns: list -- list of db-ids for the created and updated orders.
        """
        order_ids = []
        session_ids = set({order.get('session_id') for order in orders})
        for order in orders:
            if len(self._get_refunded_orders(order)) > 1:
                raise ValidationError(_('You can only refund products from the same order.'))

            existing_order = self.env['pos.order'].search([('uuid', '=', order.get('uuid'))])
            if existing_order and existing_order.state == 'draft':
                order_ids.append(self._process_order(order, existing_order))
            elif not existing_order:
                order_ids.append(self._process_order(order, False))

        # Sometime pos_orders_ids can be empty.
        pos_order_ids = self.env['pos.order'].browse(order_ids)
        config_id = pos_order_ids.config_id.ids[0] if pos_order_ids else False

        for order in pos_order_ids:
            order._ensure_access_token()

        # If the previous session is closed, the order will get a new session_id due to _get_valid_session in _process_order
        is_new_session = any(order.get('session_id') not in session_ids for order in orders)
        return {
            'pos.order': pos_order_ids.read(pos_order_ids._load_pos_data_fields(config_id), load=False) if config_id else [],
            'pos.session': pos_order_ids.session_id._load_pos_data({}) if config_id and is_new_session else [],
            'pos.payment': pos_order_ids.payment_ids.read(pos_order_ids.payment_ids._load_pos_data_fields(config_id), load=False) if config_id else [],
            'pos.order.line': pos_order_ids.lines.read(pos_order_ids.lines._load_pos_data_fields(config_id), load=False) if config_id else [],
            'pos.pack.operation.lot': pos_order_ids.lines.pack_lot_ids.read(pos_order_ids.lines.pack_lot_ids._load_pos_data_fields(config_id), load=False) if config_id else [],
            "product.attribute.custom.value": pos_order_ids.lines.custom_attribute_value_ids.read(pos_order_ids.lines.custom_attribute_value_ids._load_pos_data_fields(config_id), load=False) if config_id else [],
        }

    @api.model
    def _get_refunded_orders(self, order):
        refunded_orderline_ids = [line[2]['refunded_orderline_id'] for line in order['lines'] if line[0] in [0, 1] and line[2].get('refunded_orderline_id')]
        return self.env['pos.order.line'].browse(refunded_orderline_ids).mapped('order_id')

    def _should_create_picking_real_time(self):
        return not self.session_id.update_stock_at_closing or (self.company_id.anglo_saxon_accounting and self.to_invoice)

    def _create_order_picking(self):
        self.ensure_one()
        if self.shipping_date:
            self.sudo().lines._launch_stock_rule_from_pos_order_lines()
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
            'name': _('%(name)s REFUND', name=self.name),
            'session_id': current_session.id,
            'date_order': fields.Datetime.now(),
            'pos_reference': self.pos_reference,
            'lines': False,
            'amount_tax': -self.amount_tax,
            'amount_total': -self.amount_total,
            'amount_paid': 0,
            'is_total_cost_computed': False
        }

    def _prepare_mail_values(self, email, ticket, basic_ticket):
        message = Markup(
            _("<p>Dear %(client_name)s,<br/>Here is your Receipt %(is_invoiced)sfor \
            %(pos_name)s amounting in %(amount)s from %(company_name)s. </p>")
        ) % {
            'client_name': self.partner_id.name or _('Customer'),
            'pos_name': self.name,
            'amount': self.currency_id.format(self.amount_total),
            'company_name': self.company_id.name,
            'is_invoiced': "and Invoice " if self.account_move else "",
        }

        return {
            'subject': _('Receipt %s', self.name),
            'body_html': message,
            'author_id': self.env.user.partner_id.id,
            'email_from': self.env.company.email or self.env.user.email_formatted,
            'email_to': email,
            'attachment_ids': self._add_mail_attachment(self.name, ticket, basic_ticket),
        }

    def _refund(self):
        """ Create a copy of order to refund them.

        return The newly created refund orders.
        """
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
                PosPackOperationLot = self.env['pos.pack.operation.lot']
                for pack_lot in line.pack_lot_ids:
                    PosPackOperationLot += pack_lot.copy()
                line.copy(line._prepare_refund_data(refund_order, PosPackOperationLot))
            refund_orders |= refund_order
        return refund_orders

    def refund(self):
        return {
            'name': _('Return Products'),
            'view_mode': 'form',
            'res_model': 'pos.order',
            'res_id': self._refund().ids[0],
            'view_id': False,
            'context': self.env.context,
            'type': 'ir.actions.act_window',
            'target': 'current',
        }

    def action_send_mail(self):
        template = self.env['mail.template'].search([('model', '=', self._name)], limit=1)
        return {
            'name': _('Send Email'),
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'type': 'ir.actions.act_window',
            'context': {
                'default_composition_mode': 'mass_mail',
                'default_res_ids': self.ids,
                'default_template_id': template.id,
            },
            'target': 'new'
        }

    def _add_mail_attachment(self, name, ticket, basic_ticket):
        attachment = []
        filename = 'Receipt-' + name + '.jpg'
        receipt = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': ticket,
            'res_model': 'pos.order',
            'res_id': self.ids[0],
            'mimetype': 'image/jpeg',
        })
        attachment += [(4, receipt.id)]
        if basic_ticket:
            filename = 'Receipt-' + name + '-1' + '.jpg'
            basic_receipt = self.env['ir.attachment'].create({
                'name': filename,
                'type': 'binary',
                'datas': basic_ticket,
                'res_model': 'pos.order',
                'res_id': self.ids[0],
                'mimetype': 'image/jpeg',
            })
            attachment += [(4, basic_receipt.id)]


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

    def action_send_receipt(self, email, ticket_image, basic_image):
        self.env['mail.mail'].sudo().create(self._prepare_mail_values(email, ticket_image, basic_image)).send()
        self.email = email

    @api.model
    def remove_from_ui(self, server_ids):
        """ Remove orders from the frontend PoS application

        Remove orders from the server by id.
        :param server_ids: list of the id's of orders to remove from the server.
        :type server_ids: list.
        :returns: list -- list of db-ids for the removed orders.
        """
        orders = self.search([('id', 'in', server_ids), ('state', '=', 'draft')])
        orders.write({'state': 'cancel'})
        # TODO Looks like delete cascade is a better solution.
        orders.mapped('payment_ids').sudo().unlink()
        orders.sudo().unlink()
        return orders.ids

    @api.model
    def search_paid_order_ids(self, config_id, domain, limit, offset):
        """Search for 'paid' orders that satisfy the given domain, limit and offset."""
        default_domain = [('state', '!=', 'draft'), ('state', '!=', 'cancel')]
        if domain == []:
            real_domain = AND([[['config_id', '=', config_id]], default_domain])
        else:
            real_domain = AND([domain, default_domain])
        orders = self.search(real_domain, limit=limit, offset=offset, order='create_date desc')
        # We clean here the orders that does not have the same currency.
        # As we cannot use currency_id in the domain (because it is not a stored field),
        # we must do it after the search.
        pos_config = self.env['pos.config'].browse(config_id)
        orders = orders.filtered(lambda order: order.currency_id == pos_config.currency_id)
        orderlines = self.env['pos.order.line'].search(['|', ('refunded_orderline_id.order_id', 'in', orders.ids), ('order_id', 'in', orders.ids)])

        # We will return to the frontend the ids and the date of their last modification
        # so that it can compare to the last time it fetched the orders and can ask to fetch
        # orders that are not up-to-date.
        # The date of their last modification is either the last time one of its orderline has changed,
        # or the last time a refunded orderline related to it has changed.
        orders_info = defaultdict(lambda: datetime.min)
        for orderline in orderlines:
            key_order = orderline.order_id.id if orderline.order_id in orders \
                            else orderline.refunded_orderline_id.order_id.id
            if orders_info[key_order] < orderline.write_date:
                orders_info[key_order] = orderline.write_date
        totalCount = self.search_count(real_domain)
        return {'ordersInfo': list(orders_info.items())[::-1], 'totalCount': totalCount}

    def _send_order(self):
        # This function is made to be overriden by pos_self_order_preparation_display
        pass

    def _prepare_pos_log(self, body):
        return body


class PosOrderLine(models.Model):
    _name = 'pos.order.line'
    _description = "Point of Sale Order Lines"
    _rec_name = "product_id"
    _inherit = ['pos.load.mixin']

    company_id = fields.Many2one('res.company', string='Company', related="order_id.company_id", store=True)
    name = fields.Char(string='Line No', required=True, copy=False)
    skip_change = fields.Boolean('Skip line when sending ticket to kitchen printers.')
    notice = fields.Char(string='Discount Notice')
    product_id = fields.Many2one('product.product', string='Product', domain=[('sale_ok', '=', True)], required=True, change_default=True)
    attribute_value_ids = fields.Many2many('product.template.attribute.value', string="Selected Attributes")
    custom_attribute_value_ids = fields.One2many(
        comodel_name='product.attribute.custom.value', inverse_name='pos_order_line_id',
        string="Custom Values",
        store=True, readonly=False)
    price_unit = fields.Float(string='Unit Price', digits=0)
    qty = fields.Float('Quantity', digits='Product Unit of Measure', default=1)
    price_subtotal = fields.Float(string='Tax Excl.', digits=0,
        readonly=True, required=True)
    price_subtotal_incl = fields.Float(string='Tax Incl.', digits=0,
        readonly=True, required=True)
    price_extra = fields.Float(string="Price extra")
    price_type = fields.Selection([
        ('original', 'Original'),
        ('manual', 'Manual'),
        ('automatic', 'Automatic'),
    ], string='Price Type', default='original')
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
    uuid = fields.Char(string='Uuid', readonly=True, default=lambda self: str(uuid4()), copy=False)
    note = fields.Char('Product Note')
    origin_order_id = fields.Many2one('pos.order', string='Origin Order', help='Tracks the original order from which this orderline was created.', readonly=True, ondelete="set null")

    combo_parent_id = fields.Many2one('pos.order.line', string='Combo Parent') # FIXME rename to parent_line_id
    combo_line_ids = fields.One2many('pos.order.line', 'combo_parent_id', string='Combo Lines') # FIXME rename to child_line_ids

    combo_item_id = fields.Many2one('product.combo.item', string='Combo Item')
    is_edited = fields.Boolean('Edited', default=False)

    @api.model
    def _load_pos_data_domain(self, data):
        return [('order_id', 'in', [order['id'] for order in data['pos.order']])]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return [
            'qty', 'attribute_value_ids', 'custom_attribute_value_ids', 'price_unit', 'skip_change', 'uuid', 'price_subtotal', 'price_subtotal_incl', 'order_id', 'origin_order_id', 'note', 'price_type',
            'product_id', 'discount', 'tax_ids', 'pack_lot_ids', 'customer_note', 'refunded_qty', 'price_extra', 'full_product_name', 'refunded_orderline_id', 'combo_parent_id', 'combo_line_ids', 'combo_item_id', 'refund_orderline_ids'
        ]

    @api.model
    def _is_field_accepted(self, field):
        return field in self._fields and not field in ['combo_parent_id', 'combo_line_ids']

    @api.depends('refund_orderline_ids')
    def _compute_refund_qty(self):
        for orderline in self:
            orderline.refunded_qty = -sum(orderline.mapped('refund_orderline_ids.qty'))

    def _prepare_refund_data(self, refund_order, PosPackOperationLot):
        """
        This prepares data for refund order line. Inheritance may inject more data here

        @param refund_order: the pre-created refund order
        @type refund_order: pos.order

        @param PosPackOperationLot: the pre-created Pack operation Lot
        @type PosPackOperationLot: pos.pack.operation.lot

        @return: dictionary of data which is for creating a refund order line from the original line
        @rtype: dict
        """
        self.ensure_one()
        return {
            'name': _('%(name)s REFUND', name=self.name),
            'qty': -(self.qty - self.refunded_qty),
            'order_id': refund_order.id,
            'price_subtotal': -self.price_subtotal,
            'price_subtotal_incl': -self.price_subtotal_incl,
            'pack_lot_ids': PosPackOperationLot,
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
        if self.order_id.config_id.order_edit_tracking and values.get('qty') is not None and values.get('qty') < self.qty:
            self.is_edited = True
            body = _("%(product_name)s: Ordered quantity: %(old_qty)s", product_name=self.full_product_name, old_qty=self.qty)
            body += Markup("&rarr;") + str(values.get('qty'))
            for line in self:
                line.order_id.message_post(body=line.order_id._prepare_pos_log(body))
        return super().write(values)

    @api.model
    def get_existing_lots(self, company_id, config_id, product_id):
        """
        Return the lots that are still available in the given company.
        The lot is available if its quantity in the corresponding stock_quant and pos stock location is > 0.
        """
        self.check_access('read')
        pos_config = self.env['pos.config'].browse(config_id)
        if not pos_config:
            raise UserError(_('No PoS configuration found'))

        src_loc = pos_config.picking_type_id.default_location_src_id
        src_loc_quants = self.sudo().env['stock.quant'].search([
            '|',
            ('company_id', '=', False),
            ('company_id', '=', company_id),
            ('product_id', '=', product_id),
            ('location_id', 'in', src_loc.child_internal_location_ids.ids),
        ])
        available_lots = src_loc_quants.\
            filtered(lambda q: float_compare(q.quantity, 0, precision_rounding=q.product_id.uom_id.rounding) > 0).\
            mapped('lot_id')

        return available_lots.read(['id', 'name'])

    @api.ondelete(at_uninstall=False)
    def _unlink_except_order_state(self):
        if self.filtered(lambda x: x.order_id.state not in ["draft", "cancel"]):
            raise UserError(_("You can only unlink PoS order lines that are related to orders in new or cancelled state."))

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
        taxes = tax_ids_after_fiscal_position.compute_all(price, self.order_id.currency_id, self.qty, product=self.product_id, partner=self.order_id.partner_id)
        return {
            'price_subtotal_incl': taxes['total_included'],
            'price_subtotal': taxes['total_excluded'],
        }

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            price = self.order_id.pricelist_id._get_product_price(
                self.product_id, self.qty or 1.0, currency=self.currency_id
            )
            self.tax_ids = self.product_id.taxes_id.filtered_domain(self.env['account.tax']._check_company_domain(self.company_id))
            tax_ids_after_fiscal_position = self.order_id.fiscal_position_id.map_tax(self.tax_ids)
            self.price_unit = self.env['account.tax']._fix_tax_included_price_company(price, self.tax_ids, tax_ids_after_fiscal_position, self.company_id)
            self._onchange_qty()

    @api.onchange('qty', 'discount', 'price_unit', 'tax_ids')
    def _onchange_qty(self):
        if self.product_id:
            price = self.price_unit * (1 - (self.discount or 0.0) / 100.0)
            self.price_subtotal = self.price_subtotal_incl = price * self.qty
            if (self.tax_ids):
                taxes = self.tax_ids.compute_all(price, self.order_id.currency_id, self.qty, product=self.product_id, partner=False)
                self.price_subtotal = taxes['total_excluded']
                self.price_subtotal_incl = taxes['total_included']

    @api.depends('order_id', 'order_id.fiscal_position_id')
    def _get_tax_ids_after_fiscal_position(self):
        for line in self:
            line.tax_ids_after_fiscal_position = line.order_id.fiscal_position_id.map_tax(line.tax_ids)

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
        coming from a sale order line. This method could be override in order to add other custom key that could
        be used in move/po creation.
        """
        self.ensure_one()
        # Use the delivery date if there is else use date_order and lead time
        if self.order_id.shipping_date:
            # get timezone from user
            # and convert to UTC to avoid any timezone issue
            # because shipping_date is date and date_planned is datetime
            from_zone = pytz.timezone(self._context.get('tz') or self.env.user.tz or 'UTC')
            shipping_date = fields.Datetime.to_datetime(self.order_id.shipping_date)
            shipping_date = from_zone.localize(shipping_date)
            date_deadline = shipping_date.astimezone(pytz.UTC).replace(tzinfo=None)
        else:
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
            if line.product_id.type != 'consu':
                continue

            group_id = line._get_procurement_group()
            if not group_id:
                group_id = self.env['procurement.group'].create(line._prepare_procurement_group_vals())
                line.order_id.with_context(backend_recomputation=True).write({'procurement_group_id': group_id})

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
                tracked_lines = order.lines.filtered(lambda l: l.product_id.tracking != 'none')
                lines_by_tracked_product = groupby(sorted(tracked_lines, key=lambda l: l.product_id.id), key=lambda l: l.product_id.id)
                pickings_to_confirm.action_confirm()
                for product_id, lines in lines_by_tracked_product:
                    lines = self.env['pos.order.line'].concat(*lines)
                    moves = pickings_to_confirm.move_ids.filtered(lambda m: m.product_id.id == product_id)
                    moves.move_line_ids.unlink()
                    moves._add_mls_related_to_order(lines, are_qties_done=False)
                    moves._recompute_state()
        return True

    def _is_product_storable_fifo_avco(self):
        self.ensure_one()
        return self.product_id.is_storable and self.product_id.cost_method in ['fifo', 'average']

    def _compute_total_cost(self, stock_moves):
        """
        Compute the total cost of the order lines.
        :param stock_moves: recordset of `stock.move`, used for fifo/avco lines
        """
        for line in self.filtered(lambda l: not l.is_total_cost_computed):
            product = line.product_id
            if line._is_product_storable_fifo_avco() and stock_moves:
                product_cost = product._compute_average_price(0, line.qty, line._get_stock_moves_to_consider(stock_moves, product))
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

    def _get_stock_moves_to_consider(self, stock_moves, product):
        self.ensure_one()
        return stock_moves.filtered(lambda ml: ml.product_id.id == product.id)

    @api.depends('price_subtotal', 'total_cost')
    def _compute_margin(self):
        for line in self:
            if line.product_id.type == 'combo':
                line.margin = 0
                line.margin_percent = 0
            else:
                line.margin = line.price_subtotal - line.total_cost
                line.margin_percent = not float_is_zero(line.price_subtotal, precision_rounding=line.currency_id.rounding) and line.margin / line.price_subtotal or 0

    def _prepare_tax_base_line_values(self):
        """ Convert pos order lines into dictionaries that would be used to compute taxes later.

        :param sign: An optional parameter to force the sign of amounts.
        :return: A list of python dictionaries (see '_prepare_base_line_for_taxes_computation' in account.tax).
        """
        base_line_vals_list = []
        for line in self:
            commercial_partner = self.order_id.partner_id.commercial_partner_id
            fiscal_position = self.order_id.fiscal_position_id
            line = line.with_company(self.order_id.company_id)
            account = line.product_id._get_product_accounts()['income'] or self.order_id.config_id.journal_id.default_account_id
            if not account:
                raise UserError(_(
                    "Please define income account for this product: '%(product)s' (id:%(id)d).",
                    product=line.product_id.name, id=line.product_id.id,
                ))

            if fiscal_position:
                account = fiscal_position.map_account(account)

            is_refund_order = line.order_id.amount_total < 0.0
            is_refund_line = line.qty * line.price_unit < 0

            product_name = line.product_id\
                .with_context(lang=line.order_id.partner_id.lang or self.env.user.lang)\
                .get_product_multiline_description_sale()

            base_line_vals_list.append(
                {
                    **self.env['account.tax']._prepare_base_line_for_taxes_computation(
                        line,
                        partner_id=commercial_partner,
                        currency_id=self.order_id.currency_id,
                        product_id=line.product_id,
                        tax_ids=line.tax_ids_after_fiscal_position,
                        price_unit=line.price_unit,
                        quantity=line.qty * (-1 if is_refund_order else 1),
                        discount=line.discount,
                        account_id=account,
                        is_refund=is_refund_line,
                        sign=1 if is_refund_order else -1,
                    ),
                    'uom_id': line.product_uom_id,
                    'name': product_name,
                }
            )
        return base_line_vals_list

    def unlink(self):
        for line in self:
            if line.order_id.config_id.order_edit_tracking:
                line.order_id.has_deleted_line = True
                body = _("%s: Deleted line", line.full_product_name)
                line.order_id.message_post(body=line.order_id._prepare_pos_log(body))
        res = super().unlink()
        return res

    def _get_discount_amount(self):
        self.ensure_one()
        original_price = self.tax_ids.compute_all(self.price_unit, self.currency_id, self.qty, product=self.product_id, partner=self.order_id.partner_id)['total_included']
        return original_price - self.price_subtotal_incl


class PosPackOperationLot(models.Model):
    _name = 'pos.pack.operation.lot'
    _description = "Specify product lot/serial number in pos order line"
    _rec_name = "lot_name"
    _inherit = ['pos.load.mixin']

    pos_order_line_id = fields.Many2one('pos.order.line')
    order_id = fields.Many2one('pos.order', related="pos_order_line_id.order_id", readonly=False)
    lot_name = fields.Char('Lot Name')
    product_id = fields.Many2one('product.product', related='pos_order_line_id.product_id', readonly=False)

    @api.model
    def _load_pos_data_domain(self, data):
        return [('pos_order_line_id', 'in', [line['id'] for line in data['pos.order.line']])]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['lot_name', 'pos_order_line_id']


class AccountCashRounding(models.Model):
    _name = 'account.cash.rounding'
    _inherit = ['account.cash.rounding', 'pos.load.mixin']

    @api.constrains('rounding', 'rounding_method', 'strategy')
    def _check_session_state(self):
        open_session = self.env['pos.session'].search([('config_id.rounding_method', 'in', self.ids), ('state', '!=', 'closed')], limit=1)
        if open_session:
            raise ValidationError(
                _("You are not allowed to change the cash rounding configuration while a pos session using it is already opened."))

    @api.model
    def _load_pos_data_domain(self, data):
        return [('id', '=', data['pos.config'][0]['rounding_method'])]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'name', 'rounding', 'rounding_method', 'strategy']
