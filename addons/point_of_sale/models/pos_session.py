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
    cash_control = fields.Boolean(
        related='config_id.cash_control',
        string='Cash Control',
        readonly=True,
        store=True)  # Need to be stored in case of change of config
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

            if params.comodel_name:
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
            'opening_notes': self.opening_notes,
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
            'amount_authorized_diff': self.config_id.amount_authorized_diff if self.config_id.set_maximum_difference else None,
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
