# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from collections import defaultdict
from pprint import pformat
from random import randrange
from uuid import uuid4

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command, Domain
from odoo.tools import (
    float_compare,
    float_is_zero,
    float_repr,
    float_round,
    formatLang,
    frozendict,
)

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _name = 'pos.order'
    _inherit = ["portal.mixin", "pos.bus.mixin", "pos.order.receipt", "pos.load.mixin", "mail.thread"]
    _description = "Point of Sale Order"
    _order = "date_order desc, name desc, id desc"
    _mailing_enabled = True

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
            ('state', '=', 'opened'),
            ('config_id', '=', closed_session.config_id.id),
        ], limit=1)

        if open_session:
            _logger.warning('Using open session %s for uuid number %s', open_session.name, order['uuid'])
            return open_session

        raise UserError(_('No open session available. Please open a new session to capture the order.'))

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [('state', '=', 'draft'), ('config_id', '=', config.id)]

    @api.model
    def _process_order(self, order, existing_order):
        """Create or update an pos.order from a given dictionary.

        :param dict order: dictionary representing the order.
        :param existing_order: order to be updated or False.
        :type existing_order: pos.order.
        :returns: id of created/updated pos.order
        :rtype: int
        """
        draft = order.get('state') == 'draft'
        pos_session = self.env['pos.session'].browse(order['session_id'])
        if pos_session.state == 'closing_control' or pos_session.state == 'closed':
            pos_session = self._get_valid_session(order)
            order['session_id'] = pos_session.id

        if not order.get('source'):
            order['source'] = 'pos'

        if order.get('partner_id'):
            self.update_order_partner(order)

        if not order.get('company_id'):
            order['company_id'] = pos_session.config_id.company_id.id

        if self.env.context.get('current_order_uuid') and order['uuid'] == self.env.context['current_order_uuid']:
            # Prioritize the server date for the order that is currently being processed
            order['date_order'] = fields.Datetime.now()

        pos_order = False
        record_uuid_mapping = order.pop('relations_uuid_mapping', {})

        if not existing_order:
            pos_order = self.create({
                **{key: value for key, value in order.items() if key != 'name'},
            })
            pos_order = pos_order.with_company(pos_order.company_id)
        else:
            pos_order = existing_order

            # If the order is belonging to another session, it must be moved to the current session first
            if order.get('session_id') and order['session_id'] != pos_order.session_id.id:
                pos_order.write({'session_id': order['session_id']})

            self._update_lines(order, pos_order, ['lines', 'payment_ids'])
            del order['uuid']
            del order['access_token']
            if order.get('state') == 'paid':
                # The "paid" state will be assigned later by `_process_saved_order`
                order['state'] = pos_order.state
            pos_order.write(order)

        for model_name, mapping in record_uuid_mapping.items():
            owner_records = self.env[model_name].search([('uuid', 'in', mapping.keys())])
            for uuid, field_names in mapping.items():
                for name, uuids in field_names.items():
                    params = self.env[model_name]._fields[name]
                    if params.type in ['one2many', 'many2many']:
                        records = self.env[params.comodel_name].search([('uuid', 'in', uuids)])
                        owner_records.filtered(lambda r: r.uuid == uuid).write({name: [Command.link(r.id) for r in records]})
                    else:
                        record = self.env[params.comodel_name].search([('uuid', '=', uuids)])
                        owner_records.filtered(lambda r: r.uuid == uuid).write({name: record.id})

        self_comp = self.with_company(pos_order.company_id)
        self_comp._process_payment_lines(order, pos_order, pos_session, draft)
        return pos_order._process_saved_order(draft)

    def _process_saved_order(self, draft):
        self.ensure_one()
        if not draft and self.state != 'cancel':
            self._compute_prices()
            self.action_pos_order_paid()
            self._set_product_qty_available()
            self._compute_total_cost_in_real_time()

        self._generate_order_invoice()
        return self.id

    def _update_lines(self, order, pos_order, fields=[]):
        # Save lines and payments before to avoid exception if a line is deleted
        # when vals change the state to 'paid'
        for field in fields:
            if order.get(field):
                existing_ids = set(pos_order[field].ids)
                existing_line_ids = {line.uuid: line.id for line in pos_order[field]}
                for line in order[field]:
                    if len(line) < 3:
                        continue
                    line_vals = line[2]
                    if line[0] == Command.CREATE and line_vals.get('uuid') in existing_line_ids:
                        # If we try to create (line[0] == Command.CREATE) a line with a uuid that already
                        # exists on another line of the same order, we transform the creation
                        # into an update (line[0] = Command.UPDATE) of the existing line.
                        line[0] = Command.UPDATE
                        line[1] = existing_line_ids[line_vals.get('uuid')]
                pos_order.write({field: order[field]})
                added_ids = set(pos_order[field].ids) - existing_ids
                if added_ids:
                    _logger.info("Added %s %s to pos.order #%s", field, list(added_ids), pos_order.id)
                order[field] = []

    def _generate_order_invoice(self):
        self.ensure_one()
        has_paylater_pm = any(payment.payment_method_id.type == 'pay_later' for payment in self.payment_ids)
        if (self.to_invoice or has_paylater_pm) and self.state == 'paid' and self.config_id.journal_id and not self.is_singly_invoiced:
            self.to_invoice = True  # Ensure true if has_paylater_pm is true
            should_generate_pdf = self.env.context.get('generate_pdf') or self.config_id.use_download_invoice
            self.with_context(generate_pdf=should_generate_pdf)._generate_pos_order_invoice()
        elif not self.config_id.journal_id:
            _logger.warning('Trying to create an invoice without any journal configured')
            raise UserError(_('No invoice journal configured for this POS session.'))

    def update_order_partner(self, order):
        partner_id = self.env['res.partner'].browse(order['partner_id'])
        if not partner_id.exists():
            order.update({
                "partner_id": False,
                "to_invoice": False,
            })

    def process_saved_payments(self, order, existing_order):
        """This will process and save payment related changes by ensuring necessary updates are performed on UI"""
        # don't directly write the order - on continuing from feedback screen it syncs with wrong amounts
        if order.get('partner_id'):
            self.update_order_partner(order)
            existing_order.write({'partner_id': order.get('partner_id'), 'to_invoice': order.get('to_invoice', False)})
        # payments
        if order.get('payment_ids'):
            self._update_lines(order, existing_order, ['lines', 'payment_ids'])
            self._process_payment_lines(order, existing_order, existing_order.session_id, False)
        existing_order._generate_order_invoice()

    def _clean_payment_lines(self):
        self.ensure_one()
        self.payment_ids.unlink()

    def _compute_amount_paid(self):
        paid_payment_ids = self.payment_ids.filtered(lambda p: not p.payment_status or p.payment_status == "done")
        return sum(paid_payment_ids.mapped('amount'))

    def _process_payment_lines(self, pos_order, order, pos_session, draft):
        """Create account.bank.statement.lines from the dictionary given to the parent function.

        If the payment_line is an updated version of an existing one, the existing payment_line will first be
        removed before making a new one.
        """
        prec_acc = order.currency_id.decimal_places

        # Recompute amount paid because we don't trust the client
        order.write({'amount_paid': order._compute_amount_paid()})

        if not draft and not float_is_zero(pos_order['amount_return'], prec_acc):
            cash_payment_method = pos_session.payment_method_ids.filtered(lambda pm: pm.type == 'cash')[:1]
            if not cash_payment_method:
                raise UserError(_("No cash statement found for this session. Unable to record returned cash."))
            return_payment_vals = {
                'name': _('return'),
                'pos_order_id': order.id,
                'amount': pos_order['amount_return'],
                'payment_date': fields.Datetime.now(),
                'payment_method_id': cash_payment_method.id,
                'is_change': True,
            }
            order.add_payment(return_payment_vals)
            order._compute_prices()

    def _get_pos_anglo_saxon_price_unit(self, product, quantity):
        moves = self.mapped('picking_ids.move_ids')\
            .filtered(lambda m: m.is_valued and m.product_id.valuation == 'real_time' and m.product_id.id == product.id)\
            .sorted(lambda x: x.date)
        return moves._get_price_unit()

    name = fields.Char(string='Order Ref', required=True, readonly=True, copy=False, default='/')
    date_order = fields.Datetime(string='Date', readonly=True, index=True, default=fields.Datetime.now)
    user_id = fields.Many2one(
        comodel_name='res.users', string='Employee',
        help="Employee who uses the cash register.",
        default=lambda self: self.env.uid,
    )
    amount_difference = fields.Monetary(string='Difference', readonly=True)
    amount_tax = fields.Monetary(string='Taxes', readonly=True, required=True)
    amount_total = fields.Monetary(string='Total', readonly=True, required=True)
    amount_paid = fields.Monetary(string='Paid', required=True)
    amount_return = fields.Monetary(string='Returned', required=True, readonly=True)
    margin = fields.Monetary(string="Margin", compute='_compute_margin')
    margin_percent = fields.Float(string="Margin (%)", compute='_compute_margin', digits=(12, 4))
    is_total_cost_computed = fields.Boolean(compute='_compute_is_total_cost_computed',
        help="Allows to know if all the total cost of the order lines have already been computed")
    lines = fields.One2many('pos.order.line', 'order_id', string='Order Lines', copy=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, index=True)
    country_code = fields.Char(related='company_id.account_fiscal_country_id.code')
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist')
    partner_id = fields.Many2one('res.partner', string='Customer', change_default=True, index='btree_not_null')
    sequence_number = fields.Integer(string='Sequence Number', copy=False,
                                     help='A session-unique sequence number for the order. Negative if generated from the client')
    session_id = fields.Many2one('pos.session', string='Session', index=True, domain="[('state', '=', 'opened')]")
    config_id = fields.Many2one('pos.config', compute='_compute_order_config_id', string="Point of Sale", readonly=False, store=True, index=True)
    currency_id = fields.Many2one('res.currency', related='config_id.currency_id', string="Currency")
    currency_rate = fields.Float("Currency Rate", compute='_compute_currency_rate', compute_sudo=True, store=True, digits=0, readonly=True,
        help='The rate of the currency to the currency of rate applicable at the date of the order')

    is_refund = fields.Boolean(string='Is Refund', readonly=True, default=False)
    state = fields.Selection(
        [('draft', 'New'), ('cancel', 'Cancelled'), ('paid', 'Paid'), ('done', 'Posted')],
        'Status', readonly=True, copy=False, default='draft', index=True)

    account_move = fields.Many2one('account.move', string='Invoice', readonly=True, copy=False, index="btree_not_null")
    preset_id = fields.Many2one('pos.preset', string='Preset')
    floating_order_name = fields.Char(string='Order Name')
    general_customer_note = fields.Text(string='General Customer Note')
    internal_note = fields.Text(string='Internal Note')
    nb_print = fields.Integer(string='Number of Print', readonly=True, copy=False, default=0)
    print_history = fields.Json('Print History', copy=False)
    pos_reference = fields.Char(string='Receipt Number', readonly=True, copy=False, index=True)
    sale_journal = fields.Many2one('account.journal', related='session_id.config_id.journal_id', string='Sales Journal', store=True, readonly=True, ondelete='restrict')
    fiscal_position_id = fields.Many2one(
        comodel_name='account.fiscal.position', string='Fiscal Position',
        readonly=False,
    )
    payment_ids = fields.One2many('pos.payment', 'pos_order_id', string='Payments')
    to_invoice = fields.Boolean('To invoice', copy=False)
    preset_time = fields.Datetime(string='Hour', help="Hour of the day for the order")
    is_singly_invoiced = fields.Boolean('Is Singly Invoiced', compute='_compute_is_invoiced')
    is_globally_invoiced = fields.Boolean('Is Globally Invoiced', compute='_compute_is_invoiced')
    is_tipped = fields.Boolean('Is this already tipped?', readonly=True)
    tip_amount = fields.Monetary(string='Tip Amount', readonly=True)
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
    ], string='Invoice Status', compute='_compute_is_invoiced')
    reversed_move_ids = fields.One2many(
        'account.move',
        'reversed_pos_order_id',
        string="Reversal Journal Entries",
        help="List of journal entries created when this POS order was reversed and invoiced after session close.",
    )
    source = fields.Selection(string="Origin", selection=[('pos', 'Point of Sale')], default='pos')
    defer_invoice_pdf = fields.Boolean(string="Defer Invoice PDF Generation", index=True)

    prep_order_ids = fields.One2many('pos.prep.order', 'pos_order_id', string='Preparation orders')
    _unique_uuid = models.Constraint('unique (uuid)', 'An order with this uuid already exists')

    def ask_for_ticket_printing(self):
        self.config_id._notify("TICKET_PRINTING_REQUESTED", self.ids)

    def is_refund_or_negative(self):
        return self.is_refund or self.amount_total < 0

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
            order.refunded_order_id = next(iter(order.lines.refunded_orderline_id.order_id), False)

    @api.depends('lines.refunded_qty', 'lines.qty')
    def _compute_has_refundable_lines(self):
        digits = self.env['decimal.precision'].precision_get('Product Unit')
        for order in self:
            order.has_refundable_lines = any(float_compare(line.qty, line.refunded_qty, digits) > 0 for line in order.lines)

    @api.depends('account_move', 'session_id.move_ids')
    def _compute_is_invoiced(self):
        for order in self:
            order_move = order.account_move
            session_moves = order.session_id.move_ids
            order.is_singly_invoiced = order_move and order_move not in session_moves
            order.is_globally_invoiced = order_move and order_move in session_moves
            order.invoice_status = 'invoiced' if order.is_singly_invoiced else 'to_invoice'

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
            order.mobile = order._phone_format(number=order.partner_id.phone or "",
                        country=order.partner_id.country_id)

    def _compute_total_cost_in_real_time(self):
        """
        Compute the total cost of the order when it's processed by the server. It will compute the total cost of all the lines
        if it's possible. If a margin of one of the order's lines cannot be computed (because of session_id.update_stock_at_closing),
        then the margin of said order is not computed (it will be computed when closing the session).
        """
        for order in self:
            lines = order._get_total_cost_in_real_time_lines()
            lines._compute_total_cost()

    def _get_total_cost_in_real_time_lines(self):
        self.ensure_one()
        return self.lines

    @api.depends('lines.margin', 'is_total_cost_computed')
    def _compute_margin(self):
        for order in self:
            sign = -1 if order.is_refund_or_negative() else 1
            if order.is_total_cost_computed:
                order.margin = sum(order.lines.mapped('margin'))
                amount_untaxed = order.currency_id.round(sum(line.price_subtotal for line in order.lines)) * sign
                order.margin_percent = (not float_is_zero(amount_untaxed, precision_rounding=order.currency_id.rounding)
                                        and order.margin / amount_untaxed) \
                                        or 0
            else:
                order.margin = 0
                order.margin_percent = 0

    @api.onchange('payment_ids', 'lines')
    def _onchange_amount_all(self):
        self._compute_prices()

    def _get_order_tax_totals(self):
        self.ensure_one()
        self.amount_paid = sum(payment.amount for payment in self.payment_ids)
        self.amount_return = -sum((payment.amount < 0 and payment.amount) or 0 for payment in self.payment_ids)
        base_lines = self.lines._prepare_base_lines_for_taxes_computation()
        self.env['account.tax']._add_tax_details_in_base_lines(base_lines, self.company_id)
        self.env['account.tax']._round_base_lines_tax_details(base_lines, self.company_id)

        cash_rounding = None
        only_cash = self.config_id.only_round_cash_method
        available_type = ['cash'] if only_cash else ['cash', 'bank']

        if self.payment_ids.filtered_domain([
            ('payment_method_id.type', 'in', available_type),
        ]):
            cash_rounding = self.config_id.rounding_method

        return self.env['account.tax']._get_tax_totals_summary(
            base_lines=base_lines,
            currency=self.currency_id,
            company=self.company_id,
            cash_rounding=cash_rounding,
        )

    def _compute_prices(self):
        for order in self:
            if not order.currency_id:
                raise UserError(_("You can't: create a pos order from the backend interface, or unset the pricelist, or create a pos.order in a python test with Form tool, or edit the form view in studio if no PoS order exist"))
            tax_totals = order._get_order_tax_totals()
            rounding_base_amount_currency = tax_totals.get('cash_rounding_base_amount_currency', 0)
            amount_total = tax_totals['total_amount_currency'] - rounding_base_amount_currency
            refund_factor = -1 if order.is_refund_or_negative() else 1
            order.amount_tax = refund_factor * tax_totals['tax_amount_currency']
            order.amount_total = refund_factor * amount_total
            order.amount_difference = order.amount_paid - amount_total

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
        order_to_cancel = self.env['pos.order']
        for pos_order in self:
            if pos_order.state not in ['draft', 'cancel']:
                raise UserError(_('In order to delete a sale, it must be new or cancelled.'))
            if pos_order.state == 'draft':
                order_to_cancel |= pos_order
        # Cancel orders before deletion to trigger notifications and keep the UI in sync
        if order_to_cancel:
            order_to_cancel.action_pos_order_cancel()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            session = self.env['pos.session'].browse(vals['session_id'])
            vals = self._complete_values_from_session(session, vals)
        return super().create(vals_list)

    def _update_sequence_number(self, session, values):
        # Some localization needs orders to have a sequence number
        seq_id = session.config_id.order_seq_id
        prefix, suffix = seq_id._get_prefix_suffix()
        seq_next = seq_id._next()
        if prefix:
            seq_next = seq_next.removeprefix(prefix)
        if suffix:
            seq_next = seq_next.removesuffix(suffix)
        values['sequence_number'] = seq_next

    @api.model
    def _complete_values_from_session(self, session, values):
        values.setdefault('pricelist_id', session.config_id.pricelist_id.id)
        values.setdefault('fiscal_position_id', session.config_id.default_fiscal_position_id.id)
        values.setdefault('company_id', session.config_id.company_id.id)
        if session.config_id.use_presets and session.config_id.default_preset_id:
            values.setdefault('preset_id', session.config_id.default_preset_id.id)

        if not values.get('pos_reference'):
            reference, tracking_number = session.config_id._get_next_order_refs()
            values['pos_reference'] = reference
            values['tracking_number'] = tracking_number

        if not values.get('sequence_number'):
            self._update_sequence_number(session, values)

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
            allowed_vals = ['paid', 'done', 'invoiced']
            if vals.get('state') and vals['state'] not in allowed_vals and order.state in allowed_vals:
                raise UserError(_('This order has already been paid. You cannot set it back to draft or edit it.'))
            if vals.get('state') and vals['state'] in ('cancel', 'paid', 'done') and order.print_history:
                vals['print_history'] = False

        list_line = self._create_pm_change_log(vals)
        res = super().write(vals)
        for order in self:
            if vals.get('payment_ids'):
                order._compute_prices()
                totally_paid_or_more = order.currency_id.compare_amounts(order.amount_paid, order.amount_total)
                if totally_paid_or_more < 0 and order.state in ['paid', 'done']:
                    raise UserError(_('The paid amount is different from the total amount of the order.'))
                if totally_paid_or_more > 0 and order.state == 'paid':
                    list_line.append(_("Warning, the paid amount is higher than the total amount. (Difference: %s)", formatLang(self.env, order.amount_paid - order.amount_total, currency_obj=order.currency_id)))
                if order.nb_print > 0 and any(command[0] in [0, 1] and command[2].get('payment_status') and command[2]['payment_status'] != 'cancelled' for command in vals.get('payment_ids')):
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

    def _get_order_name_from_pos_reference(self, session=None):
        """Return the order name from the sequence prefix and the receipt reference (``pos_reference``)."""
        self.ensure_one()
        session = session or self.session_id
        last_reference_part = self.get_reference_last_part()
        seq_id = session.config_id.order_seq_id
        prefix, suffix = seq_id._get_prefix_suffix()
        if not prefix:
            prefix = session.config_id.name
        suffix = f" - {suffix}" if suffix else ''
        return f"{prefix} - {last_reference_part}{suffix}"

    def _compute_order_name(self, session=None):
        session = session or self.session_id
        if self.refunded_order_id.exists():
            return _('%(refunded_order)s REFUND', refunded_order=self.refunded_order_id.name)
        return self._get_order_name_from_pos_reference(session)

    def get_reference_last_part(self):
        return self.pos_reference.split('-')[-1]

    @api.model
    def _cron_process_pos_orders(self):
        """
        Entry point for the POS 5-minute cron.

        This method acts as a central handler that runs various
        PoS order-related background tasks (e.g., processing deferred
        invoices, syncing orders, cleanup operations).

        Each task should be implemented in its own dedicated method
        and called from here to keep responsibilities well separated.
        """
        self._process_deferred_invoice_orders()

    @api.model
    def _process_deferred_invoice_orders(self):
        orders = self.search([('defer_invoice_pdf', '=', True)])
        for order in orders:
            try:
                order.account_move.with_context(skip_invoice_sync=True)._generate_and_send()
            except (UserError, ValidationError) as e:
                _logger.error("Error processing order %s: %s", order.name, e)
            order.defer_invoice_pdf = False

    def action_view_invoice(self):
        invoices = self.account_move
        if (len(invoices) == 1):
            return {
                'name': _('Customer Invoice'),
                'view_mode': 'form',
                'view_id': self.env.ref('account.view_move_form').id,
                'res_model': 'account.move',
                'context': "{'move_type':'out_invoice'}",
                'type': 'ir.actions.act_window',
                'res_id': self.account_move.id,
            }
        return {
            'name': _('Customer Invoices'),
            'view_mode': 'list,form',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', invoices.ids)],
        }

    def action_create_invoices(self):
        return {
            'name': _('Create Invoice(s)'),
            'view_mode': 'form',
            'view_id': self.env.ref('point_of_sale.view_pos_make_invoice').id,
            'res_model': 'pos.make.invoice',
            'target': 'new',
            'type': 'ir.actions.act_window',
            'context': {'dialog_size': 'medium'},
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
           and (force_round or (not self.config_id.only_round_cash_method
           or any(p.payment_method_id.type == 'cash' for p in self.payment_ids))):
            amount = float_round(amount, precision_rounding=self.config_id.rounding_method.rounding, rounding_method=self.config_id.rounding_method.rounding_method)
        currency = self.currency_id
        return currency.round(amount) if currency else amount

    def _get_partner_bank_id(self):
        partner_bank_id = False
        amount_total = sum(order.amount_total for order in self)

        def _first_allowed(bank_ids):
            return bank_ids.filtered(lambda b: b.allow_out_payment)[:1]

        # Case 1: refund / negative amount → customer bank
        if amount_total <= 0 and self.partner_id.bank_ids:
            partner_bank_id = _first_allowed(self.partner_id.bank_ids)

        # Case 2: positive amount → payment journal bank
        elif amount_total >= 0 and self.payment_ids:
            journal_bank = self.payment_ids[0].payment_method_id.journal_id.bank_account_id
            if journal_bank and journal_bank.allow_out_payment:
                partner_bank_id = journal_bank

        # Case 3: fallback → company bank
        if not partner_bank_id and amount_total >= 0 and self.company_id.partner_id.bank_ids:
            partner_bank_id = _first_allowed(self.company_id.partner_id.bank_ids)

        return partner_bank_id.id if partner_bank_id else False

    def action_pos_order_paid(self):
        self.ensure_one()

        # TODO: add support for mix of cash and non-cash payments when both cash_rounding and only_round_cash_method are True
        if not self.config_id.cash_rounding \
           or (self.config_id.only_round_cash_method
           and not any(p.payment_method_id.type == 'cash' for p in self.payment_ids)):
            total = self.amount_total
        else:
            total = float_round(self.amount_total, precision_rounding=self.config_id.rounding_method.rounding, rounding_method=self.config_id.rounding_method.rounding_method)

        isPaid = float_is_zero(total - self.amount_paid, precision_rounding=self.currency_id.rounding)

        if not isPaid and not self.config_id.cash_rounding:
            raise UserError(_("Order %s is not fully paid.", self.name))
        if not isPaid and self.config_id.cash_rounding:
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

    def _prepare_product_aml_dict(self, base_line_vals, update_base_line_vals, rate, sign):
        amount_currency = update_base_line_vals['amount_currency']
        balance = self.company_id.currency_id.round(amount_currency * rate)
        order_line = base_line_vals['record']
        return {
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
            'no_followup': False,
        }

    @api.model
    def get_example_order_data(self):
        last_order = self.env['pos.order'].search([], order='id desc', limit=1)
        return last_order.order_receipt_generate_data()

    def action_pos_order_receipt(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/pos/receipt/{self.id}?company_id={self.company_id.id}",
            "target": "new",
        }

    def _get_invoice_post_context(self):
        return {"skip_invoice_sync": True}

    def _get_payments(self):
        return self.payment_ids.sudo().with_company(self.company_id)

    def _reconcile_invoice_payments(self, invoice, payment_moves):
        receivable_account = self.env["res.partner"]._find_accounting_partner(invoice.partner_id).with_company(self.company_id).property_account_receivable_id
        payment_receivable_lines = payment_moves.pos_payment_ids._get_receivable_lines_for_invoice_reconciliation(receivable_account)
        invoice_receivable_lines = invoice.line_ids.filtered(lambda line: line.account_id == receivable_account and not line.reconciled)
        (payment_receivable_lines | invoice_receivable_lines).sudo().with_company(invoice.company_id).reconcile()

    def _post_cancel_message(self, author_id=None):
        author_id = author_id or self.env.user.partner_id.id
        for record in self:
            record.message_post(body=_('Point of Sale Order cancelled'), author_id=author_id)

    def cancel_order_from_pos(self):
        draft_orders = self.filtered(lambda o: o.state == 'draft')
        today = fields.Date.context_today(self)
        if self.env.context.get('active_ids'):
            orders = self.browse(self.env.context.get('active_ids'))
            order_is_in_futur = any(order.preset_time and order.preset_time.date() > today for order in orders)
            if order_is_in_futur:
                raise UserError(_('The order delivery / pickup date is in the future. You cannot cancel it.'))
            if not draft_orders:
                raise UserError(_('This order has already been paid. You cannot set it back to draft or edit it.'))

        if draft_orders:
            draft_orders.write({'state': 'cancel'})
            author_id = self.session_id._get_message_author().id
            draft_orders._post_cancel_message(author_id=author_id)
            for config in draft_orders.mapped('config_id'):
                config.notify_synchronisation(config.current_session_id.id, self.env.context.get('device_identifier', 0))

        return {
            'pos.order': self._load_pos_data_read(draft_orders, self.config_id),
        }

    def action_pos_order_cancel(self):
        orders = self.browse(self.env.context.get('active_ids'))
        orders.write({'state': 'cancel'})
        orders._post_cancel_message()
        for config in orders.config_id:
            config.notify_synchronisation(config.current_session_id.id, 0)

    def _get_open_order(self, order):
        return self.env["pos.order"].search([('uuid', '=', order.get('uuid'))], limit=1, order='id desc')

    @staticmethod
    def _get_order_log_representation(order):
        return {k: order.get(k) for k in ("name", "pos_reference", "uuid")}

    def _should_log_order_data(self):
        return self.env['ir.config_parameter'].sudo().get_bool('point_of_sale.log_order_data')

    @api.model
    def sync_from_ui(self, orders):
        """ Create and update Orders from the frontend PoS application.

        Create new orders and update orders that are in draft status. If an order already exists with a status
        different from 'draft' it will be discarded, otherwise it will be saved to the database. If saved with
        'draft' status the order can be overwritten later by this function.

        :param orders: dictionary with the orders to be created.
        :type orders: dict.
        :returns: list of db-ids for the created and updated orders.
        :rtype: list
        """
        sync_token = randrange(100_000_000)  # Use to differentiate 2 parallels calls to this function in the logs
        _logger.info("PoS synchronisation #%d started for PoS orders references: %s", sync_token, [self._get_order_log_representation(order) for order in orders])
        order_ids = []

        for order in orders:
            order_log_name = self._get_order_log_representation(order)
            if self._should_log_order_data():
                _logger.info("PoS synchronisation #%d processing order %s order full data:\n%s", sync_token, order_log_name, pformat(order))

            refunded_orders = self._get_refunded_orders(order)
            if len(refunded_orders) > 1:
                raise ValidationError(_('You can only refund products from the same order.'))
            if len(refunded_orders) == 1:
                order_ids.append(refunded_orders[0].id)

            existing_order = self._get_open_order(order)
            if existing_order and existing_order.state == 'draft':
                order_ids.append(self._process_order(order, existing_order))
                _logger.info("PoS synchronisation #%d order %s updated pos.order #%d", sync_token, order_log_name, order_ids[-1])
            elif not existing_order:
                order_ids.append(self._process_order(order, False))
                _logger.info("PoS synchronisation #%d order %s created pos.order #%d", sync_token, order_log_name, order_ids[-1])
            else:
                # In theory, this situation is unintended
                # In practice it can happen when "Tip later" option is used
                # This will update the order if edited after payent from UI.
                if existing_order.state == "paid" and not existing_order.nb_print:
                    self.process_saved_payments(order, existing_order)
                order_ids.append(existing_order.id)
                _logger.info("PoS synchronisation #%d order %s sync ignored for existing PoS order %s (state: %s)", sync_token, order_log_name, existing_order, existing_order.state)

        # Sometime pos_orders_ids can be empty.
        pos_order_ids = self.env['pos.order'].browse(order_ids)
        config = pos_order_ids.config_id[0] if pos_order_ids else False

        for order in pos_order_ids:
            order._ensure_access_token()
            if not self.env.context.get('preparation'):
                order.config_id.notify_synchronisation(order.config_id.current_session_id.id, self.env.context.get('device_identifier', 0))

        _logger.info("PoS synchronisation #%d finished", sync_token)
        return pos_order_ids.read_pos_data(orders, config)

    @api.model
    def read_pos_orders(self, domain=False):
        orders = self.search(domain)
        config_id = orders[0].config_id if orders else False
        return orders.read_pos_data([], config_id) if config_id else {'pos.order': []}

    @api.model
    def read_pos_data_uuid(self, uuid):
        return self.read_pos_orders([('uuid', '=', uuid)])

    def read_pos_data(self, data, config):
        # If the previous session is closed, the order will get a new session_id due to _get_valid_session in _process_order
        account_moves = self.sudo().account_move | self.sudo().payment_ids.account_move_id | self.session_id.sales_move_id | self.session_id.refunds_move_id
        return {
            'pos.order': self._load_pos_data_read(self, config) if config else [],
            'pos.session': [],
            'pos.payment': self.env['pos.payment']._load_pos_data_read(self.payment_ids, config) if config else [],
            'pos.order.line': self.env['pos.order.line']._load_pos_data_read(self.lines, config) if config else [],
            'product.attribute.custom.value': self.env['product.attribute.custom.value']._load_pos_data_read(self.lines.custom_attribute_value_ids, config) if config else [],
            'account.move': self.env['account.move'].sudo()._load_pos_data_read(account_moves, config) if config else [],
            'pos.prep.order': self.env['pos.prep.order']._load_pos_data_read(self.prep_order_ids, config) if config else [],
            'pos.prep.line': self.env['pos.prep.line']._load_pos_data_read(self.prep_order_ids.prep_line_ids, config) if config else [],
        }

    @api.model
    def _get_refunded_orders(self, order):
        refunded_orderline_ids = [line[2]['refunded_orderline_id'] for line in order['lines'] if line[0] in [0, 1] and line[2].get('refunded_orderline_id')]
        return self.env['pos.order.line'].browse(refunded_orderline_ids).mapped('order_id')

    def add_payment(self, data):
        """Create a new payment for the order"""
        self.ensure_one()
        self.env['pos.payment'].create(data)
        self.amount_paid = self._compute_amount_paid()

    def _prepare_refund_values(self, current_session):
        self.ensure_one()
        pos_reference, tracking_number = current_session.config_id._get_next_order_refs()
        return {
            'name': _('%(name)s REFUND', name=self.name),
            'session_id': current_session.id,
            'date_order': fields.Datetime.now(),
            'pos_reference': pos_reference,
            'lines': False,
            'amount_paid': 0,
            'is_total_cost_computed': False,
            'is_refund': True,
            'tracking_number': tracking_number,
        }

    def _prepare_mail_values(self, email, ticket, basic_ticket):
        message = Markup(
            _("<p>Dear %(client_name)s,<br/>Here is your Receipt %(is_invoiced)sfor \
            %(pos_name)s amounting in %(amount)s from %(company_name)s. </p>"),
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
                order._prepare_refund_values(current_session),
            )
            for line in order.lines:
                if line.refunded_qty < line.qty:
                    refund_line = line.copy(line._prepare_refund_data(refund_order))
                    refund_line._onchange_amount_line_all()
            refund_order._compute_prices()
            refund_orders |= refund_order
            refund_order.config_id.notify_synchronisation(current_session.id, 0)
        refund_orders._compute_prices()
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
            'target': 'new',
        }

    def action_send_receipt(self, email):
        self.ensure_one()
        self.email = email
        mail_template_id = 'point_of_sale.email_template_pos_receipt'
        mail_template = self.env.ref(mail_template_id, raise_if_not_found=False)
        ticket_image = self.order_receipt_generate_image()
        basic_image = None
        if self.config_id.basic_receipt:
            basic_image = self.order_receipt_generate_image(True)
        if not mail_template:
            raise UserError(_("The mail template with xmlid %s has been deleted.", mail_template_id))
        mail_template.send_mail(
            self.id,
            force_send=True,
            email_values={
                'email_to': email,
                'attachment_ids': self._get_mail_attachments(self.name, ticket_image, basic_image),
            })

    def _get_mail_attachments(self, name, ticket, basic_ticket):
        attachments = []

        if ticket:
            receipt = self.env['ir.attachment'].create({
                'name': 'Receipt-' + name + '.jpg',
                'type': 'binary',
                'raw': ticket,
                'res_model': 'pos.order',
                'res_id': self.ids[0],
                'mimetype': 'image/jpeg',
            })
            attachments += [(4, receipt.id)]

        if basic_ticket:
            basic_receipt = self.env['ir.attachment'].create({
                'name': 'Receipt-' + name + '-1' + '.jpg',
                'type': 'binary',
                'raw': basic_ticket,
                'res_model': 'pos.order',
                'res_id': self.ids[0],
                'mimetype': 'image/jpeg',
            })
            attachments += [(4, basic_receipt.id)]

        if self.mapped('account_move'):
            report = self.env['ir.actions.report']._render_qweb_pdf("account.account_invoices", self.account_move.ids[0])
            invoice = self.env['ir.attachment'].create({
                'name': name + '.pdf',
                'type': 'binary',
                'raw': report[0],
                'res_model': 'pos.order',
                'res_id': self.ids[0],
                'mimetype': 'application/pdf',
            })
            attachments += [(4, invoice.id)]

        return attachments

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
    def search_order_ids(self, config_id, domain, limit, offset, state_filter='paid'):
        """Search for orders that satisfy the given domain, limit and offset.

        state_filter: 'paid' for non-draft/non-cancelled orders, 'cancelled' for cancelled orders.
        """
        pos_config = self.env['pos.config'].browse(config_id)
        if state_filter == 'cancelled':
            state_domain = Domain('state', '=', 'cancel')
        else:
            state_domain = Domain('state', '!=', 'draft') & Domain('state', '!=', 'cancel')
        default_domain = state_domain & Domain('config_id', 'in', [config_id] + pos_config.trusted_config_ids.ids)
        real_domain = Domain(domain) & default_domain
        orders = self.search(real_domain, limit=limit, offset=offset, order='create_date desc')
        # We clean here the orders that does not have the same currency.
        # As we cannot use currency_id in the domain (because it is not a stored field),
        # we must do it after the search.
        orders = orders.filtered(lambda order: order.currency_id == pos_config.currency_id)
        orderlines = self.env['pos.order.line'].search(['|', ('refunded_orderline_id.order_id', 'in', orders.ids), ('order_id', 'in', orders.ids)])

        # We will return to the frontend the ids and the date of their last modification
        # so that it can compare to the last time it fetched the orders and can ask to fetch
        # orders that are not up-to-date.
        # The date of their last modification is either the last time one of its orderline has changed,
        # or the last time a refunded orderline related to it has changed.
        orders_info = {order.id: order.write_date for order in orders}
        for orderline in orderlines:
            key_order = orderline.order_id.id if orderline.order_id in orders \
                            else orderline.refunded_orderline_id.order_id.id
            if orders_info[key_order] < orderline.write_date:
                orders_info[key_order] = orderline.write_date
        totalCount = self.search_count(real_domain)
        return {'ordersInfo': list(orders_info.items())[::-1], 'totalCount': totalCount}

    def _should_send_to_preparation(self):
        """
        Determine whether the order should be sent to preparation based
        on its payment status and the config's payment method configuration.
        """
        return self.state == "paid"

    def _send_order(self):
        self.ensure_one()
        if self._should_send_to_preparation():
            self.env['pos.prep.order'].sudo().update_last_order_change(self.sudo())  # Will send to preparation display if installed.

    def _prepare_pos_log(self, body):
        return body

    def _set_product_qty_available(self):
        if not self._should_update_quantity_on_product():
            return
        for line in self.lines:
            if line.product_id.is_storable:
                line.product_id.sudo().qty_available -= line.qty

    @api.model
    def _should_update_quantity_on_product(self):
        """ Overriden in pos_stock, as the quantity update is handled through the stock module.
        """
        return True

    ##############################################################
    #                 Accounting related methods                 #
    ##############################################################
    def _grouping_function(self, base_line):
        use_product = self.config_id.use_closing_entry_by_product
        product_id = base_line['product_id']
        return frozendict({
            'account_id': base_line['account_id'],
            'product_id': product_id if use_product else False,
            'tax_ids': base_line['tax_ids'],
        })

    def _prepare_move_line_vals_from_base_line(self, base_line):
        product = base_line['product_id']
        name = base_line['account_id'].name
        product_id = product.id if product else False
        if product:
            desc = product.description_sale
            name = f"{product.display_name} {desc}" if desc else product.display_name

        if self.config_id._is_quantities_set():
            quantity = base_line['_aggregated_quantity']
            price_unit = base_line['price_unit'] / quantity if quantity else base_line['price_unit']
        else:
            quantity, price_unit = 1.0, base_line['price_unit']

        line_vals = {
            'name': name,
            'quantity': quantity,
            'price_unit': price_unit,
            'display_type': 'product',
            'extra_tax_data': self.env['account.tax']._export_base_line_extra_tax_data(base_line),
            'account_id': base_line['account_id'].id,
            'tax_ids': [(6, 0, base_line['tax_ids'].ids)],
        }
        if self.config_id.use_closing_entry_by_product:
            line_vals['product_id'] = product_id

        return line_vals

    def _aggregate_base_line_and_prepare_account_move_line_data(self, base_lines):
        def aggregate_function(target_base_line, base_line):
            target_base_line.setdefault('_aggregated_quantity', 0.0)
            target_base_line['_aggregated_quantity'] += base_line['quantity']

        AccountTax = self.env['account.tax']
        company = self.company_id
        aggregated = AccountTax._reduce_base_lines_with_grouping_function(
            base_lines,
            grouping_function=self._grouping_function,
            aggregate_function=aggregate_function,
        )
        AccountTax._fix_base_lines_tax_details_on_manual_tax_amounts(
            aggregated,
            company,
        )
        to_create = []
        for base_line in aggregated:
            to_create.append({
                'account.move.line': self._prepare_move_line_vals_from_base_line(base_line),
                'metadata': {
                    'base_line': base_line,
                },
            })
        return to_create

    def _prepare_account_move_line_data_from_base_line(self, base_lines):
        """
        Convert base_lines to a format compatible with account.move.line Command.create().

        This produces the same structure as _aggregate_base_line_and_prepare_account_move_line_data
        but without any aggregation, each base_line becomes its own entry.
        """
        def add_customer_note(note):
            to_create.append({
                'account.move.line': {
                    'name': note,
                    'display_type': 'line_note',
                },
                'metadata': {},
            })

        self.ensure_one()  # Not aggregated version can only works with on order
        if not len(base_lines):
            return []

        to_create = []
        is_percentage = self.pricelist_id and any(
            self.pricelist_id.item_ids.filtered(
                lambda rule: rule.compute_price == "percentage",
            ),
        )

        for base_line in base_lines:
            line = base_line['record']
            product = base_line['product_id']

            if line.product_id.type == 'combo' and not self.env.context.get('hide_combo_title'):
                to_create.append({
                    'account.move.line': {
                        'display_type': 'line_section',
                        'name': f"{product.name} x {line.qty}",
                        'quantity': abs(line.qty),
                        'product_uom_id': line.product_id.uom_id.id,
                    },
                    'metadata': {
                        'line': line,
                    },
                })
            elif line.product_id.type != 'combo':
                desc = product.description_sale
                name = f"{product.display_name} {desc}" if desc else product.display_name
                to_create.append({
                    'account.move.line': {
                        'name': name,
                        'display_type': 'product',
                        'quantity': base_line['quantity'],
                        'discount': base_line['discount'],
                        'price_unit': base_line['price_unit'],
                        'account_id': base_line['account_id'].id,
                        'tax_ids': [(6, 0, base_line['tax_ids'].ids)],
                        'extra_tax_data': self.env['account.tax']._export_base_line_extra_tax_data(base_line),
                        'product_id': product.id,
                        'product_uom_id': base_line['uom_id'].id,
                    },
                    'metadata': {
                        'line': line,
                    },
                })

            price_changed = float_compare(
                line.price_unit,
                line.product_id.lst_price,
                precision_rounding=self.currency_id.rounding,
            )

            if is_percentage and price_changed < 0:
                decimal = self.currency_id.decimal_places
                name = _(
                    'Price discount from %(list_price)s to %(price_unit)s',
                    list_price=float_repr(line.product_id.lst_price, decimal),
                    price_unit=float_repr(line.price_unit, decimal),
                )
                add_customer_note(name)

            if line.customer_note:
                add_customer_note(line.customer_note)

        if self.general_customer_note:
            add_customer_note(self.general_customer_note)

        return to_create

    def _prepare_account_move_line_data(self, aggregate=True):
        """
        Build Command.create entries for account move line, this method
        is used in both the invoice generation and the session closing
        to create move lines for sales and refunds.
        - Session closing: lines are aggregated by taxes
        - Order invoice: no aggregation, each line is a separate entry
        """
        AccountTax = self.env['account.tax']
        company = self.company_id
        base_lines = []

        # 1. Collect base_lines with PER-ORDER rounding + accounting data
        for order in self:
            lines = order.lines._prepare_base_lines_for_taxes_computation()
            AccountTax._add_tax_details_in_base_lines(lines, company)
            AccountTax._round_base_lines_tax_details(lines, company)
            AccountTax._add_accounting_data_in_base_lines_tax_details(
                lines,
                company,
                include_caba_tags=True,
            )
            base_lines.extend(lines)

        if not aggregate:
            # Transform each base_line to the same format as aggregated version,
            # but without grouping/aggregation. Each line becomes a separate entry.
            AccountTax._fix_base_lines_tax_details_on_manual_tax_amounts(
                base_lines,
                company,
            )
            return self._prepare_account_move_line_data_from_base_line(base_lines)

        # Create zero price line independently, as they will not be aggregated
        # This can happen with a fixed taxes, the product is free but the
        # tax will add price on the receipt
        zero_price_line_data = [line for line in base_lines if line['currency_id'].is_zero(line['price_unit'])]
        sales_by_order = defaultdict(list)
        zero_price_lines = []

        for line in zero_price_line_data:
            sales_by_order[line['record'].order_id].append(line)

        for [order, line] in sales_by_order.items():
            data = order._prepare_account_move_line_data_from_base_line(line)
            zero_price_lines.extend(data)

        # 2. Aggregate product lines by (revenue account + VAT rate) grouping
        aggregated_per_line = self._aggregate_base_line_and_prepare_account_move_line_data(base_lines)
        return aggregated_per_line + zero_price_lines

    def _prepare_account_move_line_data_for_payments(self, partner=None):
        """
        Aggregate pos.payment amounts by payment method for the session receipt.

        This method only COLLECTS and AGGREGATES data, it does NOT create any
        accounting records. The actual account.payment records are created
        later, after the out_receipt is posted

        Skipped:
          - payments whose order is already invoiced (handled by a separate flow)
        """
        combined = {}   # pm -> total signed amount
        session = self.session_id  # Always single record in this context
        today = fields.Date.context_today(self)

        for payment in self.payment_ids:
            pm = payment.payment_method_id
            combined.setdefault(pm, 0.0)
            combined[pm] += payment.amount

        # Combined payments: aggregate all orders for a given PM into one slot
        result = []
        for pm, amount in combined.items():
            partner_account = partner.property_account_receivable_id if partner else None
            destination_account = partner_account or session._get_receivable_account()

            result.append({
                'account.move.line': {
                    'display_type': 'payment_term',
                    'name': pm.name,
                    'account_id': destination_account.id,
                    'partner_id': partner.id if partner else None,
                    'date_maturity': today,
                    'amount_currency': amount,
                },
                'metadata': {
                    'payment_method_id': pm,
                },
            })

        return result

    def _prepare_account_move_line_data_for_rounding(self, invoice):
        line_ids_commands = []
        currency = self.currency_id
        lines = invoice.line_ids.filtered_domain([
            ('display_type', '!=', 'rounding'),
        ])

        debit = sum(lines.mapped('debit'))
        credit = sum(lines.mapped('credit'))
        invoice_difference = credit - debit

        if invoice.move_type == 'out_refund':
            invoice_difference = -invoice_difference

        if not self.config_id.cash_rounding or currency.is_zero(invoice_difference):
            return line_ids_commands

        rate = invoice.invoice_currency_rate
        difference_balance = invoice.company_currency_id.round(invoice_difference / rate) if rate else 0.0
        signed_difference = (invoice_difference * invoice.direction_sign)
        signed_balance = (difference_balance * invoice.direction_sign)

        profit = invoice.invoice_cash_rounding_id.loss_account_id
        lost = invoice.invoice_cash_rounding_id.profit_account_id
        account = profit if invoice_difference > 0.0 else lost
        rounding_line = invoice.line_ids.filtered(
            lambda line: line.display_type == 'rounding' and not line.tax_line_id,
        )

        if rounding_line:
            line_ids_commands.append(Command.unlink(rounding_line.id))

        line_ids_commands.append(Command.create({
            'name': invoice.invoice_cash_rounding_id.name,
            'amount_currency': -signed_difference,
            'balance': -signed_balance,
            'currency_id': invoice.currency_id.id,
            'display_type': 'rounding',
            'account_id': account.id,
        }))

        return line_ids_commands

    def _prepare_invoice_vals(self):
        """We have orders filtered by company > config > partners >
        fiscal_positions so it won't make any issue when we access user,
        partner, bank or similar directly.
        """
        invoice_date = fields.Date.today()
        pos_refunded_invoice_ids = []
        is_single_order = len(self) == 1

        for orderline in self.lines:
            refunded_line = orderline.refunded_orderline_id
            if refunded_line.order_id.account_move:
                pos_refunded_invoice_ids.append(
                    refunded_line.order_id.account_move.id,
                )

        is_some_refund = any(order.is_refund_or_negative() for order in self)
        is_total_negative = sum(order.amount_total for order in self) < 0
        move_type = 'out_refund' if is_some_refund or is_total_negative else 'out_invoice'
        partner_term = self.partner_id.property_payment_term_id
        is_pay_later = any(p.payment_method_id.type == 'pay_later' for p in self.payment_ids)
        invoice_payment_term_id = partner_term.id if partner_term and is_pay_later else False
        lines = []
        for order in self:
            lines += order._prepare_account_move_line_data(False)
        line_commands = [Command.create(line['account.move.line']) for line in lines]
        users = self.user_id.ids
        fp = self.fiscal_position_id.ids
        currencies = self.currency_id.ids
        ref = None

        if is_single_order:
            ref = _('Customer invoice from %(pos_reference)s', pos_reference=self.name)

        if len(currencies) > 1:
            raise UserError(_("You cannot create an invoice for orders with different currencies."))

        # Ensure rounding method record is set on the invoice if needed
        rounding_method = self.config_id._get_rounding_method_for_invoice(self)

        vals = {
            'invoice_origin': ', '.join(ref or '' for ref in self.mapped('pos_reference')),
            'pos_refunded_invoice_ids': pos_refunded_invoice_ids,
            'review_state': 'no_review',
            'ref': ref,
            'journal_id': self.config_id.journal_id.id,
            'move_type': move_type,
            'partner_id': self.partner_id.address_get(['invoice'])['invoice'],
            'partner_shipping_id': self.partner_id.address_get(['delivery'])['delivery'],
            'partner_bank_id': self._get_partner_bank_id(),
            'currency_id': self.currency_id.id,
            'invoice_date': invoice_date,
            'invoice_user_id': users[0] if len(users) == 1 else None,
            'fiscal_position_id': fp[0] if fp else None,
            'invoice_line_ids': line_commands,
            'invoice_payment_term_id': invoice_payment_term_id,
            'invoice_cash_rounding_id': rounding_method.id,
        }

        refunded_order_invoice = self.refunded_order_id.account_move
        if is_single_order and refunded_order_invoice:
            vals['ref'] = _('Reversal of: %s', refunded_order_invoice.name)
            vals['reversed_entry_id'] = refunded_order_invoice.id

        if any(order.floating_order_name for order in self):
            narr = ', '.join(self.filtered('floating_order_name').mapped('floating_order_name'))
            vals.update({'narration': narr})

        return vals

    def _prepare_invoice_extra_line_commands(self, payments=[]):
        """ Inherited in pos_stock """
        return []

    def _generate_pos_order_invoice(self):
        if not self.env['res.company']._with_locked_records(self, allow_raising=False):
            raise UserError(_("Some orders are already being invoiced. Please try again later."))

        company = self.company_id
        vals = self._prepare_invoice_vals()

        lines = []
        total_payments_by_session = {}
        for order in self:
            payments = order._prepare_account_move_line_data_for_payments(
                order.partner_id,
            )

            line_data = [pm['account.move.line'] for pm in payments]
            payment_commands = [Command.create(pm_data) for pm_data in line_data]
            extra_commands = order._prepare_invoice_extra_line_commands(payments)
            lines += payment_commands + extra_commands
            total_payments_by_session.setdefault(order.session_id, [])
            total_payments_by_session[order.session_id] += payments

        vals['line_ids'] = lines
        AccountMove = self.env['account.move'].sudo().with_company(company)
        move_ctx = AccountMove.with_context(
            default_move_type=vals['move_type'],
            check_move_validity=False,
            always_tax_exigible=True,
            linked_to_pos=True,
        )
        invoice = move_ctx.create(vals)
        invoice_ctx = invoice.sudo().with_company(company).with_context(
            **self._get_invoice_post_context(),
        )

        # Create rounding line if needed
        data = self._prepare_account_move_line_data_for_rounding(invoice)
        with self.env['account.move']._check_balanced({'records': invoice}):
            invoice.with_context(linked_to_pos=True).line_ids = data

        # Set account_move before _post() so that invoice.pos_order_ids is
        # populated when stock_account computes COGS via _get_cogs_value()
        # (pos_stock overrides _get_cogs_value to use _get_pos_anglo_saxon_price_unit
        # which relies on pos_order_ids being set on the move).
        self.account_move = invoice
        invoice_ctx._post()

        if not self.env.context.get('skip_payment'):
            name_str = " - ".join(self.mapped('name')) if len(self) > 1 else self.name
            all_payment_lines = self.env['account.move.line']
            payment_term_lines = invoice.line_ids.filtered(
                lambda line: line.display_type == 'payment_term',
            )

            for session, payments in total_payments_by_session.items():
                for payment in payments:
                    pm = payment['metadata']['payment_method_id']
                    amount = payment['account.move.line']['amount_currency']
                    all_payment_lines |= pm._create_payment_line(
                        session,
                        amount,
                        self.partner_id.property_account_receivable_id,
                        f"POS Order {name_str}",
                        self.partner_id,
                    )

            to_reconcile = (payment_term_lines | all_payment_lines).filtered(
                lambda line: not line.reconciled,
            )
            to_reconcile.with_context(skip_invoice_sync=True).reconcile()

        body = _("This invoice has been created from the point of sale session:%s",
            Markup().join(Markup("%s ") % order._get_html_link() for order in self),
        )
        invoice.message_post(body=body)
        if self.env.context.get('generate_pdf', True):
            invoice.with_context(skip_invoice_sync=True)._generate_and_send()
        else:
            order.defer_invoice_pdf = True

        statement = self.session_id.bank_statement_id
        if statement:
            statement._compute_balance_end_real()

        return invoice

    def _prepare_missing_invoice_moves(self):
        self.write({'to_invoice': True})
        return self._generate_pos_order_invoice()

    def action_invoice_download_pdf(self):
        self.ensure_one()
        if self.defer_invoice_pdf:
            self.account_move.with_context(skip_invoice_sync=True)._generate_and_send()
            self.defer_invoice_pdf = False
        return self.account_move.action_invoice_download_pdf()

    def action_pos_order_invoice(self):
        self.ensure_one()

        if self.invoice_status == 'invoiced':
            # Already has a real customer invoice (account_move is not a session closing entry).
            move = self.account_move
        elif self.session_id and self.session_id.state == 'closed':
            # Session is closed: reverse the closing entry and create a proper invoice.
            move = self._generate_invoice_after_session_closing()
        else:
            # Session still open: standard path (also handles pos_stock picking creation).
            move = self._prepare_missing_invoice_moves()

        return {
            'name': _('Customer Invoice'),
            'view_mode': 'form',
            'view_id': self.env.ref('account.view_move_form').id,
            'res_model': 'account.move',
            'context': "{'move_type':'out_invoice'}",
            'type': 'ir.actions.act_window',
            'target': 'current',
            'res_id': move.id,
        }

    def _generate_invoice_after_session_closing(self):
        """
        This method will reverse the corresponding amount from the global
        session closing entry and create a new invoice with the same
        amount, so that the invoice will be correctly taken into account
        in the fiscal report of the day of the order, and not in the day
        of the session closing.
        """
        self.ensure_one()
        if not self.session_id or self.session_id.state != "closed":
            return self._generate_pos_order_invoice()

        session = self.session_id
        refund_move = session.refunds_move_id
        sale_move = session.sales_move_id
        global_move = refund_move if self.is_refund_or_negative() else sale_move
        if not global_move or global_move.state != "posted":
            return self.env['account.move']

        invoice = self.with_context(
            skip_payment=True,
        )._generate_pos_order_invoice()
        session = self.session_id
        move = session._create_partial_reversal_move_from_session_closing(self)
        sign = -1 if self.is_refund_or_negative() else 1
        move.line_ids = [
            Command.create({
                'name': _("Reversal for %s", self.name),
                'account_id': global_move.line_ids[0].account_id.id,
                'partner_id': global_move.partner_id.id,
                'balance': invoice.amount_total * sign,
            }),
            Command.create({
                'name': _("Counterpart for invoice payment %s", invoice.name),
                'account_id': invoice.partner_id.property_account_receivable_id.id,
                'partner_id': invoice.partner_id.id,
                'balance': -invoice.amount_total * sign,
            }),
        ]

        move._post()
        counter_part = move.line_ids[-1]
        to_reconcile = invoice.line_ids.filtered_domain([
            ('account_id', '=', counter_part.account_id.id),
            ('reconciled', '=', False),
        ])
        (to_reconcile | counter_part).with_context(
            skip_invoice_sync=True,
        ).reconcile()
        return invoice
