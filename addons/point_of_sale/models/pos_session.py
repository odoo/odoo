# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from datetime import timedelta

from markupsafe import Markup

from odoo import Command, _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import float_is_zero, plaintext2html

_logger = logging.getLogger(__name__)


class PosSession(models.Model):
    _name = 'pos.session'
    _order = 'id desc'
    _description = 'Point of Sale Session'
    _inherit = ['mail.thread', 'mail.activity.mixin', "pos.bus.mixin", 'pos.load.mixin']

    POS_SESSION_STATE = [
        ('opening_control', 'Opening Control'),
        ('opened', 'In Progress'),
        ('closing_control', 'Closing Control'),
        ('closed', 'Closed & Posted'),
    ]

    company_id = fields.Many2one(
        'res.company',
        related='config_id.company_id',
        string="Company",
        readonly=True,
    )
    config_id = fields.Many2one(
        'pos.config',
        string='Point of Sale',
        required=True,
        index=True,
    )
    user_id = fields.Many2one(
        'res.users', string='Opened By',
        required=True,
        index=True,
        readonly=False,
        default=lambda self: self.env.uid,
        ondelete='restrict')
    currency_id = fields.Many2one(
        'res.currency',
        related='config_id.currency_id',
        string="Currency",
        readonly=False,
    )
    name = fields.Char(string='Session ID', readonly=True, default='/')
    start_at = fields.Datetime(string='Opening Date', readonly=True)
    stop_at = fields.Datetime(string='Closing Date', readonly=True, copy=False)
    opening_notes = fields.Text(string="Opening Notes")
    closing_notes = fields.Text(string="Closing Notes")
    state = fields.Selection(
        POS_SESSION_STATE,
        string='Status',
        required=True,
        readonly=True,
        index=True,
        copy=False,
        default='opening_control',
    )

    # Cash control fields
    bank_statement_id = fields.Many2one(
        'account.bank.statement',
        string='Bank Statement',
        index='btree_not_null',
        readonly=True)
    bank_statement_line_ids = fields.One2many(
        'account.bank.statement.line',
        related='bank_statement_id.line_ids',
        string='Bank Statement Lines',
        readonly=True)
    opening_balance = fields.Monetary(
        string='Opening Balance',
        related='bank_statement_id.balance_start',
        readonly=True)
    closing_balance = fields.Monetary(
        string='Closing Balance',
        related='bank_statement_id.balance_end_real',
        readonly=True,
    )
    closing_difference = fields.Monetary(
        string='Closing Difference',
        compute='_compute_closing_difference',
    )
    sales_move_id = fields.Many2one(
        'account.move',
        string='Sales Entry',
        index=True,
    )
    refunds_move_id = fields.Many2one(
        'account.move',
        string='Refunds Entry',
        index=True,
    )
    correction_move_ids = fields.Many2many(
        'account.move',
        string='Correction Entries',
        index=True,
    )
    move_ids = fields.Many2many(
        'account.move',
        string='Related Journal Entries',
        compute='_compute_move_ids',
        search='_search_move_ids',
    )
    account_move_count = fields.Integer(
        string='Number of related journal entries',
        compute='_compute_account_move_count',
    )

    order_ids = fields.One2many('pos.order', 'session_id', string='Orders')
    order_count = fields.Integer(compute='_compute_order_count')
    rescue = fields.Boolean(
        string='Recovery Session',
        help="Auto-generated session for orphan orders, ignored in constraints",
        readonly=True,
        copy=False)
    payment_method_ids = fields.Many2many(
        'pos.payment.method',
        related='config_id.payment_method_ids',
        string='Payment Methods',
    )
    total_payments_amount = fields.Float(
        compute='_compute_total_payments_amount',
        string='Total Payments Amount',
    )
    is_in_company_currency = fields.Boolean(
        'Is Using Company Currency',
        compute='_compute_is_in_company_currency',
    )

    @api.depends('closing_balance', 'opening_balance')
    def _compute_closing_difference(self):
        for record in self:
            record.closing_difference = record.closing_balance - record.opening_balance

    def write(self, vals):
        if vals.get('state') == 'closed':
            for record in self:
                record.config_id._notify(('CLOSING_SESSION', {
                    'device_identifier': self.env.context.get('device_identifier', False),
                    'session_id': record.id,
                }))
        return super().write(vals)

    @api.model
    def _load_pos_data_relations(self, model, fields):
        model_fields = self.env[model]._fields
        relations = {}

        for name, params in model_fields.items():
            if (name not in fields and len(fields)) or (params.manual and not len(fields)):
                continue

            if params.relational:
                relations[name] = {
                    'name': name,
                    'model': params.model_name,
                    'compute': bool(params.compute),
                    'related': bool(params.related),
                    'relation': params.comodel_name,
                    'type': params.type,
                }
                if params.type == 'many2one' and params.ondelete:
                    relations[name]['ondelete'] = params.ondelete
                if params.type == 'one2many' and params.inverse_name:
                    relations[name]['inverse_name'] = params.inverse_name
                if params.type == 'many2many':
                    relations[name]['relation_table'] = self.env[model]._fields[name].relation
            else:
                relations[name] = {
                    'name': name,
                    'type': params.type,
                    'compute': bool(params.compute),
                    'related': bool(params.related),
                }

        return relations

    @api.model
    def _load_pos_data_models(self, config):
        return [
            'pos.config', 'pos.preset', 'resource.calendar.attendance', 'pos.order',
            'pos.order.line', 'pos.payment', 'pos.payment.method', 'pos.printer',
            'pos.category', 'pos.bill', 'res.company', 'account.tax', 'account.tax.group',
            'product.template', 'product.product', 'product.attribute', 'product.attribute.custom.value',
            'product.template.attribute.line', 'product.template.attribute.value',
            'product.combo', 'product.combo.item', 'res.users', 'res.partner',
            'product.uom', 'decimal.precision', 'uom.uom', 'res.country', 'res.country.state',
            'res.lang', 'product.category', 'product.pricelist', 'product.pricelist.item',
            'account.cash.rounding', 'account.fiscal.position', 'res.currency', 'pos.note',
            'product.tag', 'ir.module.module', 'account.move', 'account.account',
            'pos.product.template.snooze', 'pos.prep.order', 'pos.prep.line',
        ]

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [('id', '=', self.id)]

    @api.model
    def _load_pos_data_fields(self, config):
        return [
            'id', 'name', 'user_id', 'config_id', 'start_at', 'stop_at',
            'payment_method_ids', 'state', 'access_token',
        ]

    def load_data(self, models_to_load):
        response = {}
        response['pos.session'] = self._load_pos_data_search_read(response, self.config_id)

        for model in self._load_pos_data_models(self.config_id):
            if models_to_load and model not in models_to_load:
                continue

            try:
                response[model] = self.env[model]._load_pos_data_search_read(response, self.config_id)
            except AccessError as e:
                response[model] = []
                _logger.info("Could not load model %s due to AccessError: %s", model, e)

        return response

    def load_data_params(self):
        response = {}
        fields = self._load_pos_data_fields(self.config_id)
        response['pos.session'] = {
            'fields': fields,
            'relations': self._load_pos_data_relations('pos.session', fields),
        }

        for model in self._load_pos_data_models(self.config_id):
            fields = self.env[model]._load_pos_data_fields(self.config_id)
            response[model] = {
                'fields': fields,
                'relations': self._load_pos_data_relations(model, fields),
            }

        return response

    def filter_local_data(self, models_to_filter):
        response = {}
        for model, ids in models_to_filter.items():
            existing_records = self.env[model].browse(ids).exists()

            non_existent_ids = set(ids) - set(existing_records.ids)
            inactive_ids = set(existing_records._unrelevant_records(self.config_id))

            response[model] = list(non_existent_ids | inactive_ids)
        return response

    def delete_opening_control_session(self):
        self.ensure_one()
        if not self.exists():
            return {
                'status': 'success',
            }
        if self.state != 'opening_control' or len(self.order_ids) > 0:
            raise UserError(_("You can only cancel a session that is in opening control state and has no orders."))
        self._delete_session()
        return {
            'status': 'success',
        }

    def _delete_session(self):
        self.sudo().unlink()

    def get_pos_ui_product_pricelist_item_by_product(self, product_tmpl_ids, product_ids, config_id):
        pos_config = self.env['pos.config'].browse(config_id)
        pricelist_fields = self.env['product.pricelist']._load_pos_data_fields(pos_config)
        pricelist_item_fields = self.env['product.pricelist.item']._load_pos_data_fields(pos_config)
        today = fields.Date.context_today(self)
        pricelist_item_domain = [
            '&',
            ('pricelist_id', 'in', self.config_id._get_available_pricelists().ids),
            *self.env['product.pricelist.item']._check_company_domain(self.company_id),
            '|',
            '&', ('product_id', '=', False), ('product_tmpl_id', 'in', product_tmpl_ids),
            ('product_id', 'in', product_ids),
            '|', ('date_start', '=', False), ('date_start', '<=', today),
            '|', ('date_end', '=', False), ('date_end', '>=', today)]

        pricelist_item = self.env['product.pricelist.item'].search(pricelist_item_domain)
        pricelist = pricelist_item.pricelist_id

        return {
            'product.pricelist.item': pricelist_item.read(pricelist_item_fields, load=False),
            'product.pricelist': pricelist.read(pricelist_fields, load=False),
        }

    @api.depends('currency_id', 'company_id.currency_id')
    def _compute_is_in_company_currency(self):
        for session in self:
            session.is_in_company_currency = session.currency_id == session.company_id.currency_id

    @api.depends('order_ids.payment_ids.amount')
    def _compute_total_payments_amount(self):
        result = self.env['pos.payment']._read_group(self._get_captured_payments_domain(), ['session_id'], ['amount:sum'])
        session_amount_map = {session.id: amount for session, amount in result}
        for session in self:
            session.total_payments_amount = session_amount_map.get(session.id) or 0

    def _search_move_ids(self, operator, value):
        moves = self.env['account.move'].search([('id', operator, value)])
        return [
            '|',
            ('sales_move_id', 'in', moves.ids),
            ('refunds_move_id', 'in', moves.ids),
        ]

    @api.depends('sales_move_id', 'refunds_move_id')
    def _compute_move_ids(self):
        for session in self:
            session.move_ids = session.sales_move_id | session.refunds_move_id

    def _compute_order_count(self):
        orders_data = self.env['pos.order']._read_group([('session_id', 'in', self.ids)], ['session_id'], ['__count'])
        sessions_data = {session.id: count for session, count in orders_data}
        for session in self:
            session.order_count = sessions_data.get(session.id, 0)

    @api.constrains('config_id')
    def _check_pos_config(self):
        onboarding_creation = self.env.context.get('onboarding_creation', False)
        if not onboarding_creation and self.search_count([
                ('state', '!=', 'closed'),
                ('config_id', '=', self.config_id.id),
                ('rescue', '=', False),
            ]) > 1:
            raise ValidationError(_("Another session is already opened for this point of sale."))

    @api.constrains('start_at')
    def _check_start_date(self):
        for record in self:
            journal = record.config_id.journal_id
            company = journal.company_id
            start_date = record.start_at.date()
            violated_lock_dates = company._get_violated_lock_dates(start_date, True, journal)
            if violated_lock_dates:
                raise ValidationError(_("You cannot create a session starting before: %(lock_date_info)s",
                                        lock_date_info=self.env['res.company']._format_lock_dates(violated_lock_dates)))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            config_id = vals.get('config_id') or self.env.context.get('default_config_id')
            if not config_id:
                raise UserError(_("You should assign a Point of Sale to your session."))

            # journal_id is not required on the pos_config because it does not
            # exists at the installation. If nothing is configured at the
            # installation we do the minimal configuration. Impossible to do in
            # the .xml files as the CoA is not yet installed.
            vals.update(self._get_default_session_vals(config_id))

        if self.env.user.has_group('point_of_sale.group_pos_user'):
            sessions = super(PosSession, self.sudo()).create(vals_list)
        else:
            sessions = super().create(vals_list)

        return sessions

    @api.model
    def _get_default_session_vals(self, config_id):
        return {'config_id': config_id}

    def get_session_orders(self):
        today = fields.Date.context_today(self)
        return self.order_ids.filtered(lambda o:
            not (o.preset_time and o.preset_time.date() > today),
        )

    def get_order_count_by_preset(self):
        orders = self.order_ids.filtered(lambda o: o.state != 'cancel' and o.preset_id and o.preset_time and o.preset_time > fields.Datetime.now())
        orders_by_preset = {}
        for order in orders:
            if order.preset_id.id not in orders_by_preset:
                orders_by_preset[order.preset_id.id] = {
                    'id': order.preset_id.id,
                    'name': order.preset_id.name,
                    'count': 0,
                }
            orders_by_preset[order.preset_id.id]['count'] += 1
        return list(orders_by_preset.values())

    def close_session_from_ui(self, payment_method_closing={}):
        """
        Main entry point for closing a session from the UI. It will
        perform all necessary checks and operations to close the session
        """
        self.ensure_one()
        if any(order.state == 'draft' for order in self.get_session_orders()):
            return {
                'status': False,
                'type': 'draft_orders',
                'message': _("You cannot close the POS while there are still draft orders for the day."),
                'redirect': False,
            }

        if self.state == 'closed':
            return {
                'status': False,
                'type': 'session_already_closed',
                'message': _("This session is already closed."),
                'redirect': True,
            }

        self.config_id.close_session_snoozes()
        future_orders = self.order_ids.filtered_domain([
            ('preset_time', '!=', False),
            ('preset_time', '>', fields.Datetime.now()),
            ('state', '=', 'draft'),
        ])
        future_orders.session_id = False

        self.with_company(self.company_id)._validate_session_accounting()
        self._handle_bank_payment_method_difference(payment_method_closing)
        self._handle_cash_statement_entries(payment_method_closing)

        statement = self.bank_statement_id
        if statement:
            statement._compute_balance_end_real()

        if self.config_id.order_edit_tracking:
            edited_orders = self.get_session_orders().filtered(lambda o: o.is_edited)
            if len(edited_orders) > 0:
                order_links = Markup().join(
                    Markup("<li>%s</li>") % order._get_html_link() for order in edited_orders
                )
                body = _(
                    "Edited order(s) during the session:%s",
                    Markup("<br/><ul>%s</ul>") % order_links,
                )
                self.message_post(body=body)

        if self.env.user.email:
            self.post_close_register_message()

        self.write({
            'state': 'closed',
            'stop_at': self.stop_at or fields.Datetime.now(),
        })
        self.order_ids.write({'state': 'done'})
        self.env.flush_all()  # ensure sale.report is up to date
        return {'status': True}

    def post_close_register_message(self):
        self.message_post(body=_('Closed Register'), author_id=self._get_message_author().id)

    def _get_message_author(self):
        return self.env.user.partner_id

    def get_cash_in_out_list(self):
        if not self.env.user.has_group('point_of_sale.group_pos_user'):
            raise AccessError(_("You don't have the access rights to get the cash in/out list."))
        cash_in_count = 0
        cash_out_count = 0
        cash_in_out_list = []
        for cash_move in self.sudo().bank_statement_line_ids.sorted('create_date'):
            if cash_move.amount > 0:
                cash_in_count += 1
                name = f'Cash in {cash_in_count}'
            else:
                cash_out_count += 1
                name = f'Cash out {cash_out_count}'
            cash_in_out_list.append({
                'name': cash_move.payment_ref or name,
                'amount': cash_move.amount,
                'id': cash_move.id,
                'date': cash_move.create_date,
                'cashier_name': cash_move.partner_id.name,
            })
        return cash_in_out_list

    def get_closing_control_data(self):
        if not self.env.user.has_group('point_of_sale.group_pos_user'):
            raise AccessError(_("You don't have the access rights to get the point of sale closing control data."))
        self.ensure_one()
        orders = self._get_order_for_session_closing()
        payments = orders.payment_ids.filtered(lambda p: p.payment_method_id.type != "pay_later")
        cash_pm = self.config_id._get_cash_payment_method()
        cash_payments = payments.filtered_domain([
            ('payment_method_id', '=', cash_pm.id),
            ('pos_order_id.is_singly_invoiced', '=', False),
        ])
        cash_payments_summary = sum(cash_payments.mapped('amount'))
        non_cash_payment_method_ids = self.payment_method_ids - cash_pm
        non_cash_payments_grouped_by_method_id = {pm: orders.payment_ids.filtered(lambda p: p.payment_method_id == pm) for pm in non_cash_payment_method_ids}
        ending_cash_balance = self.bank_statement_id.balance_end or 0
        cash_in_out_list = self.get_cash_in_out_list()
        opening_amount = self.config_id._get_opening_balance()

        return {
            'orders_details': {
                'quantity': len(orders),
                'amount': sum(orders.mapped('amount_total')),
            },
            'opening_notes': self.opening_notes or "",
            'default_cash_details': {
                'name': cash_pm.name,
                'amount': ending_cash_balance + cash_payments_summary,
                'opening': opening_amount,
                'payment_amount': cash_payments_summary,
                'moves': cash_in_out_list,
                'id': cash_pm.id,
            } if cash_pm else {},
            'non_cash_payment_methods': [{
                'name': pm.name,
                'amount': sum(non_cash_payments_grouped_by_method_id[pm].mapped('amount')),
                'number': len(non_cash_payments_grouped_by_method_id[pm]),
                'id': pm.id,
                'type': pm.type,
            } for pm in non_cash_payment_method_ids],
            'is_manager': self.env.user.has_group("point_of_sale.group_pos_manager"),
<<<<<<< aa9097425137afa3543c9e145f9ca4fc0a4d4a98
            'amount_authorized_diff': self.config_id.amount_authorized_diff if self.config_id.set_maximum_difference else None,
||||||| 5663509fe5caa1191fafcea3b3879dcef9ceca8f
            'amount_authorized_diff': self.config_id.amount_authorized_diff if self.config_id.set_maximum_difference else None
        }

    def _create_balancing_line(self, data, balancing_account, amount_to_balance):
        if not self.company_id.currency_id.is_zero(amount_to_balance):
            balancing_vals = self._prepare_balancing_line_vals(amount_to_balance, self.move_id, balancing_account)
            MoveLine = data.get('MoveLine')
            MoveLine.create(balancing_vals)
        return data

    def _prepare_balancing_line_vals(self, imbalance_amount, move, balancing_account):
        partial_vals = {
            'name': _('Difference at closing PoS session'),
            'account_id': balancing_account.id,
            'move_id': move.id,
            'partner_id': False,
        }
        # `imbalance_amount` is already in terms of company currency so it is the amount_converted
        # param when calling `_credit_amounts`. amount param will be the converted value of
        # `imbalance_amount` from company currency to the session currency.
        imbalance_amount_session = 0
        if (not self.is_in_company_currency):
            imbalance_amount_session = self.company_id.currency_id._convert(imbalance_amount, self.currency_id, self.company_id)
        return self._credit_amounts(partial_vals, imbalance_amount_session, imbalance_amount)

    def _get_balancing_account(self):
        return (
            self.company_id.account_default_pos_receivable_account_id
            or self.env['res.partner']._fields['property_account_receivable_id'].get_company_dependent_fallback(self.env['res.partner'])
            or self.env['account.account']
        )

    def _create_account_move(self, balancing_account=False, amount_to_balance=0, bank_payment_method_diffs=None):
        """ Create account.move and account.move.line records for this session.

        Side-effects include:
            - setting self.move_id to the created account.move record
            - reconciling cash receivable lines, invoice receivable lines and stock output lines
        """
        account_move = self.env['account.move'].create({
            'journal_id': self.config_id.journal_id.id,
            'date': fields.Date.context_today(self),
            'ref': self.name,
        })
        self.write({'move_id': account_move.id})
        data = self._get_account_move_data(bank_payment_method_diffs)
        if balancing_account and amount_to_balance:
            data = self._create_balancing_line(data, balancing_account, amount_to_balance)
        return data

    def _get_account_move_data(self, bank_payment_method_diffs):
        data = {'bank_payment_method_diffs': bank_payment_method_diffs or {}}
        data = self._accumulate_amounts(data)
        data = self._create_non_reconciliable_move_lines(data)
        data = self._create_bank_payment_moves(data)
        data = self._create_pay_later_receivable_lines(data)
        data = self._create_cash_statement_lines_and_cash_move_lines(data)
        data = self._create_invoice_receivable_lines(data)
        return data

    def _accumulate_amounts(self, data):
        # Accumulate the amounts for each accounting lines group
        # Each dict maps `key` -> `amounts`, where `key` is the group key.
        # E.g. `combine_receivables_bank` is derived from pos.payment records
        # in the self.order_ids with group key of the `payment_method_id`
        # field of the pos.payment record.
        AccountTax = self.env['account.tax']
        amounts = lambda: {'amount': 0.0, 'amount_converted': 0.0}
        tax_amounts = lambda: {'amount': 0.0, 'amount_converted': 0.0, 'base_amount': 0.0, 'base_amount_converted': 0.0}
        split_receivables_bank = defaultdict(amounts)
        split_receivables_cash = defaultdict(amounts)
        split_receivables_pay_later = defaultdict(amounts)
        combine_receivables_bank = defaultdict(amounts)
        combine_receivables_cash = defaultdict(amounts)
        combine_receivables_pay_later = defaultdict(amounts)
        combine_invoice_receivables = defaultdict(amounts)
        split_invoice_receivables = defaultdict(amounts)
        sales = defaultdict(amounts)
        taxes = defaultdict(tax_amounts)
        rounding_difference = {'amount': 0.0, 'amount_converted': 0.0}
        # Track the receivable lines of the order's invoice payment moves for reconciliation
        # These receivable lines are reconciled to the corresponding invoice receivable lines
        # of this session's move_id.
        combine_inv_payment_receivable_lines = defaultdict(lambda: self.env['account.move.line'])
        split_inv_payment_receivable_lines = defaultdict(lambda: self.env['account.move.line'])
        pos_receivable_account = self.company_id.account_default_pos_receivable_account_id
        currency_rounding = self.currency_id.rounding
        closed_orders = self._get_order_for_session_closing()
        for order in closed_orders:
            order_is_invoiced = order.is_invoiced
            for payment in order.payment_ids:
                amount = payment.amount
                if float_is_zero(amount, precision_rounding=currency_rounding):
                    continue
                date = payment.payment_date
                payment_method = payment.payment_method_id
                is_split_payment = payment.payment_method_id.split_transactions
                payment_type = payment_method.type

                # If not pay_later, we create the receivable vals for both invoiced and uninvoiced orders.
                #   Separate the split and aggregated payments.
                # Moreover, if the order is invoiced, we create the pos receivable vals that will balance the
                # pos receivable lines from the invoice payments.
                if payment_type != 'pay_later':
                    if is_split_payment and payment_type == 'cash':
                        split_receivables_cash[payment] = self._update_amounts(split_receivables_cash[payment], {'amount': amount}, date)
                    elif not is_split_payment and payment_type == 'cash':
                        combine_receivables_cash[payment_method] = self._update_amounts(combine_receivables_cash[payment_method], {'amount': amount}, date)
                    elif is_split_payment and payment_type == 'bank':
                        split_receivables_bank[payment] = self._update_amounts(split_receivables_bank[payment], {'amount': amount}, date)
                    elif not is_split_payment and payment_type == 'bank':
                        combine_receivables_bank[payment_method] = self._update_amounts(combine_receivables_bank[payment_method], {'amount': amount}, date)

                    # Create the vals to create the pos receivables that will balance the pos receivables from invoice payment moves.
                    if order_is_invoiced:
                        if is_split_payment:
                            split_inv_payment_receivable_lines[payment] |= payment.account_move_id.line_ids.filtered(lambda line: line.account_id == pos_receivable_account)
                            split_invoice_receivables[payment] = self._update_amounts(split_invoice_receivables[payment], {'amount': payment.amount}, order.date_order)
                        else:
                            combine_inv_payment_receivable_lines[payment_method] |= payment.account_move_id.line_ids.filtered(lambda line: line.account_id == pos_receivable_account)
                            combine_invoice_receivables[payment_method] = self._update_amounts(combine_invoice_receivables[payment_method], {'amount': payment.amount}, order.date_order)

                # If pay_later, we create the receivable lines.
                #   if split, with partner
                #   Otherwise, it's aggregated (combined)
                # But only do if order is *not* invoiced because no account move is created for pay later invoice payments.
                if payment_type == 'pay_later' and not order_is_invoiced:
                    if is_split_payment:
                        split_receivables_pay_later[payment] = self._update_amounts(split_receivables_pay_later[payment], {'amount': amount}, date)
                    elif not is_split_payment:
                        combine_receivables_pay_later[payment_method] = self._update_amounts(combine_receivables_pay_later[payment_method], {'amount': amount}, date)

            if not order_is_invoiced:
                base_lines = order.with_context(linked_to_pos=True)._prepare_tax_base_line_values()
                AccountTax._add_tax_details_in_base_lines(base_lines, order.company_id)
                AccountTax._round_base_lines_tax_details(base_lines, order.company_id)
                AccountTax._add_accounting_data_in_base_lines_tax_details(base_lines, order.company_id, include_caba_tags=True)
                tax_results = AccountTax._prepare_tax_lines(base_lines, order.company_id)
                total_amount_currency = 0.0
                for base_line, to_update in tax_results['base_lines_to_update']:
                    # Combine sales/refund lines
                    sale_vals_dict = self._get_sale_key(base_line)
                    sale_key = frozendict(sale_vals_dict)
                    total_amount_currency += to_update['amount_currency']
                    sales[sale_key] = self._update_amounts(
                        sales[sale_key],
                        {
                            'amount': to_update['amount_currency'],
                            'amount_converted': to_update['balance'],
                        },
                        order.date_order,
                    )
                    if self.config_id._is_quantities_set():
                        sales[sale_key].setdefault('quantity', 0)
                        sales[sale_key]['quantity'] += base_line['quantity']

                # Combine tax lines
                for tax_line in tax_results['tax_lines_to_add']:
                    tax_key = (
                        tax_line['account_id'],
                        tax_line['tax_repartition_line_id'],
                        tuple(tax_line['tax_tag_ids'][0][2]),
                    )
                    total_amount_currency += tax_line['amount_currency']
                    taxes[tax_key] = self._update_amounts(
                        taxes[tax_key],
                        {
                            'amount': tax_line['amount_currency'],
                            'amount_converted': tax_line['balance'],
                            'base_amount': tax_line['tax_base_amount']
                        },
                        order.date_order,
                    )

                if self.config_id.cash_rounding:
                    diff = order.amount_paid + total_amount_currency
                    rounding_difference = self._update_amounts(rounding_difference, {'amount': diff}, order.date_order)

                # Increasing current partner's customer_rank
                partners = (order.partner_id | order.partner_id.commercial_partner_id)
                partners._increase_rank('customer_rank')

        MoveLine = self.env['account.move.line'].with_context(check_move_validity=False, skip_invoice_sync=True)

        data.update({
            'taxes':                               taxes,
            'sales':                               sales,
            'split_receivables_bank':              split_receivables_bank,
            'combine_receivables_bank':            combine_receivables_bank,
            'split_receivables_cash':              split_receivables_cash,
            'combine_receivables_cash':            combine_receivables_cash,
            'combine_invoice_receivables':         combine_invoice_receivables,
            'split_receivables_pay_later':         split_receivables_pay_later,
            'combine_receivables_pay_later':       combine_receivables_pay_later,
            'combine_inv_payment_receivable_lines': combine_inv_payment_receivable_lines,
            'rounding_difference':                 rounding_difference,
            'MoveLine':                            MoveLine,
            'split_invoice_receivables': split_invoice_receivables,
            'split_inv_payment_receivable_lines': split_inv_payment_receivable_lines,
        })
        return data

    def _get_rounding_difference_vals(self, amount, amount_converted):
        if not self.config_id.cash_rounding:
            return {}

        compare_result = float_compare(0.0, amount, precision_rounding=self.currency_id.rounding)
        if not compare_result:
            return {}

        partial_args = {'name': 'Rounding line', 'move_id': self.move_id.id}
        if compare_result > 0:    # loss
            partial_args['account_id'] = self.config_id.rounding_method.loss_account_id.id
            return self._debit_amounts(partial_args, -amount, -amount_converted)

        partial_args['account_id'] = self.config_id.rounding_method.profit_account_id.id
        return self._credit_amounts(partial_args, amount, amount_converted)

    def _create_non_reconciliable_move_lines(self, data):
        # Create account.move.line records for
        #   - sales
        #   - taxes
        #   - non-cash split receivables (not for automatic reconciliation)
        #   - non-cash combine receivables (not for automatic reconciliation)
        taxes = data.get('taxes')
        sales = data.get('sales')
        rounding_difference = data.get('rounding_difference')
        MoveLine = data.get('MoveLine')

        tax_vals = [self._get_tax_vals(key, amounts['amount'], amounts['amount_converted'], amounts['base_amount_converted']) for key, amounts in taxes.items()]
        # Check if all taxes lines have account_id assigned. If not, there are repartition lines of the tax that have no account_id.
        tax_names_no_account = [line['name'] for line in tax_vals if not line['account_id']]
        if tax_names_no_account:
            raise UserError(_(
                'Unable to close and validate the session.\n'
                'Please set corresponding tax account in each repartition line of the following taxes: \n%s',
                ', '.join(tax_names_no_account)
            ))

        rounding_vals = []
        if not float_is_zero(rounding_difference['amount'], precision_rounding=self.currency_id.rounding) or not float_is_zero(rounding_difference['amount_converted'], precision_rounding=self.currency_id.rounding):
            rounding_vals = [self._get_rounding_difference_vals(rounding_difference['amount'], rounding_difference['amount_converted'])]

        MoveLine.create(tax_vals + rounding_vals)
        move_line_ids = MoveLine.create(list(starmap(self._get_sale_vals, sales.items())))
        for key, ml_id in zip(sales.keys(), move_line_ids.ids):
            sales[key]['move_line_id'] = ml_id

        return data

    def _create_bank_payment_moves(self, data):
        combine_receivables_bank = data.get('combine_receivables_bank')
        split_receivables_bank = data.get('split_receivables_bank')
        bank_payment_method_diffs = data.get('bank_payment_method_diffs')
        MoveLine = data.get('MoveLine')
        payment_method_to_receivable_lines = {}
        payment_to_receivable_lines = {}
        for payment_method, amounts in combine_receivables_bank.items():
            combine_receivable_line = MoveLine.create(self._get_combine_receivable_vals(payment_method, amounts['amount'], amounts['amount_converted']))
            payment_receivable_line = self._create_combine_account_payment(payment_method, amounts, diff_amount=bank_payment_method_diffs.get(payment_method.id) or 0)
            payment_method_to_receivable_lines[payment_method] = combine_receivable_line | payment_receivable_line

        for payment, amounts in split_receivables_bank.items():
            split_receivable_line = MoveLine.create(self._get_split_receivable_vals(payment, amounts['amount'], amounts['amount_converted']))
            payment_receivable_line = self._create_split_account_payment(payment, amounts)
            payment_to_receivable_lines[payment] = split_receivable_line | payment_receivable_line

        for bank_payment_method in self.payment_method_ids.filtered(lambda pm: pm.type == 'bank' and pm.split_transactions):
            self._create_diff_account_move_for_split_payment_method(bank_payment_method, bank_payment_method_diffs.get(bank_payment_method.id) or 0)

        data['payment_method_to_receivable_lines'] = payment_method_to_receivable_lines
        data['payment_to_receivable_lines'] = payment_to_receivable_lines
        return data

    def _create_pay_later_receivable_lines(self, data):
        MoveLine = data.get('MoveLine')
        combine_receivables_pay_later = data.get('combine_receivables_pay_later')
        split_receivables_pay_later = data.get('split_receivables_pay_later')
        vals = []
        for payment_method, amounts in combine_receivables_pay_later.items():
            vals.append(self._get_combine_receivable_vals(payment_method, amounts['amount'], amounts['amount_converted']))
        for payment, amounts in split_receivables_pay_later.items():
            vals.append(self._get_split_receivable_vals(payment, amounts['amount'], amounts['amount_converted']))
        for val in vals:
            # Entries related to a `pay_later` payment method should not be excluded from follow-ups.
            val['no_followup'] = False
        data['pay_later_move_lines'] = MoveLine.create(vals)
        return data

    def _ensure_payment_outstanding_account(self, payment):
        # In community the outstanding account is computed on the creation of account.payment records
        if not payment.outstanding_account_id and self.env['account.move']._get_invoice_in_payment_state() == 'in_payment':
            payment.force_outstanding_account_id = payment._get_outstanding_account(payment.payment_type)

    def _create_combine_account_payment(self, payment_method, amounts, diff_amount):
        outstanding_account = payment_method.outstanding_account_id
        destination_account = self._get_receivable_account(payment_method)
        payment_type = "inbound"
        if self.currency_id.compare_amounts(amounts['amount'], 0) < 0:
            payment_type = 'outbound'

        account_payment = self.env['account.payment'].with_context(pos_payment=True).create({
            'amount': abs(amounts['amount']),
            'journal_id': payment_method.journal_id.id,
            'force_outstanding_account_id': outstanding_account.id,
            'destination_account_id': destination_account.id,
            'memo': _('Combine %(payment_method)s POS payments from %(session)s', payment_method=payment_method.name, session=self.name),
            'pos_payment_method_id': payment_method.id,
            'pos_session_id': self.id,
            'company_id': self.company_id.id,
            'payment_type': payment_type,
        })

        self._ensure_payment_outstanding_account(account_payment)
        account_payment.action_post()

        diff_amount_compare_to_zero = self.currency_id.compare_amounts(diff_amount, 0)
        if diff_amount_compare_to_zero != 0:
            self._apply_diff_on_account_payment_move(account_payment, payment_method, diff_amount)

        return account_payment.move_id.line_ids.filtered(lambda line: line.account_id == self._get_receivable_account(payment_method))

    def _apply_diff_on_account_payment_move(self, account_payment, payment_method, diff_amount):
        diff_vals = self._get_diff_vals(payment_method.id, diff_amount, account_payment.outstanding_account_id)
        if not diff_vals:
            return
        source_vals, dest_vals = diff_vals
        outstanding_line = account_payment.move_id.line_ids.filtered(lambda line: line.account_id.id == source_vals['account_id'])
        new_balance = outstanding_line.balance + self._amount_converter(diff_amount, self.stop_at, False)
        new_balance_compare_to_zero = self.currency_id.compare_amounts(new_balance, 0)
        account_payment.move_id.button_draft()
        account_payment.move_id.write({
            'line_ids': [
                Command.create(dest_vals),
                Command.update(outstanding_line.id, {
                    'debit': new_balance_compare_to_zero > 0 and new_balance or 0.0,
                    'credit': new_balance_compare_to_zero < 0 and -new_balance or 0.0
                })
            ]
        })
        account_payment.write({
            'amount': abs(new_balance),
        })
        account_payment.move_id.action_post()

    def _create_split_account_payment(self, payment, amounts):
        payment_method = payment.payment_method_id
        if not payment_method.journal_id:
            return self.env['account.move.line']
        outstanding_account = payment_method.outstanding_account_id
        accounting_partner = self.env["res.partner"]._find_accounting_partner(payment.partner_id)
        destination_account = accounting_partner.property_account_receivable_id
        payment_type = "inbound"
        if self.currency_id.compare_amounts(amounts['amount'], 0) < 0:
            payment_type = 'outbound'

        account_payment = self.env['account.payment'].create({
            'amount': abs(amounts['amount']),
            'partner_id': accounting_partner.id,
            'journal_id': payment_method.journal_id.id,
            'force_outstanding_account_id': outstanding_account.id,
            'destination_account_id': destination_account.id,
            'memo': _('%(payment_method)s POS payment of %(partner)s in %(session)s', payment_method=payment_method.name, partner=payment.partner_id.display_name, session=self.name),
            'pos_payment_method_id': payment_method.id,
            'pos_session_id': self.id,
            'payment_type': payment_type,
        })

        self._ensure_payment_outstanding_account(account_payment)
        account_payment.action_post()
        return account_payment.move_id.line_ids.filtered(lambda line: line.account_id == accounting_partner.property_account_receivable_id)

    def _create_cash_statement_lines_and_cash_move_lines(self, data):
        # Create the split and combine cash statement lines and account move lines.
        # `split_cash_statement_lines` maps `journal` -> split cash statement lines
        # `combine_cash_statement_lines` maps `journal` -> combine cash statement lines
        # `split_cash_receivable_lines` maps `journal` -> split cash receivable lines
        # `combine_cash_receivable_lines` maps `journal` -> combine cash receivable lines
        MoveLine = data.get('MoveLine')
        split_receivables_cash = data.get('split_receivables_cash')
        combine_receivables_cash = data.get('combine_receivables_cash')

        # handle split cash payments
        split_cash_statement_line_vals = []
        split_cash_receivable_vals = []
        for payment, amounts in split_receivables_cash.items():
            journal_id = payment.payment_method_id.journal_id
            split_cash_statement_line_vals.append(
                self._get_split_statement_line_vals(
                    journal_id,
                    amounts['amount'],
                    payment
                )
            )
            split_cash_receivable_vals.append(
                self._get_split_receivable_vals(
                    payment,
                    amounts['amount'],
                    amounts['amount_converted']
                )
            )
        # handle combine cash payments
        combine_cash_statement_line_vals = []
        combine_cash_receivable_vals = []
        for payment_method, amounts in combine_receivables_cash.items():
            if not float_is_zero(amounts['amount'] , precision_rounding=self.currency_id.rounding):
                combine_cash_statement_line_vals.append(
                    self._get_combine_statement_line_vals(
                        payment_method.journal_id,
                        amounts['amount'],
                        payment_method
                    )
                )
                combine_cash_receivable_vals.append(
                    self._get_combine_receivable_vals(
                        payment_method,
                        amounts['amount'],
                        amounts['amount_converted']
                    )
                )

        # create the statement lines and account move lines
        BankStatementLine = self.env['account.bank.statement.line'].with_context(no_retrieve_partner=True)
        split_cash_statement_lines = {}
        combine_cash_statement_lines = {}
        split_cash_receivable_lines = {}
        combine_cash_receivable_lines = {}
        split_cash_statement_lines = BankStatementLine.create(split_cash_statement_line_vals).mapped('move_id.line_ids').filtered(lambda line: line.account_id.account_type == 'asset_receivable')
        combine_cash_statement_lines = BankStatementLine.create(combine_cash_statement_line_vals).mapped('move_id.line_ids').filtered(lambda line: line.account_id.account_type == 'asset_receivable')
        split_cash_receivable_lines = MoveLine.create(split_cash_receivable_vals)
        combine_cash_receivable_lines = MoveLine.create(combine_cash_receivable_vals)

        data.update(
            {'split_cash_statement_lines':    split_cash_statement_lines,
             'combine_cash_statement_lines':  combine_cash_statement_lines,
             'split_cash_receivable_lines':   split_cash_receivable_lines,
             'combine_cash_receivable_lines': combine_cash_receivable_lines
             })
        return data

    def _create_invoice_receivable_lines(self, data):
        # Create invoice receivable lines for this session's move_id.
        # Keep reference of the invoice receivable lines because
        # they are reconciled with the lines in combine_inv_payment_receivable_lines
        MoveLine = data.get('MoveLine')
        combine_invoice_receivables = data.get('combine_invoice_receivables')
        split_invoice_receivables = data.get('split_invoice_receivables')

        combine_invoice_receivable_vals = defaultdict(list)
        split_invoice_receivable_vals = defaultdict(list)
        combine_invoice_receivable_lines = {}
        split_invoice_receivable_lines = {}
        for payment_method, amounts in combine_invoice_receivables.items():
            combine_invoice_receivable_vals[payment_method].append(self._get_invoice_receivable_vals(amounts['amount'], amounts['amount_converted']))
        for payment, amounts in split_invoice_receivables.items():
            split_invoice_receivable_vals[payment].append(self._get_invoice_receivable_vals(amounts['amount'], amounts['amount_converted']))
        for payment_method, vals in combine_invoice_receivable_vals.items():
            receivable_lines = MoveLine.create(vals)
            combine_invoice_receivable_lines[payment_method] = receivable_lines
        for payment, vals in split_invoice_receivable_vals.items():
            receivable_lines = MoveLine.create(vals)
            split_invoice_receivable_lines[payment] = receivable_lines

        data.update({'combine_invoice_receivable_lines': combine_invoice_receivable_lines})
        data.update({'split_invoice_receivable_lines': split_invoice_receivable_lines})
        return data

    def _reconcile_account_move_lines(self, data):
        # reconcile cash receivable lines
        split_cash_statement_lines = data.get('split_cash_statement_lines')
        combine_cash_statement_lines = data.get('combine_cash_statement_lines')
        split_cash_receivable_lines = data.get('split_cash_receivable_lines')
        combine_cash_receivable_lines = data.get('combine_cash_receivable_lines')
        combine_inv_payment_receivable_lines = data.get('combine_inv_payment_receivable_lines')
        split_inv_payment_receivable_lines = data.get('split_inv_payment_receivable_lines')
        combine_invoice_receivable_lines = data.get('combine_invoice_receivable_lines')
        split_invoice_receivable_lines = data.get('split_invoice_receivable_lines')
        payment_method_to_receivable_lines = data.get('payment_method_to_receivable_lines')
        payment_to_receivable_lines = data.get('payment_to_receivable_lines')

        all_lines = (
              split_cash_statement_lines
            | combine_cash_statement_lines
            | split_cash_receivable_lines
            | combine_cash_receivable_lines
        )
        all_lines.filtered(lambda line: line.move_id.state != 'posted').move_id._post(soft=False)

        lines_by_account = all_lines.filtered(lambda l: not l.reconciled).grouped('account_id')
        for lines in lines_by_account.values():
            lines.with_context(no_cash_basis=True).reconcile()

        for payment_method, lines in payment_method_to_receivable_lines.items():
            lines.filtered(lambda line: not line.reconciled).with_context(no_cash_basis=True).reconcile()

        for payment, lines in payment_to_receivable_lines.items():
            lines.filtered(lambda line: not line.reconciled).with_context(no_cash_basis=True).reconcile()

        # Reconcile invoice payments' receivable lines.
        for payment_method in combine_inv_payment_receivable_lines:
            lines = combine_inv_payment_receivable_lines[payment_method] | combine_invoice_receivable_lines.get(payment_method, self.env['account.move.line'])
            lines.filtered(lambda line: not line.reconciled).with_context(no_cash_basis=True).reconcile()

        for payment in split_inv_payment_receivable_lines:
            lines = split_inv_payment_receivable_lines[payment] | split_invoice_receivable_lines.get(payment, self.env['account.move.line'])
            lines.filtered(lambda line: not line.reconciled).with_context(no_cash_basis=True).reconcile()

        return data

    def _get_split_receivable_vals(self, payment, amount, amount_converted):
        accounting_partner = self.env["res.partner"]._find_accounting_partner(payment.partner_id)
        if not accounting_partner:
            raise UserError(_("You have enabled the \"Identify Customer\" option for %(payment_method)s payment method,"
                              "but the order %(order)s does not contain a customer.",
                              payment_method=payment.payment_method_id.name,
                              order=payment.pos_order_id.name))
        partial_vals = {
            'account_id': accounting_partner.property_account_receivable_id.id,
            'move_id': self.move_id.id,
            'partner_id': accounting_partner.id,
            'name': '%s - %s' % (self.name, payment.payment_method_id.name),
        }
        return self._debit_amounts(partial_vals, amount, amount_converted)

    def _get_combine_receivable_vals(self, payment_method, amount, amount_converted):
        partial_vals = {
            'account_id': self._get_receivable_account(payment_method).id,
            'move_id': self.move_id.id,
            'name': '%s - %s' % (self.name, payment_method.name),
            'display_type': 'payment_term',
        }
        return self._debit_amounts(partial_vals, amount, amount_converted)

    def _get_invoice_receivable_vals(self, amount, amount_converted):
        partial_vals = {
            'account_id': self.company_id.account_default_pos_receivable_account_id.id,
            'move_id': self.move_id.id,
            'name': _('From invoice payments'),
            'display_type': 'payment_term',
        }
        return self._credit_amounts(partial_vals, amount, amount_converted)

    def _get_sale_key(self, base_line):
        return {
            # account
            'account_id': base_line['account_id'].id,
            # sign
            'sign': -1 if base_line['is_refund'] else 1,
            # for taxes
            'tax_ids': tuple(base_line['record'].tax_ids_after_fiscal_position.flatten_taxes_hierarchy().ids),
            'base_tag_ids': tuple(base_line['tax_tag_ids'].ids),
            'product_id': base_line['product_id'].id if self.config_id.use_closing_entry_by_product else False,
        }

    def _get_sale_vals(self, key, sale_vals):
        tax_ids = key['tax_ids']
        product_id = key['product_id']
        sign = key['sign']
        applied_taxes = self.env['account.tax'].browse(tax_ids)
        if product_id:
            product = self.env['product.product'].browse(product_id)
            product_name = product.display_name
            product_uom = product.uom_id.id
        else:
            product_name = ""
            product_uom = False
        title = _('Sales') if sign == 1 else _('Refund')
        name = _('%s untaxed', title)
        if applied_taxes:
            name = _('%(title)s %(product_name)s with %(taxes)s', title=title, product_name=product_name, taxes=', '.join([tax.name for tax in applied_taxes]))
        partial_vals = {
            'name': name,
            'account_id': key['account_id'],
            'move_id': self.move_id.id,
            'tax_ids': [(6, 0, tax_ids)],
            'tax_tag_ids': [(6, 0, key['base_tag_ids'])],
            'product_id': product_id,
            'display_type': 'product',
            'product_uom_id': product_uom,
            'currency_id': self.currency_id.id,
            'amount_currency': sale_vals['amount'],
            'balance': sale_vals['amount_converted'],
            'quantity': sale_vals.get('quantity', 1.00) * key['sign'],
        }
        return partial_vals

    def _get_tax_vals(self, key, amount, amount_converted, base_amount_converted):
        account_id, repartition_line_id, tag_ids = key
        tax_rep = self.env['account.tax.repartition.line'].browse(repartition_line_id)
        tax = tax_rep.tax_id
        return {
            'name': tax.name,
            'account_id': account_id,
            'move_id': self.move_id.id,
            'tax_base_amount': base_amount_converted,
            'tax_repartition_line_id': repartition_line_id,
            'tax_tag_ids': [(6, 0, tag_ids)],
            'display_type': 'tax',
            'currency_id': self.currency_id.id,
            'amount_currency': amount,
            'balance': amount_converted,
        }

    def _get_combine_statement_line_vals(self, journal, amount, payment_method):
        amount_values = self._prepare_statement_line_amount_values(journal, amount)
        return {
            'date': fields.Date.context_today(self),
            'payment_ref': self.name,
            'pos_session_id': self.id,
            'journal_id': journal.id,
            'counterpart_account_id': self._get_receivable_account(payment_method).id,
            **amount_values
        }

    def _get_split_statement_line_vals(self, journal, amount, payment):
        accounting_partner = self.env["res.partner"]._find_accounting_partner(payment.partner_id)
        amount_values = self._prepare_statement_line_amount_values(journal, amount)
        return {
            'date': fields.Date.context_today(self, timestamp=payment.payment_date),
            'payment_ref': payment.name,
            'pos_session_id': self.id,
            'journal_id': journal.id,
            'counterpart_account_id': accounting_partner.property_account_receivable_id.id,
            'partner_id': accounting_partner.id,
            **amount_values
        }

    def _prepare_statement_line_amount_values(self, journal, amount):
        journal_currency = journal.currency_id or self.company_id.currency_id
        if journal_currency == self.currency_id:
            return {'amount': amount}
        return {
            'amount': self.currency_id._convert(amount, journal_currency, self.company_id, self.stop_at),
            'amount_currency': amount,
            'foreign_currency_id': self.currency_id.id,
        }

    def _update_amounts(self, old_amounts, amounts_to_add, date, round=True, force_company_currency=False):
        """Responsible for adding `amounts_to_add` to `old_amounts` considering the currency of the session.

        ::

            old_amounts {                                                       new_amounts {
                amount                         amounts_to_add {                     amount
                amount_converted        +          amount               ->          amount_converted
               [base_amount                       [base_amount]                    [base_amount
                base_amount_converted]        }                                     base_amount_converted]
            }                                                                   }

        NOTE:
            - Notice that `amounts_to_add` does not have `amount_converted` field.
                This function is responsible in calculating the `amount_converted` from the
                `amount` of `amounts_to_add` which is used to update the values of `old_amounts`.
            - Values of `amount` and/or `base_amount` should always be in session's currency [1].
            - Value of `amount_converted` should be in company's currency

        [1] Except when `force_company_currency` = True. It means that values in `amounts_to_add`
            is in company currency.

        :param dict old_amounts:
            Amounts to update
        :param dict amounts_to_add:
            Amounts used to update the old_amounts
        :param date date:
            Date used for conversion
        :param bool round:
            Same as round parameter of `res.currency._convert`.
            Defaults to True because that is the default of `res.currency._convert`.
            We put it to False if we want to round globally.
        :param bool force_company_currency:
            If True, the values in amounts_to_add are in company's currency.
            Defaults to False because it is only used to anglo-saxon lines.

        :returns: new amounts combining the values of `old_amounts` and `amounts_to_add`.
        :rtype: dict
        """
        # make a copy of the old amounts
        new_amounts = { **old_amounts }

        amount = amounts_to_add.get('amount')
        if self.is_in_company_currency or force_company_currency:
            amount_converted = amount
        else:
            amount_converted = self._amount_converter(amount, date, round)

        # update amount and amount converted
        new_amounts['amount'] += amount
        new_amounts['amount_converted'] += amount_converted

        # consider base_amount if present

        if amounts_to_add.get('base_amount'):
            base_amount = amounts_to_add.get('base_amount')

            # update base_amount and base_amount_converted
            new_amounts['base_amount'] += base_amount
            new_amounts['base_amount_converted'] += base_amount

        return new_amounts

    def _credit_amounts(self, partial_move_line_vals, amount, amount_converted, force_company_currency=False):
        """ `partial_move_line_vals` is completed by `crediting` the given amounts.

        NOTE Amounts in PoS are in the currency of journal_id in the session.config_id.
        This means that amount fields in any pos record are actually equivalent to amount_currency
        in account module. Understanding this basic is important in correctly assigning values for
        'amount' and 'amount_currency' in the account.move.line record.

        :param dict partial_move_line_vals:
            initial values in creating account.move.line
        :param float amount:
            amount derived from pos.payment, pos.order, or pos.order.line records
        :param float amount_converted:
            converted value of `amount` from the given `session_currency` to company currency

        :return: complete values for creating 'amount.move.line' record
        :rtype: dict
        """
        if self.is_in_company_currency or force_company_currency:
            additional_field = {}
        else:
            additional_field = {
                'amount_currency': -amount,
                'currency_id': self.currency_id.id,
            }
        return {
            'debit': -amount_converted if amount_converted < 0.0 else 0.0,
            'credit': amount_converted if amount_converted > 0.0 else 0.0,
            **partial_move_line_vals,
            **additional_field,
        }

    def _debit_amounts(self, partial_move_line_vals, amount, amount_converted, force_company_currency=False):
        """ `partial_move_line_vals` is completed by `debiting` the given amounts.

        See _credit_amounts docs for more details.
        """
        if self.is_in_company_currency or force_company_currency:
            additional_field = {}
        else:
            additional_field = {
                'amount_currency': amount,
                'currency_id': self.currency_id.id,
            }
        return {
            'debit': amount_converted if amount_converted > 0.0 else 0.0,
            'credit': -amount_converted if amount_converted < 0.0 else 0.0,
            **partial_move_line_vals,
            **additional_field,
=======
            'amount_authorized_diff': self.config_id.amount_authorized_diff if self.config_id.set_maximum_difference else None
        }

    def _create_balancing_line(self, data, balancing_account, amount_to_balance):
        if not self.company_id.currency_id.is_zero(amount_to_balance):
            balancing_vals = self._prepare_balancing_line_vals(amount_to_balance, self.move_id, balancing_account)
            MoveLine = data.get('MoveLine')
            MoveLine.create(balancing_vals)
        return data

    def _prepare_balancing_line_vals(self, imbalance_amount, move, balancing_account):
        partial_vals = {
            'name': _('Difference at closing PoS session'),
            'account_id': balancing_account.id,
            'move_id': move.id,
            'partner_id': False,
        }
        # `imbalance_amount` is already in terms of company currency so it is the amount_converted
        # param when calling `_credit_amounts`. amount param will be the converted value of
        # `imbalance_amount` from company currency to the session currency.
        imbalance_amount_session = 0
        if (not self.is_in_company_currency):
            imbalance_amount_session = self.company_id.currency_id._convert(imbalance_amount, self.currency_id, self.company_id)
        return self._credit_amounts(partial_vals, imbalance_amount_session, imbalance_amount)

    def _get_balancing_account(self):
        return (
            self.company_id.account_default_pos_receivable_account_id
            or self.env['res.partner']._fields['property_account_receivable_id'].get_company_dependent_fallback(self.env['res.partner'])
            or self.env['account.account']
        )

    def _create_account_move(self, balancing_account=False, amount_to_balance=0, bank_payment_method_diffs=None):
        """ Create account.move and account.move.line records for this session.

        Side-effects include:
            - setting self.move_id to the created account.move record
            - reconciling cash receivable lines, invoice receivable lines and stock output lines
        """
        account_move = self.env['account.move'].create({
            'journal_id': self.config_id.journal_id.id,
            'date': fields.Date.context_today(self),
            'ref': self.name,
        })
        self.write({'move_id': account_move.id})
        data = self._get_account_move_data(bank_payment_method_diffs)
        if balancing_account and amount_to_balance:
            data = self._create_balancing_line(data, balancing_account, amount_to_balance)
        return data

    def _get_account_move_data(self, bank_payment_method_diffs):
        data = {'bank_payment_method_diffs': bank_payment_method_diffs or {}}
        data = self._accumulate_amounts(data)
        data = self._create_non_reconciliable_move_lines(data)
        data = self._create_bank_payment_moves(data)
        data = self._create_pay_later_receivable_lines(data)
        data = self._create_cash_statement_lines_and_cash_move_lines(data)
        data = self._create_invoice_receivable_lines(data)
        return data

    def _accumulate_amounts(self, data):
        # Accumulate the amounts for each accounting lines group
        # Each dict maps `key` -> `amounts`, where `key` is the group key.
        # E.g. `combine_receivables_bank` is derived from pos.payment records
        # in the self.order_ids with group key of the `payment_method_id`
        # field of the pos.payment record.
        AccountTax = self.env['account.tax']
        amounts = lambda: {'amount': 0.0, 'amount_converted': 0.0}
        tax_amounts = lambda: {'amount': 0.0, 'amount_converted': 0.0, 'base_amount': 0.0, 'base_amount_converted': 0.0}
        split_receivables_bank = defaultdict(amounts)
        split_receivables_cash = defaultdict(amounts)
        split_receivables_pay_later = defaultdict(amounts)
        combine_receivables_bank = defaultdict(amounts)
        combine_receivables_cash = defaultdict(amounts)
        combine_receivables_pay_later = defaultdict(amounts)
        combine_invoice_receivables = defaultdict(amounts)
        split_invoice_receivables = defaultdict(amounts)
        sales = defaultdict(amounts)
        taxes = defaultdict(tax_amounts)
        rounding_difference = {'amount': 0.0, 'amount_converted': 0.0}
        # Track the receivable lines of the order's invoice payment moves for reconciliation
        # These receivable lines are reconciled to the corresponding invoice receivable lines
        # of this session's move_id.
        combine_inv_payment_receivable_lines = defaultdict(lambda: self.env['account.move.line'])
        split_inv_payment_receivable_lines = defaultdict(lambda: self.env['account.move.line'])
        pos_receivable_account = self.company_id.account_default_pos_receivable_account_id
        currency_rounding = self.currency_id.rounding
        closed_orders = self._get_order_for_session_closing()
        for order in closed_orders:
            order_is_invoiced = order.is_invoiced
            for payment in order.payment_ids:
                amount = payment.amount
                if float_is_zero(amount, precision_rounding=currency_rounding):
                    continue
                date = payment.payment_date
                payment_method = payment.payment_method_id
                is_split_payment = payment.payment_method_id.split_transactions
                payment_type = payment_method.type

                # If not pay_later, we create the receivable vals for both invoiced and uninvoiced orders.
                #   Separate the split and aggregated payments.
                # Moreover, if the order is invoiced, we create the pos receivable vals that will balance the
                # pos receivable lines from the invoice payments.
                if payment_type != 'pay_later':
                    if is_split_payment and payment_type == 'cash':
                        split_receivables_cash[payment] = self._update_amounts(split_receivables_cash[payment], {'amount': amount}, date)
                    elif not is_split_payment and payment_type == 'cash':
                        combine_receivables_cash[payment_method] = self._update_amounts(combine_receivables_cash[payment_method], {'amount': amount}, date)
                    elif is_split_payment and payment_type == 'bank':
                        split_receivables_bank[payment] = self._update_amounts(split_receivables_bank[payment], {'amount': amount}, date)
                    elif not is_split_payment and payment_type == 'bank':
                        combine_receivables_bank[payment_method] = self._update_amounts(combine_receivables_bank[payment_method], {'amount': amount}, date)

                    # Create the vals to create the pos receivables that will balance the pos receivables from invoice payment moves.
                    if order_is_invoiced:
                        if is_split_payment:
                            split_inv_payment_receivable_lines[payment] |= payment.account_move_id.line_ids.filtered(lambda line: line.account_id == pos_receivable_account)
                            split_invoice_receivables[payment] = self._update_amounts(split_invoice_receivables[payment], {'amount': payment.amount}, order.date_order)
                        else:
                            combine_inv_payment_receivable_lines[payment_method] |= payment.account_move_id.line_ids.filtered(lambda line: line.account_id == pos_receivable_account)
                            combine_invoice_receivables[payment_method] = self._update_amounts(combine_invoice_receivables[payment_method], {'amount': payment.amount}, order.date_order)

                # If pay_later, we create the receivable lines.
                #   if split, with partner
                #   Otherwise, it's aggregated (combined)
                # But only do if order is *not* invoiced because no account move is created for pay later invoice payments.
                if payment_type == 'pay_later' and not order_is_invoiced:
                    if is_split_payment:
                        split_receivables_pay_later[payment] = self._update_amounts(split_receivables_pay_later[payment], {'amount': amount}, date)
                    elif not is_split_payment:
                        combine_receivables_pay_later[payment_method] = self._update_amounts(combine_receivables_pay_later[payment_method], {'amount': amount}, date)

            if not order_is_invoiced:
                base_lines = order.with_context(linked_to_pos=True)._prepare_tax_base_line_values()
                AccountTax._add_tax_details_in_base_lines(base_lines, order.company_id)
                AccountTax._round_base_lines_tax_details(base_lines, order.company_id)
                AccountTax._add_accounting_data_in_base_lines_tax_details(base_lines, order.company_id, include_caba_tags=True)
                tax_results = AccountTax._prepare_tax_lines(base_lines, order.company_id)
                total_amount_currency = 0.0
                for base_line, to_update in tax_results['base_lines_to_update']:
                    # Combine sales/refund lines
                    sale_vals_dict = self._get_sale_key(base_line)
                    sale_key = frozendict(sale_vals_dict)
                    total_amount_currency += to_update['amount_currency']
                    sales[sale_key] = self._update_amounts(
                        sales[sale_key],
                        {
                            'amount': to_update['amount_currency'],
                            'amount_converted': to_update['balance'],
                        },
                        order.date_order,
                    )
                    if self.config_id._is_quantities_set():
                        sales[sale_key].setdefault('quantity', 0)
                        sales[sale_key]['quantity'] += base_line['quantity']

                # Combine tax lines
                for tax_line in tax_results['tax_lines_to_add']:
                    tax_key = (
                        tax_line['account_id'],
                        tax_line['tax_repartition_line_id'],
                        tuple(tax_line['tax_tag_ids'][0][2]),
                    )
                    total_amount_currency += tax_line['amount_currency']
                    taxes[tax_key] = self._update_amounts(
                        taxes[tax_key],
                        {
                            'amount': tax_line['amount_currency'],
                            'amount_converted': tax_line['balance'],
                            'base_amount': tax_line['tax_base_amount']
                        },
                        order.date_order,
                    )

                if self.config_id.cash_rounding:
                    diff = order.amount_paid + total_amount_currency
                    rounding_difference = self._update_amounts(rounding_difference, {'amount': diff}, order.date_order)

                # Increasing current partner's customer_rank
                partners = (order.partner_id | order.partner_id.commercial_partner_id)
                partners._increase_rank('customer_rank')

        MoveLine = self.env['account.move.line'].with_context(check_move_validity=False, skip_invoice_sync=True)

        data.update({
            'taxes':                               taxes,
            'sales':                               sales,
            'split_receivables_bank':              split_receivables_bank,
            'combine_receivables_bank':            combine_receivables_bank,
            'split_receivables_cash':              split_receivables_cash,
            'combine_receivables_cash':            combine_receivables_cash,
            'combine_invoice_receivables':         combine_invoice_receivables,
            'split_receivables_pay_later':         split_receivables_pay_later,
            'combine_receivables_pay_later':       combine_receivables_pay_later,
            'combine_inv_payment_receivable_lines': combine_inv_payment_receivable_lines,
            'rounding_difference':                 rounding_difference,
            'MoveLine':                            MoveLine,
            'split_invoice_receivables': split_invoice_receivables,
            'split_inv_payment_receivable_lines': split_inv_payment_receivable_lines,
        })
        return data

    def _get_rounding_difference_vals(self, amount, amount_converted):
        if not self.config_id.cash_rounding:
            return {}

        compare_result = float_compare(0.0, amount, precision_rounding=self.currency_id.rounding)
        if not compare_result:
            return {}

        partial_args = {'name': 'Rounding line', 'move_id': self.move_id.id}
        if compare_result > 0:    # loss
            partial_args['account_id'] = self.config_id.rounding_method.loss_account_id.id
            return self._debit_amounts(partial_args, -amount, -amount_converted)

        partial_args['account_id'] = self.config_id.rounding_method.profit_account_id.id
        return self._credit_amounts(partial_args, amount, amount_converted)

    def _create_non_reconciliable_move_lines(self, data):
        # Create account.move.line records for
        #   - sales
        #   - taxes
        #   - non-cash split receivables (not for automatic reconciliation)
        #   - non-cash combine receivables (not for automatic reconciliation)
        taxes = data.get('taxes')
        sales = data.get('sales')
        rounding_difference = data.get('rounding_difference')
        MoveLine = data.get('MoveLine')

        tax_vals = [self._get_tax_vals(key, amounts['amount'], amounts['amount_converted'], amounts['base_amount_converted']) for key, amounts in taxes.items()]
        # Check if all taxes lines have account_id assigned. If not, there are repartition lines of the tax that have no account_id.
        tax_names_no_account = [line['name'] for line in tax_vals if not line['account_id']]
        if tax_names_no_account:
            raise UserError(_(
                'Unable to close and validate the session.\n'
                'Please set corresponding tax account in each repartition line of the following taxes: \n%s',
                ', '.join(tax_names_no_account)
            ))

        rounding_vals = []
        if not float_is_zero(rounding_difference['amount'], precision_rounding=self.currency_id.rounding) or not float_is_zero(rounding_difference['amount_converted'], precision_rounding=self.currency_id.rounding):
            rounding_vals = [self._get_rounding_difference_vals(rounding_difference['amount'], rounding_difference['amount_converted'])]

        MoveLine.create(tax_vals + rounding_vals)
        move_line_ids = MoveLine.create(list(starmap(self._get_sale_vals, sales.items())))
        for key, ml_id in zip(sales.keys(), move_line_ids.ids):
            sales[key]['move_line_id'] = ml_id

        return data

    def _create_bank_payment_moves(self, data):
        combine_receivables_bank = data.get('combine_receivables_bank')
        split_receivables_bank = data.get('split_receivables_bank')
        bank_payment_method_diffs = data.get('bank_payment_method_diffs')
        MoveLine = data.get('MoveLine')
        payment_method_to_receivable_lines = {}
        payment_to_receivable_lines = {}
        for payment_method, amounts in combine_receivables_bank.items():
            combine_receivable_line = MoveLine.create(self._get_combine_receivable_vals(payment_method, amounts['amount'], amounts['amount_converted']))
            payment_receivable_line = self._create_combine_account_payment(payment_method, amounts, diff_amount=bank_payment_method_diffs.get(payment_method.id) or 0)
            payment_method_to_receivable_lines[payment_method] = combine_receivable_line | payment_receivable_line

        split_items = list(split_receivables_bank.items())
        split_receivable_lines = MoveLine.create([
            self._get_split_receivable_vals(payment, amounts['amount'], amounts['amount_converted'])
            for payment, amounts in split_items
        ])
        payment_receivable_lines = self._create_split_account_payments(split_items)
        for (payment, amounts), split_receivable_line in zip(split_items, split_receivable_lines):
            payment_to_receivable_lines[payment] = split_receivable_line | payment_receivable_lines.get(payment, self.env['account.move.line'])

        for bank_payment_method in self.payment_method_ids.filtered(lambda pm: pm.type == 'bank' and pm.split_transactions):
            self._create_diff_account_move_for_split_payment_method(bank_payment_method, bank_payment_method_diffs.get(bank_payment_method.id) or 0)

        data['payment_method_to_receivable_lines'] = payment_method_to_receivable_lines
        data['payment_to_receivable_lines'] = payment_to_receivable_lines
        return data

    def _create_pay_later_receivable_lines(self, data):
        MoveLine = data.get('MoveLine')
        combine_receivables_pay_later = data.get('combine_receivables_pay_later')
        split_receivables_pay_later = data.get('split_receivables_pay_later')
        vals = []
        for payment_method, amounts in combine_receivables_pay_later.items():
            vals.append(self._get_combine_receivable_vals(payment_method, amounts['amount'], amounts['amount_converted']))
        for payment, amounts in split_receivables_pay_later.items():
            vals.append(self._get_split_receivable_vals(payment, amounts['amount'], amounts['amount_converted']))
        for val in vals:
            # Entries related to a `pay_later` payment method should not be excluded from follow-ups.
            val['no_followup'] = False
        data['pay_later_move_lines'] = MoveLine.create(vals)
        return data

    def _ensure_payment_outstanding_account(self, payment):
        # In community the outstanding account is computed on the creation of account.payment records
        if not payment.outstanding_account_id and self.env['account.move']._get_invoice_in_payment_state() == 'in_payment':
            payment.force_outstanding_account_id = payment._get_outstanding_account(payment.payment_type)

    def _create_combine_account_payment(self, payment_method, amounts, diff_amount):
        outstanding_account = payment_method.outstanding_account_id
        destination_account = self._get_receivable_account(payment_method)
        payment_type = "inbound"
        if self.currency_id.compare_amounts(amounts['amount'], 0) < 0:
            payment_type = 'outbound'

        account_payment = self.env['account.payment'].with_context(pos_payment=True).create({
            'amount': abs(amounts['amount']),
            'journal_id': payment_method.journal_id.id,
            'force_outstanding_account_id': outstanding_account.id,
            'destination_account_id': destination_account.id,
            'memo': _('Combine %(payment_method)s POS payments from %(session)s', payment_method=payment_method.name, session=self.name),
            'pos_payment_method_id': payment_method.id,
            'pos_session_id': self.id,
            'company_id': self.company_id.id,
            'payment_type': payment_type,
        })

        self._ensure_payment_outstanding_account(account_payment)
        account_payment.action_post()

        diff_amount_compare_to_zero = self.currency_id.compare_amounts(diff_amount, 0)
        if diff_amount_compare_to_zero != 0:
            self._apply_diff_on_account_payment_move(account_payment, payment_method, diff_amount)

        return account_payment.move_id.line_ids.filtered(lambda line: line.account_id == self._get_receivable_account(payment_method))

    def _apply_diff_on_account_payment_move(self, account_payment, payment_method, diff_amount):
        diff_vals = self._get_diff_vals(payment_method.id, diff_amount, account_payment.outstanding_account_id)
        if not diff_vals:
            return
        source_vals, dest_vals = diff_vals
        outstanding_line = account_payment.move_id.line_ids.filtered(lambda line: line.account_id.id == source_vals['account_id'])
        new_balance = outstanding_line.balance + self._amount_converter(diff_amount, self.stop_at, False)
        new_balance_compare_to_zero = self.currency_id.compare_amounts(new_balance, 0)
        account_payment.move_id.button_draft()
        account_payment.move_id.write({
            'line_ids': [
                Command.create(dest_vals),
                Command.update(outstanding_line.id, {
                    'debit': new_balance_compare_to_zero > 0 and new_balance or 0.0,
                    'credit': new_balance_compare_to_zero < 0 and -new_balance or 0.0
                })
            ]
        })
        account_payment.write({
            'amount': abs(new_balance),
        })
        account_payment.move_id.action_post()

    def _create_split_account_payment(self, payment, amounts):
        return self._create_split_account_payments([(payment, amounts)]).get(payment, self.env['account.move.line'])

    def _get_split_account_payment_vals(self, payment, amounts, accounting_partner, destination_account):
        payment_method = payment.payment_method_id
        payment_type = "inbound"
        if self.currency_id.compare_amounts(amounts['amount'], 0) < 0:
            payment_type = 'outbound'
        return {
            'amount': abs(amounts['amount']),
            'partner_id': accounting_partner.id,
            'journal_id': payment_method.journal_id.id,
            'force_outstanding_account_id': payment_method.outstanding_account_id.id,
            'destination_account_id': destination_account.id,
            'memo': _('%(payment_method)s POS payment of %(partner)s in %(session)s', payment_method=payment_method.name, partner=payment.partner_id.display_name, session=self.name),
            'pos_payment_method_id': payment_method.id,
            'pos_session_id': self.id,
            'payment_type': payment_type,
        }

    def _create_split_account_payments(self, payment_amounts_list):
        vals_list = []
        entries = []
        for payment, amounts in payment_amounts_list:
            if not payment.payment_method_id.journal_id:
                continue
            accounting_partner = self.env["res.partner"]._find_accounting_partner(payment.partner_id)
            destination_account = accounting_partner.property_account_receivable_id
            vals_list.append(self._get_split_account_payment_vals(payment, amounts, accounting_partner, destination_account))
            entries.append((payment, amounts, destination_account))
        account_payments = self.env['account.payment'].create(vals_list)
        for account_payment, (payment, amounts, destination_account) in zip(account_payments, entries):
            self._ensure_payment_outstanding_account(account_payment)
        account_payments.action_post()
        payment_to_line = {}
        for account_payment, (payment, amounts, destination_account) in zip(account_payments, entries):
            payment_to_line[payment] = account_payment.move_id.line_ids.filtered(lambda line: line.account_id == destination_account)
        return payment_to_line

    def _create_cash_statement_lines_and_cash_move_lines(self, data):
        # Create the split and combine cash statement lines and account move lines.
        # `split_cash_statement_lines` maps `journal` -> split cash statement lines
        # `combine_cash_statement_lines` maps `journal` -> combine cash statement lines
        # `split_cash_receivable_lines` maps `journal` -> split cash receivable lines
        # `combine_cash_receivable_lines` maps `journal` -> combine cash receivable lines
        MoveLine = data.get('MoveLine')
        split_receivables_cash = data.get('split_receivables_cash')
        combine_receivables_cash = data.get('combine_receivables_cash')

        # handle split cash payments
        split_cash_statement_line_vals = []
        split_cash_receivable_vals = []
        for payment, amounts in split_receivables_cash.items():
            journal_id = payment.payment_method_id.journal_id
            split_cash_statement_line_vals.append(
                self._get_split_statement_line_vals(
                    journal_id,
                    amounts['amount'],
                    payment
                )
            )
            split_cash_receivable_vals.append(
                self._get_split_receivable_vals(
                    payment,
                    amounts['amount'],
                    amounts['amount_converted']
                )
            )
        # handle combine cash payments
        combine_cash_statement_line_vals = []
        combine_cash_receivable_vals = []
        for payment_method, amounts in combine_receivables_cash.items():
            if not float_is_zero(amounts['amount'] , precision_rounding=self.currency_id.rounding):
                combine_cash_statement_line_vals.append(
                    self._get_combine_statement_line_vals(
                        payment_method.journal_id,
                        amounts['amount'],
                        payment_method
                    )
                )
                combine_cash_receivable_vals.append(
                    self._get_combine_receivable_vals(
                        payment_method,
                        amounts['amount'],
                        amounts['amount_converted']
                    )
                )

        # create the statement lines and account move lines
        BankStatementLine = self.env['account.bank.statement.line'].with_context(no_retrieve_partner=True)
        split_cash_statement_lines = {}
        combine_cash_statement_lines = {}
        split_cash_receivable_lines = {}
        combine_cash_receivable_lines = {}
        split_cash_statement_lines = BankStatementLine.create(split_cash_statement_line_vals).mapped('move_id.line_ids').filtered(lambda line: line.account_id.account_type == 'asset_receivable')
        combine_cash_statement_lines = BankStatementLine.create(combine_cash_statement_line_vals).mapped('move_id.line_ids').filtered(lambda line: line.account_id.account_type == 'asset_receivable')
        split_cash_receivable_lines = MoveLine.create(split_cash_receivable_vals)
        combine_cash_receivable_lines = MoveLine.create(combine_cash_receivable_vals)

        data.update(
            {'split_cash_statement_lines':    split_cash_statement_lines,
             'combine_cash_statement_lines':  combine_cash_statement_lines,
             'split_cash_receivable_lines':   split_cash_receivable_lines,
             'combine_cash_receivable_lines': combine_cash_receivable_lines
             })
        return data

    def _create_invoice_receivable_lines(self, data):
        # Create invoice receivable lines for this session's move_id.
        # Keep reference of the invoice receivable lines because
        # they are reconciled with the lines in combine_inv_payment_receivable_lines
        MoveLine = data.get('MoveLine')
        combine_invoice_receivables = data.get('combine_invoice_receivables')
        split_invoice_receivables = data.get('split_invoice_receivables')

        combine_invoice_receivable_vals = defaultdict(list)
        split_invoice_receivable_vals = defaultdict(list)
        combine_invoice_receivable_lines = {}
        split_invoice_receivable_lines = {}
        for payment_method, amounts in combine_invoice_receivables.items():
            combine_invoice_receivable_vals[payment_method].append(self._get_invoice_receivable_vals(amounts['amount'], amounts['amount_converted']))
        for payment, amounts in split_invoice_receivables.items():
            split_invoice_receivable_vals[payment].append(self._get_invoice_receivable_vals(amounts['amount'], amounts['amount_converted']))
        for payment_method, vals in combine_invoice_receivable_vals.items():
            receivable_lines = MoveLine.create(vals)
            combine_invoice_receivable_lines[payment_method] = receivable_lines
        for payment, vals in split_invoice_receivable_vals.items():
            receivable_lines = MoveLine.create(vals)
            split_invoice_receivable_lines[payment] = receivable_lines

        data.update({'combine_invoice_receivable_lines': combine_invoice_receivable_lines})
        data.update({'split_invoice_receivable_lines': split_invoice_receivable_lines})
        return data

    def _reconcile_account_move_lines(self, data):
        # reconcile cash receivable lines
        split_cash_statement_lines = data.get('split_cash_statement_lines')
        combine_cash_statement_lines = data.get('combine_cash_statement_lines')
        split_cash_receivable_lines = data.get('split_cash_receivable_lines')
        combine_cash_receivable_lines = data.get('combine_cash_receivable_lines')
        combine_inv_payment_receivable_lines = data.get('combine_inv_payment_receivable_lines')
        split_inv_payment_receivable_lines = data.get('split_inv_payment_receivable_lines')
        combine_invoice_receivable_lines = data.get('combine_invoice_receivable_lines')
        split_invoice_receivable_lines = data.get('split_invoice_receivable_lines')
        payment_method_to_receivable_lines = data.get('payment_method_to_receivable_lines')
        payment_to_receivable_lines = data.get('payment_to_receivable_lines')

        all_lines = (
              split_cash_statement_lines
            | combine_cash_statement_lines
            | split_cash_receivable_lines
            | combine_cash_receivable_lines
        )
        all_lines.filtered(lambda line: line.move_id.state != 'posted').move_id._post(soft=False)

        lines_by_account = all_lines.filtered(lambda l: not l.reconciled).grouped('account_id')
        for lines in lines_by_account.values():
            lines.with_context(no_cash_basis=True).reconcile()

        for payment_method, lines in payment_method_to_receivable_lines.items():
            lines.filtered(lambda line: not line.reconciled).with_context(no_cash_basis=True).reconcile()

        split_plan = [
            lines.filtered(lambda line: not line.reconciled)
            for lines in payment_to_receivable_lines.values()
        ]
        if split_plan:
            self.env['account.move.line'].with_context(no_cash_basis=True)._reconcile_plan(split_plan)

        # Reconcile invoice payments' receivable lines.
        for payment_method in combine_inv_payment_receivable_lines:
            lines = combine_inv_payment_receivable_lines[payment_method] | combine_invoice_receivable_lines.get(payment_method, self.env['account.move.line'])
            lines.filtered(lambda line: not line.reconciled).with_context(no_cash_basis=True).reconcile()

        for payment in split_inv_payment_receivable_lines:
            lines = split_inv_payment_receivable_lines[payment] | split_invoice_receivable_lines.get(payment, self.env['account.move.line'])
            lines.filtered(lambda line: not line.reconciled).with_context(no_cash_basis=True).reconcile()

        return data

    def _get_split_receivable_vals(self, payment, amount, amount_converted):
        accounting_partner = self.env["res.partner"]._find_accounting_partner(payment.partner_id)
        if not accounting_partner:
            raise UserError(_("You have enabled the \"Identify Customer\" option for %(payment_method)s payment method,"
                              "but the order %(order)s does not contain a customer.",
                              payment_method=payment.payment_method_id.name,
                              order=payment.pos_order_id.name))
        partial_vals = {
            'account_id': accounting_partner.property_account_receivable_id.id,
            'move_id': self.move_id.id,
            'partner_id': accounting_partner.id,
            'name': '%s - %s' % (self.name, payment.payment_method_id.name),
        }
        return self._debit_amounts(partial_vals, amount, amount_converted)

    def _get_combine_receivable_vals(self, payment_method, amount, amount_converted):
        partial_vals = {
            'account_id': self._get_receivable_account(payment_method).id,
            'move_id': self.move_id.id,
            'name': '%s - %s' % (self.name, payment_method.name),
            'display_type': 'payment_term',
        }
        return self._debit_amounts(partial_vals, amount, amount_converted)

    def _get_invoice_receivable_vals(self, amount, amount_converted):
        partial_vals = {
            'account_id': self.company_id.account_default_pos_receivable_account_id.id,
            'move_id': self.move_id.id,
            'name': _('From invoice payments'),
            'display_type': 'payment_term',
        }
        return self._credit_amounts(partial_vals, amount, amount_converted)

    def _get_sale_key(self, base_line):
        return {
            # account
            'account_id': base_line['account_id'].id,
            # sign
            'sign': -1 if base_line['is_refund'] else 1,
            # for taxes
            'tax_ids': tuple(base_line['record'].tax_ids_after_fiscal_position.flatten_taxes_hierarchy().ids),
            'base_tag_ids': tuple(base_line['tax_tag_ids'].ids),
            'product_id': base_line['product_id'].id if self.config_id.use_closing_entry_by_product else False,
        }

    def _get_sale_vals(self, key, sale_vals):
        tax_ids = key['tax_ids']
        product_id = key['product_id']
        sign = key['sign']
        applied_taxes = self.env['account.tax'].browse(tax_ids)
        if product_id:
            product = self.env['product.product'].browse(product_id)
            product_name = product.display_name
            product_uom = product.uom_id.id
        else:
            product_name = ""
            product_uom = False
        title = _('Sales') if sign == 1 else _('Refund')
        name = _('%s untaxed', title)
        if applied_taxes:
            name = _('%(title)s %(product_name)s with %(taxes)s', title=title, product_name=product_name, taxes=', '.join([tax.name for tax in applied_taxes]))
        partial_vals = {
            'name': name,
            'account_id': key['account_id'],
            'move_id': self.move_id.id,
            'tax_ids': [(6, 0, tax_ids)],
            'tax_tag_ids': [(6, 0, key['base_tag_ids'])],
            'product_id': product_id,
            'display_type': 'product',
            'product_uom_id': product_uom,
            'currency_id': self.currency_id.id,
            'amount_currency': sale_vals['amount'],
            'balance': sale_vals['amount_converted'],
            'quantity': sale_vals.get('quantity', 1.00) * key['sign'],
        }
        return partial_vals

    def _get_tax_vals(self, key, amount, amount_converted, base_amount_converted):
        account_id, repartition_line_id, tag_ids = key
        tax_rep = self.env['account.tax.repartition.line'].browse(repartition_line_id)
        tax = tax_rep.tax_id
        return {
            'name': tax.name,
            'account_id': account_id,
            'move_id': self.move_id.id,
            'tax_base_amount': base_amount_converted,
            'tax_repartition_line_id': repartition_line_id,
            'tax_tag_ids': [(6, 0, tag_ids)],
            'display_type': 'tax',
            'currency_id': self.currency_id.id,
            'amount_currency': amount,
            'balance': amount_converted,
        }

    def _get_combine_statement_line_vals(self, journal, amount, payment_method):
        amount_values = self._prepare_statement_line_amount_values(journal, amount)
        return {
            'date': fields.Date.context_today(self),
            'payment_ref': self.name,
            'pos_session_id': self.id,
            'journal_id': journal.id,
            'counterpart_account_id': self._get_receivable_account(payment_method).id,
            **amount_values
        }

    def _get_split_statement_line_vals(self, journal, amount, payment):
        accounting_partner = self.env["res.partner"]._find_accounting_partner(payment.partner_id)
        amount_values = self._prepare_statement_line_amount_values(journal, amount)
        return {
            'date': fields.Date.context_today(self, timestamp=payment.payment_date),
            'payment_ref': payment.name,
            'pos_session_id': self.id,
            'journal_id': journal.id,
            'counterpart_account_id': accounting_partner.property_account_receivable_id.id,
            'partner_id': accounting_partner.id,
            **amount_values
        }

    def _prepare_statement_line_amount_values(self, journal, amount):
        journal_currency = journal.currency_id or self.company_id.currency_id
        if journal_currency == self.currency_id:
            return {'amount': amount}
        return {
            'amount': self.currency_id._convert(amount, journal_currency, self.company_id, self.stop_at),
            'amount_currency': amount,
            'foreign_currency_id': self.currency_id.id,
        }

    def _update_amounts(self, old_amounts, amounts_to_add, date, round=True, force_company_currency=False):
        """Responsible for adding `amounts_to_add` to `old_amounts` considering the currency of the session.

        ::

            old_amounts {                                                       new_amounts {
                amount                         amounts_to_add {                     amount
                amount_converted        +          amount               ->          amount_converted
               [base_amount                       [base_amount]                    [base_amount
                base_amount_converted]        }                                     base_amount_converted]
            }                                                                   }

        NOTE:
            - Notice that `amounts_to_add` does not have `amount_converted` field.
                This function is responsible in calculating the `amount_converted` from the
                `amount` of `amounts_to_add` which is used to update the values of `old_amounts`.
            - Values of `amount` and/or `base_amount` should always be in session's currency [1].
            - Value of `amount_converted` should be in company's currency

        [1] Except when `force_company_currency` = True. It means that values in `amounts_to_add`
            is in company currency.

        :param dict old_amounts:
            Amounts to update
        :param dict amounts_to_add:
            Amounts used to update the old_amounts
        :param date date:
            Date used for conversion
        :param bool round:
            Same as round parameter of `res.currency._convert`.
            Defaults to True because that is the default of `res.currency._convert`.
            We put it to False if we want to round globally.
        :param bool force_company_currency:
            If True, the values in amounts_to_add are in company's currency.
            Defaults to False because it is only used to anglo-saxon lines.

        :returns: new amounts combining the values of `old_amounts` and `amounts_to_add`.
        :rtype: dict
        """
        # make a copy of the old amounts
        new_amounts = { **old_amounts }

        amount = amounts_to_add.get('amount')
        if self.is_in_company_currency or force_company_currency:
            amount_converted = amount
        else:
            amount_converted = self._amount_converter(amount, date, round)

        # update amount and amount converted
        new_amounts['amount'] += amount
        new_amounts['amount_converted'] += amount_converted

        # consider base_amount if present

        if amounts_to_add.get('base_amount'):
            base_amount = amounts_to_add.get('base_amount')

            # update base_amount and base_amount_converted
            new_amounts['base_amount'] += base_amount
            new_amounts['base_amount_converted'] += base_amount

        return new_amounts

    def _credit_amounts(self, partial_move_line_vals, amount, amount_converted, force_company_currency=False):
        """ `partial_move_line_vals` is completed by `crediting` the given amounts.

        NOTE Amounts in PoS are in the currency of journal_id in the session.config_id.
        This means that amount fields in any pos record are actually equivalent to amount_currency
        in account module. Understanding this basic is important in correctly assigning values for
        'amount' and 'amount_currency' in the account.move.line record.

        :param dict partial_move_line_vals:
            initial values in creating account.move.line
        :param float amount:
            amount derived from pos.payment, pos.order, or pos.order.line records
        :param float amount_converted:
            converted value of `amount` from the given `session_currency` to company currency

        :return: complete values for creating 'amount.move.line' record
        :rtype: dict
        """
        if self.is_in_company_currency or force_company_currency:
            additional_field = {}
        else:
            additional_field = {
                'amount_currency': -amount,
                'currency_id': self.currency_id.id,
            }
        return {
            'debit': -amount_converted if amount_converted < 0.0 else 0.0,
            'credit': amount_converted if amount_converted > 0.0 else 0.0,
            **partial_move_line_vals,
            **additional_field,
        }

    def _debit_amounts(self, partial_move_line_vals, amount, amount_converted, force_company_currency=False):
        """ `partial_move_line_vals` is completed by `debiting` the given amounts.

        See _credit_amounts docs for more details.
        """
        if self.is_in_company_currency or force_company_currency:
            additional_field = {}
        else:
            additional_field = {
                'amount_currency': amount,
                'currency_id': self.currency_id.id,
            }
        return {
            'debit': amount_converted if amount_converted > 0.0 else 0.0,
            'credit': -amount_converted if amount_converted < 0.0 else 0.0,
            **partial_move_line_vals,
            **additional_field,
>>>>>>> 7834209712afdbe4cdfec33022238133778af1c8
        }

    def _amount_converter(self, amount, date, round):
        # self should be single record as this method is only called in the subfunctions of self._validate_session
        return self.currency_id._convert(amount, self.company_id.currency_id, self.company_id, date, round=round)

    def show_linked_account_move(self):
        self.ensure_one()
        all_related_moves = self._get_session_and_order_account_moves()
        return {
            'name': _('Invoices'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'domain': [('id', 'in', all_related_moves.ids)],
            'views': [
                (self.env.ref('account.view_move_tree').id, 'list'),
                (self.env.ref('account.view_move_form').id, 'form'),
            ],
        }

    def _compute_account_move_count(self):
        for record in self:
            record.account_move_count = len(record._get_session_and_order_account_moves())

    def _get_session_and_order_account_moves(self):
        return self.sales_move_id | self.refunds_move_id | self.order_ids.mapped('account_move')

    def _get_related_account_moves(self):
        invoices = self._get_session_and_order_account_moves()
        invoice_payments = self.mapped('order_ids.payment_ids.account_move_id')
        cash_moves = self.bank_statement_line_ids.mapped('move_id')
        reversal_moves = self.mapped('order_ids.reversed_move_ids')
        return invoices |\
            invoice_payments |\
            self.correction_move_ids |\
            cash_moves |\
            reversal_moves

    def action_show_payments_list(self):
        return {
            'name': _('Payments'),
            'type': 'ir.actions.act_window',
            'res_model': 'pos.payment',
            'view_mode': 'list,form',
            'domain': self._get_captured_payments_domain(),
            'context': {'search_default_group_by_payment_method': 1},
        }

    def _get_captured_payments_domain(self):
        return [('session_id', 'in', self.ids), ('pos_order_id.state', 'in', ['paid', 'invoiced', 'done'])]

    def open_frontend_cb(self):
        """Open the pos interface with config_id as an extra argument.

        In vanilla PoS each user can only have one active session, therefore it was not needed to pass the config_id
        on opening a session. It is also possible to login to sessions created by other users.

        :returns: dict
        """
        if not self.ids:
            return {}
        return self.config_id.open_ui()

    def _set_opening_control_data(self, cashbox_value: int, notes: str):
        """
        Internal logic for opening the session.
        Inherit this method to add custom logic before the sequence is assigned.
        """
        self.state = 'opened'
        self.start_at = fields.Datetime.now()
        cash_pm = self.config_id._get_cash_payment_method()
        self._handle_cash_statement_entries({
            cash_pm.id: cashbox_value,
        })

        if notes:
            self.opening_notes = notes
            message = _('Opening control message: ')
            message += notes
            self.message_post(body=plaintext2html(message))

    def set_opening_control(self, cashbox_value: int, notes: str):
        """
        Public method to open the session.
        This calls the internal logic and, if successful, assigns the sequence name.

        DO NOT INHERIT THIS METHOD. Inherit _set_opening_control_data instead.
        """
        if self.state != 'opening_control':
            return

        sequence_ctx = self.env['ir.sequence'].with_context(
            company_id=self.config_id.company_id.id,
        )
        sequence = sequence_ctx.search([
            ('code', '=', 'pos.session'),
            ('company_id', 'in', [self.config_id.company_id.id, False]),
        ], order='company_id', limit=1)

        first = (self.config_id.name if sequence.prefix == '/' else '')
        second = sequence.next_by_code('pos.session')
        third = (self.name if self.name != '/' else '')
        self.name = first + second + third
        self._set_opening_control_data(cashbox_value, notes)

    def action_view_order(self):
        return {
            'name': _('Orders'),
            'res_model': 'pos.order',
            'view_mode': 'list,form',
            'views': [
                (self.env.ref('point_of_sale.view_pos_order_tree_no_session_id').id, 'list'),
                (self.env.ref('point_of_sale.view_pos_pos_form').id, 'form'),
                ],
            'type': 'ir.actions.act_window',
            'domain': [('session_id', 'in', self.ids)],
        }

    @api.model
    def _alert_old_session(self):
        # If the session is open for more then one week,
        # log a next activity to close the session.
        sessions = self.sudo().search([('start_at', '<=', (fields.Datetime.now() - timedelta(days=7))), ('state', '!=', 'closed')])
        for session in sessions:
            if self.env['mail.activity'].search_count([('res_id', '=', session.id), ('res_model', '=', 'pos.session')]) == 0:
                session.activity_schedule(
                    'point_of_sale.mail_activity_old_session',
                    user_id=session.user_id.id,
                    note=_(
                        "Your PoS Session is open since %(date)s, we advise you to close it and to create a new one.",
                        date=session.start_at,
                    ),
                )

    def _check_if_no_draft_orders(self):
        draft_orders = self.get_session_orders().filtered(lambda order: order.state == 'draft')
        if draft_orders:
            raise UserError(_(
                    'There are still orders in draft state in the session. '
                    'Pay or cancel the following orders to validate the session:\n%s',
                    ', '.join(draft_orders.mapped('name')),
            ))
        return True

    def try_cash_in_out(self, _type, amount, reason, partner_id):
        if not self.env.user._has_cash_move_permission():
            raise AccessError(_("You don't have the access rights to perform a cash in/out."))

        sign = 1 if _type == 'in' else -1
        cash_pm = self.config_id._get_cash_payment_method()
        if not cash_pm:
            raise UserError(_("There is no cash payment method for this PoS Session"))

        message = f'{self.name}-{_type}-{reason}'
        signed_amount = amount * sign
        partner = self.env['res.partner'].browse(partner_id)
        cash_pm._create_payment_line(
            self,
            signed_amount,
            cash_pm.journal_id.suspense_account_id,
            message,
            partner,
        )

    def delete_cash_in_out(self, absl_id, partner_id):
        if not self.env.user._has_cash_delete_permission():
            raise AccessError(_("You don't have the access rights to delete a cash in/out."))
        absl = self.env['account.bank.statement.line'].browse(absl_id).sudo()
        if absl not in self.sudo().bank_statement_line_ids:
            raise AccessError(_("You cannot delete a cash move that is not linked to this session."))
        cashier_name = absl.partner_id.name
        amount = absl.amount
        action = cashier_name + ': ' + str(amount)
        absl.unlink()
        self.log_partner_message(partner_id, action, "CASH_IN_OUT_UNLINK")

    def _get_invoice_total_list(self):
        invoice_list = []
        for order in self.order_ids.filtered(lambda o: o.is_singly_invoiced):
            invoice = {
                'total': order.account_move.amount_total_signed,
                'name': order.account_move.name,
                'order_ref': order.pos_reference,
            }
            invoice_list.append(invoice)

        return invoice_list

    def _get_total_invoice(self):
        amount = 0
        for order in self.order_ids.filtered(lambda o: o.is_singly_invoiced):
            amount += order.amount_paid
        return amount

    def log_partner_message(self, partner_id, action, message_type):
        if message_type == 'ACTION_CANCELLED':
            body = _('Action cancelled (%(ACTION)s)', ACTION=action)
        elif message_type == 'CASH_DRAWER_ACTION':
            body = _('Cash drawer opened (%(ACTION)s)', ACTION=action)
        elif message_type == 'CASH_IN_OUT_UNLINK':
            body = _('Cash move deleted: %s', action)
        self.message_post(body=body, author_id=partner_id)

    def _get_closed_orders(self):
        return self.order_ids.filtered(lambda o: o.state not in ['draft', 'cancel'])

    def _get_order_for_session_closing(self):
        return self._get_closed_orders()

    ##############################################################
    #                 Accounting related methods                 #
    ##############################################################
    def _handle_bank_payment_method_difference(self, payment_method_closing={}):
        """
        This method will create a new account.move after session closing
        for each bank payment method with a difference between the amount of
        the payments and the amount counted in the closing. This can happen
        when the cashier forget to enter an amount for a bank payment method
        in the closing, or when there is a difference between the amount entered
        and the amount of the payments
        """
        other_payment_methods = self.payment_method_ids.filtered_domain([
            ('type', '=', 'bank'),
        ])

        for pm in other_payment_methods:
            payments = self.order_ids.mapped('payment_ids').filtered(
                lambda p: p.payment_method_id == pm,
            )

            # If not provided skip the reconciliation of the payment method,
            # this can happen when the session is closed from the UI and not
            # all the payment methods are sent by the frontend
            if str(pm.id) not in payment_method_closing and pm.id not in payment_method_closing:
                continue

            counted = payment_method_closing.get(str(pm.id), 0)
            counted = counted or payment_method_closing.get(pm.id, 0)
            diff = sum(payments.mapped('amount')) - counted

            if float_is_zero(diff, precision_rounding=self.currency_id.rounding):
                continue

            journal = pm.journal_id
            if not journal:
                continue

            pm_account = pm.receivable_account_id or self._get_receivable_account()
            correction_account = journal.loss_account_id if diff > 0 else journal.profit_account_id

            if not correction_account:
                continue

            abs_difference = abs(diff)
            move_ctx = self.env['account.move'].sudo().with_context(
                linked_to_pos=True,
            )
            move = move_ctx.create({
                'journal_id': journal.id,
                'date': fields.Date.context_today(self),
                'ref': _(
                    'Bank difference for %(pm)s in %(session)s',
                    pm=pm.name,
                    session=self.name,
                ),
                'line_ids': [
                    Command.create({
                        'name': pm.name,
                        'account_id': pm_account.id,
                        'amount_currency': abs_difference if diff < 0 else -abs_difference,
                    }),
                    Command.create({
                        'name': pm.name,
                        'account_id': correction_account.id,
                        'amount_currency': -abs_difference if diff < 0 else abs_difference,
                    }),
                ],
            })
            move._post()
            self.correction_move_ids |= move

    def _handle_cash_statement_entries(self, payment_method_closing={}):
        """
        Called at the opening and closing of the session, this method
        will create the necessary account.bank.statement and account.bank.statement.line
        records to reflect the cash movements of the session in the cash
        statement linked to the session.
        """
        cash_pm = self.config_id._get_cash_payment_method()
        if not cash_pm:
            return False

        counted = payment_method_closing.get(str(cash_pm.id), 0)
        counted = counted or payment_method_closing.get(cash_pm.id, 0)
        if not self.bank_statement_id:
            last_balance = self.config_id._get_opening_balance()
            self.bank_statement_id = self.env['account.bank.statement'].sudo().create({
                'journal_id': cash_pm.journal_id.id,
                'balance_start': last_balance,
                'name': _(
                    'Cash Statement for %(method_name)s in %(session)s',
                    method_name=cash_pm.name,
                    session=self.name,
                ),
            })
            difference = counted - last_balance
        else:
            end = self.bank_statement_id.balance_end
            difference = counted - end

        rounding = self.currency_id.rounding
        if not float_is_zero(difference, precision_rounding=rounding):
            message = _(
                'Cash correction from %(session)s',
                session=self.name,
            )
            cash_pm._create_payment_line(
                self,
                difference,
                False,
                message,
            )

        return True

    def _get_receivable_account(self):
        """
        PoS session receivable account is now accessed through the linked
        default partner of the linked config.
        """
        self.config_id.ensure_one()
        return self.config_id.default_partner_id.property_account_receivable_id

    def _validate_session_accounting(self):
        """
        This method is the ONLY entry point for the session closing
        process, and should contain all the necessary logic to create
        the accounting entries of the session closing.
        """
        self.ensure_one()

        # Get all paid and invoiced orders of the session
        non_invoiced_orders, invoiced_orders = self._get_invoiced_and_non_invoiced_orders()
        self._check_invoiced_orders_are_posted(invoiced_orders)

        # Build the out_receipt lines. Returns pm_data_list so we can
        # create the matching account.payment / statement line records after posting.
        sale_orders = non_invoiced_orders.filtered(
            lambda order: not order.is_refund_or_negative() and order.amount_total > 0,
        )
        refund_orders = non_invoiced_orders - sale_orders
        sales_move = self._create_session_account_move(sale_orders)
        refunds_move = self._create_session_account_move(refund_orders)
        self.sales_move_id = sales_move
        self.refunds_move_id = refunds_move

        # Ensure tracking of pos orders in the account moves
        sale_orders.account_move = sales_move
        refund_orders.account_move = refunds_move

    def _prepare_session_closing_extra_line_commands(self, orders, refund, payments=[]):
        """ Inherited in pos_stock """
        return []

    def _prepare_session_move_vals(self, orders):
        self.ensure_one()
        today = fields.Date.context_today(self)
        # All orders are refunds or not
        move_type = 'out_refund' if orders[0].is_refund_or_negative() else 'out_invoice'

        return {
            'move_type': move_type,
            'company_id': self.company_id.id,
            'journal_id': self.config_id.journal_id.id,
            'partner_id': self.config_id.default_partner_id.id,
            'date': today,
            'invoice_date_due': today,
            'pos_session_ids': [(4, self.id)],
            'always_tax_exigible': True,
        }

    def _create_session_account_move(self, orders):
        """
        This method creates the receipt of the session closing, with all
        the details of the session accounting. This will only take into
        account the orders that were paid but not invoiced, as the ones
        that were invoiced already have their details in the invoice.

        We'll create following account.move.line:

        - One line per (revenue account + VAT rate) group with net amount + tax_ids
        - One tax line per (tax account + tax) combination
        - One line per payment method with the total amount
          (display_type='payment_term' on the POS receivable account,
          so it can be reconciled with account.payment)

        After posting, one account.payment is created per payment method
        and reconciled against the matching payment_term line, marking
        the receipt as fully paid via standard Odoo reconciliation.

        Returns the pm_data_list (list of dicts) for payment creation
        in _validate_session_accounting.
        """
        if not orders:
            return self.env['account.move']

        refund = orders[0].is_refund_or_negative()  # All orders are refunds or not
        AccountJournal = self.env['account.journal'].with_company(
            self.company_id,
        )
        journal = AccountJournal._ensure_company_account_journal()
        config_journal = self.config_id.journal_id
        if self.config_id.journal_id != journal and config_journal.type != 'sale':
            self.config_id.journal_id = journal

        payment_methods = orders.payment_ids.payment_method_id
        cash_payment_method = payment_methods.filtered(
            lambda pm: pm.type == 'cash',
        )

        if len(cash_payment_method) > 1:
            raise UserError(_(
                "Only one cash payment method can be used in a session.",
            ))

        # product_commands => invoice_line_ids (display_type=product, net price_unit)
        lines = orders.with_context(hide_combo_title=True)._prepare_account_move_line_data()
        lines_commands = [Command.create(line['account.move.line']) for line in lines]

        payments = orders._prepare_account_move_line_data_for_payments()
        line_data = [pm['account.move.line'] for pm in payments]
        payment_commands = [Command.create(pm_data) for pm_data in line_data]
        extra_commands = self._prepare_session_closing_extra_line_commands(
            orders,
            refund,
            payments,
        )

        # Ensure rounding method record is set on the invoice if needed
        rounding_method = self.config_id._get_rounding_method_for_invoice(orders)
        move_vals = self._prepare_session_move_vals(orders)
        move_vals.update({
            'invoice_line_ids': lines_commands,
            'line_ids': payment_commands,
            'invoice_cash_rounding_id': rounding_method.id,
        })
        move = self.env['account.move'].sudo().with_context(
            check_move_validity=False,
            linked_to_pos=True,
        ).create(move_vals)

        move_ctx = move.with_context(
            linked_to_pos=True,
            skip_invoice_sync=True,
        )

        if len(extra_commands) > 0:
            move_ctx.with_context(
                check_move_validity=False,
            ).write({'line_ids': extra_commands})

        # Ensure account_id is always the good one, sometime due to the
        # compute method on account_id in the account.move.line model,
        # the account_id on payment_commands is not the one expected,
        # so we set it again here to be sure.
        payment_term_lines = move.line_ids.filtered(
            lambda line: line.display_type == 'payment_term',
        )
        zipped = zip(payment_commands, payment_term_lines)
        for payment_command, term_line in zipped:
            term_line.account_id = payment_command[2]['account_id']

        with move_ctx._check_balanced({'records': move}):
            if rounding_method.exists():
                data = orders._prepare_account_move_line_data_for_rounding(move)
                move_ctx.line_ids = data

            # A rounded foreign-currency payment converts to a slightly different company-currency
            # total than the sum of individually converted product/tax balances. Absorb the diff.
            summary = sum(move.line_ids.mapped('balance'))
            balance_diff = self.company_id.currency_id.round(summary)
            if move.currency_id != self.company_id.currency_id and balance_diff:
                if balance_diff:
                    payment_term_lines = move.line_ids.filtered(
                        lambda line: line.display_type == 'payment_term',
                    )
                    if payment_term_lines:
                        payment_term_lines[0].balance -= balance_diff

        move_ctx.with_company(self.company_id)._post()
        partner = self.config_id.default_partner_id
        payment_lines = self.env['account.move.line']
        for payment in payments:
            pm = payment['metadata']['payment_method_id']
            amount = payment['account.move.line']['amount_currency']
            payment_lines |= pm._create_payment_line(
                self,
                amount,
                partner.property_account_receivable_id,
                False,
                partner,
            )

        payment_lines = payment_lines.filtered(
            lambda line: not line.reconciled,
        )
        payment_term_lines = payment_term_lines.filtered(
            lambda line: not line.reconciled,
        )

        # We cannot reconcile automatically all lines together because
        # sometime it create weird reconciliation with multiple payments
        for idx, term in enumerate(payment_term_lines):
            payment_line = payment_lines[idx]
            (payment_line + term).with_context(
                skip_invoice_sync=True,
                no_cash_basis=True,
            ).sudo().reconcile()

        return move

    def _get_invoiced_and_non_invoiced_orders(self):
        """ Return the paid orders of the session that are not invoiced. """
        self.ensure_one()
        orders = self._get_order_for_session_closing()
        invoiced_orders = orders.filtered(lambda o: o.is_singly_invoiced)
        non_invoiced_orders = orders - invoiced_orders
        return non_invoiced_orders, invoiced_orders

    def _check_invoiced_orders_are_posted(self, invoiced_orders):
        account_move = invoiced_orders.account_move
        unposted = account_move.filtered(lambda move: move.state != 'posted')
        if unposted:
            invoices = '\n'.join(f'{invoice.name} - {invoice.state}' for invoice in unposted)
            raise UserError(_(
                'You cannot close the POS when invoices are not posted.\nInvoices: %(invoices)s',
                invoices=invoices,
            ))

    def _prepare_account_move_line_commands_for_reversal(self, order, invoice_to_reverse):
        product_lines = invoice_to_reverse.line_ids.filtered(
            lambda line: line.display_type == 'product',
        )
        reverse_move_lines = []
        for line in product_lines:
            reverse_move_lines.append(Command.create({
                'name': _("Reversal of %s", line.name),
                'product_id': line.product_id.id,
                'account_id': line.account_id.id,
                'partner_id': line.partner_id.id,
                'currency_id': order.company_id.currency_id.id,
                'amount_currency': -line.amount_currency,
                'balance': -line.amount_currency,
                'display_type': line.display_type,
                'tax_ids': [(6, 0, line.tax_ids.ids)],
                'quantity': -line.quantity,
            }))
        return reverse_move_lines

    def _create_partial_reversal_move_from_session_closing(self, order):
        """
        Create a misc move to reverse POS orders and "remove" it from the
        POS closing entry. This is done by taking data from the orders
        and using it to somewhat replicate the resulting entry in orders
        to reverse partially the movements done in the POS closing entry.
        """
        self.ensure_one()
        order.ensure_one()
        order.account_move.ensure_one()

        reverse_move_lines = []
        invoice_to_reverse = order.account_move
        original_move = self.refunds_move_id if order.is_refund_or_negative() else self.sales_move_id
        reverse_move_lines += self._prepare_account_move_line_commands_for_reversal(
            order,
            invoice_to_reverse,
        )

        rounding_line = invoice_to_reverse.line_ids.filtered(
            lambda line: line.display_type == 'rounding',
        )
        if rounding_line:
            matching_line = original_move.line_ids.filtered(
                lambda line: line.display_type == 'rounding',
            )
            reverse_move_lines.append(Command.create({
                'name': _("Rounding reversal: %s", matching_line.name),
                'account_id': matching_line.account_id.id,
                'partner_id': matching_line.partner_id.id,
                'currency_id': order.company_id.currency_id.id,
                'amount_currency': -rounding_line.amount_currency,
                'balance': -rounding_line.balance,
                'display_type': matching_line.display_type,
            }))

        payment_lines = invoice_to_reverse.line_ids.filtered(
            lambda line: line.display_type == 'payment_term',
        )
        for idx, payment in enumerate(payment_lines):
            matching_line = original_move.line_ids.filtered(
                lambda line: line.display_type == 'payment_term',
            )[idx]
            receivable_line = Command.create({
                'name': _("Payment reversal %s", matching_line.name),
                'account_id': matching_line.account_id.id,
                'partner_id': matching_line.partner_id.id,
                'currency_id': order.company_id.currency_id.id,
                'amount_currency': -payment.amount_currency,
                'balance': -payment.balance,
                'display_type': 'payment_term',
            })
            reverse_move_lines.append(receivable_line)

        Move = self.env['account.move'].sudo().with_company(order.company_id)
        move_ctx = Move.with_context(
            linked_to_pos=True,
        )

        return move_ctx.create({
            'invoice_cash_rounding_id': invoice_to_reverse.invoice_cash_rounding_id.id,
            'date': fields.Date.today(),
            'reversed_pos_order_id': order.id,
            'ref': self.env._("Convert POS Order to Invoice"),
            'line_ids': reverse_move_lines,
            'journal_id': original_move.journal_id.id,
            'reversed_entry_id': original_move.id,
            'pos_session_ids': [(4, self.id)],
            'always_tax_exigible': True,
        })
