# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
from datetime import timedelta
from itertools import groupby, starmap
from markupsafe import Markup

from odoo import api, fields, models, _, Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import float_is_zero, float_compare, plaintext2html, split_every
from odoo.tools.constants import PREFETCH_MAX
from odoo.service.common import exp_version
from odoo.osv.expression import AND


class PosSession(models.Model):
    _name = 'pos.session'
    _order = 'id desc'
    _description = 'Point of Sale Session'
    _inherit = ['mail.thread', 'mail.activity.mixin', "pos.bus.mixin", 'pos.load.mixin']

    POS_SESSION_STATE = [
        ('opening_control', 'Opening Control'),  # method action_pos_session_open
        ('opened', 'In Progress'),               # method action_pos_session_closing_control
        ('closing_control', 'Closing Control'),  # method action_pos_session_close
        ('closed', 'Closed & Posted'),
    ]

    company_id = fields.Many2one('res.company', related='config_id.company_id', string="Company", readonly=True)

    config_id = fields.Many2one(
        'pos.config', string='Point of Sale',
        required=True,
        index=True)
    name = fields.Char(string='Session ID', required=True, readonly=True, default='/')
    user_id = fields.Many2one(
        'res.users', string='Opened By',
        required=True,
        index=True,
        readonly=False,
        default=lambda self: self.env.uid,
        ondelete='restrict')
    currency_id = fields.Many2one('res.currency', related='config_id.currency_id', string="Currency", readonly=False)
    start_at = fields.Datetime(string='Opening Date', readonly=True)
    stop_at = fields.Datetime(string='Closing Date', readonly=True, copy=False)

    state = fields.Selection(
        POS_SESSION_STATE, string='Status',
        required=True, readonly=True,
        index=True, copy=False, default='opening_control')

    order_seq_id = fields.Many2one('ir.sequence', string='Order Sequence', readonly=True, copy=False, help='Used to generate the OOOO part of the pos_reference field of the pos.order model.')
    login_number_seq_id = fields.Many2one('ir.sequence', string='Login Number Sequence', readonly=True, copy=False, help='Determines the number of times the UI is opened. It is used as proxy to the identity of the device where the UI is opened. And as such, it is the LL part of the pos_reference field of the pos.order model.')

    opening_notes = fields.Text(string="Opening Notes")
    closing_notes = fields.Text(string="Closing Notes")
    cash_control = fields.Boolean(compute='_compute_cash_control', string='Has Cash Control')
    cash_journal_id = fields.Many2one('account.journal', compute='_compute_cash_journal', string='Cash Journal', store=True)

    cash_register_balance_end_real = fields.Monetary(
        string="Ending Balance",
        readonly=True)
    cash_register_balance_start = fields.Monetary(
        string="Starting Balance",
        readonly=True)
    cash_register_balance_end = fields.Monetary(
        compute='_compute_cash_balance',
        string="Theoretical Closing Balance",
        help="Opening balance summed to all cash transactions.",
        readonly=True)
    cash_register_difference = fields.Monetary(
        compute='_compute_cash_balance',
        string='Before Closing Difference',
        help="Difference between the theoretical closing balance and the real closing balance.",
        readonly=True)

    # Total Cash In/Out
    cash_real_transaction = fields.Monetary(string='Transaction', readonly=True)

    order_ids = fields.One2many('pos.order', 'session_id',  string='Orders')
    order_count = fields.Integer(compute='_compute_order_count')
    statement_line_ids = fields.One2many('account.bank.statement.line', 'pos_session_id', string='Cash Lines', readonly=True)
    failed_pickings = fields.Boolean(compute='_compute_picking_count')
    picking_count = fields.Integer(compute='_compute_picking_count')
    picking_ids = fields.One2many('stock.picking', 'pos_session_id')
    rescue = fields.Boolean(string='Recovery Session',
        help="Auto-generated session for orphan orders, ignored in constraints",
        readonly=True,
        copy=False)
    move_id = fields.Many2one('account.move', string='Journal Entry', index=True)
    payment_method_ids = fields.Many2many('pos.payment.method', related='config_id.payment_method_ids', string='Payment Methods')
    total_payments_amount = fields.Float(compute='_compute_total_payments_amount', string='Total Payments Amount')
    is_in_company_currency = fields.Boolean('Is Using Company Currency', compute='_compute_is_in_company_currency')
    update_stock_at_closing = fields.Boolean('Stock should be updated at closing')
    bank_payment_ids = fields.One2many('account.payment', 'pos_session_id', 'Bank Payments', help='Account payments representing aggregated and bank split payments.')

    _uniq_name = models.Constraint(
        'unique(name)',
        'The name of this POS Session must be unique!',
    )

    @api.model
    def _load_pos_data_relations(self, model, fields):
        model_fields = self.env[model]._fields
        relations = {}

        for name, params in model_fields.items():
            if name not in fields and len(fields) != 0:
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
    def _load_pos_data_models(self, config_id):
        return ['pos.config', 'pos.preset', 'resource.calendar.attendance', 'pos.order', 'pos.order.line', 'pos.pack.operation.lot', 'pos.payment', 'pos.payment.method', 'pos.printer',
            'pos.category', 'pos.bill', 'res.company', 'account.tax', 'account.tax.group', 'product.template', 'product.product', 'product.attribute', 'product.attribute.custom.value',
            'product.template.attribute.line', 'product.template.attribute.value', 'product.combo', 'product.combo.item', 'product.packaging', 'res.users', 'res.partner',
            'decimal.precision', 'uom.uom', 'uom.category', 'res.country', 'res.country.state', 'res.lang', 'product.pricelist', 'product.pricelist.item', 'product.category',
            'account.cash.rounding', 'account.fiscal.position', 'account.fiscal.position.tax', 'stock.picking.type', 'res.currency', 'pos.note', 'ir.ui.view', 'product.tag', 'ir.module.module']

    @api.model
    def _load_pos_data_domain(self, data):
        return [('id', '=', self.id)]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return [
            'id', 'name', 'user_id', 'config_id', 'start_at', 'stop_at',
            'payment_method_ids', 'state', 'update_stock_at_closing', 'cash_register_balance_start', 'access_token'
        ]

    def _load_pos_data(self, data):
        domain = self._load_pos_data_domain(data)
        fields = self._load_pos_data_fields(self.config_id.id)
        data = self.search_read(domain, fields, load=False, limit=1)
        server_date = self.env.context.get('pos_last_server_date')
        data[0]['_partner_commercial_fields'] = self.env['res.partner']._commercial_fields()
        data[0]['_server_version'] = exp_version()
        data[0]['_base_url'] = self.get_base_url()
        data[0]['_data_server_date'] = server_date or self.env.cr.now()
        data[0]['_has_cash_move_perm'] = self.env.user.has_group('account.group_account_invoice')
        data[0]['_has_available_products'] = self._pos_has_valid_product()
        data[0]['_pos_special_products_ids'] = self.env['pos.config']._get_special_products().ids
        return data

    def load_data(self, models_to_load):
        response = {}
        response['pos.session'] = self._load_pos_data(response)

        for model in self._load_pos_data_models(self.config_id.id):
            if models_to_load and model not in models_to_load:
                continue

            try:
                response[model] = self.env[model]._load_pos_data(response)
            except AccessError:
                response[model] = []

        return response

    def load_data_params(self):
        response = {}
        fields = self._load_pos_data_fields(self.config_id.id)
        response['pos.session'] = {
            'fields': fields,
            'relations': self._load_pos_data_relations('pos.session', fields)
        }

        for model in self._load_pos_data_models(self.config_id.id):
            fields = self.env[model]._load_pos_data_fields(self.config_id.id)
            response[model] = {
                'fields': fields,
                'relations': self._load_pos_data_relations(model, fields)
            }

        return response

    def delete_opening_control_session(self):
        self.ensure_one()
        if self.state != 'opening_control' or len(self.order_ids) > 0:
            raise UserError(_("You can only cancel a session that is in opening control state and has no orders."))
        self.sudo().unlink()
        return {
            'status': 'success',
        }

    def get_pos_ui_product_pricelist_item_by_product(self, product_tmpl_ids, product_ids, config_id):
        pricelist_fields = self.env['product.pricelist']._load_pos_data_fields(config_id)
        pricelist_item_fields = self.env['product.pricelist.item']._load_pos_data_fields(config_id)
        today = fields.Date.today()
        pricelist_item_domain = [
            '|',
            ('company_id', '=', False),
            ('company_id', '=', self.company_id.id),
            '|',
            '&', ('product_id', '=', False), ('product_tmpl_id', 'in', product_tmpl_ids),
            ('product_id', 'in', product_ids),
            '|', ('date_start', '=', False), ('date_start', '<=', today),
            '|', ('date_end', '=', False), ('date_end', '>=', today)]

        pricelist_item = self.env['product.pricelist.item'].search(pricelist_item_domain)
        pricelist = pricelist_item.pricelist_id

        return {
            'product.pricelist.item': pricelist_item.read(pricelist_item_fields, load=False),
            'product.pricelist': pricelist.read(pricelist_fields, load=False)
        }

    @api.depends('currency_id', 'company_id.currency_id')
    def _compute_is_in_company_currency(self):
        for session in self:
            session.is_in_company_currency = session.currency_id == session.company_id.currency_id

    @api.depends('payment_method_ids', 'order_ids', 'cash_register_balance_start')
    def _compute_cash_balance(self):
        for session in self:
            cash_payment_method = session.payment_method_ids.filtered('is_cash_count')[:1]
            if cash_payment_method:
                total_cash_payment = 0.0
                result = self.env['pos.payment']._read_group([('session_id', '=', session.id), ('payment_method_id', '=', cash_payment_method.id)], aggregates=['amount:sum'])
                total_cash_payment = result[0][0] or 0.0
                if session.state == 'closed':
                    total_cash = session.cash_real_transaction + total_cash_payment
                else:
                    total_cash = sum(session.statement_line_ids.mapped('amount')) + total_cash_payment

                session.cash_register_balance_end = session.cash_register_balance_start + total_cash
                session.cash_register_difference = session.cash_register_balance_end_real - session.cash_register_balance_end
            else:
                session.cash_register_balance_end = 0.0
                session.cash_register_difference = 0.0

    @api.depends('order_ids.payment_ids.amount')
    def _compute_total_payments_amount(self):
        result = self.env['pos.payment']._read_group([('session_id', 'in', self.ids)], ['session_id'], ['amount:sum'])
        session_amount_map = {session.id: amount for session, amount in result}
        for session in self:
            session.total_payments_amount = session_amount_map.get(session.id) or 0

    def _compute_order_count(self):
        orders_data = self.env['pos.order']._read_group([('session_id', 'in', self.ids)], ['session_id'], ['__count'])
        sessions_data = {session.id: count for session, count in orders_data}
        for session in self:
            session.order_count = sessions_data.get(session.id, 0)

    @api.depends('picking_ids', 'picking_ids.state')
    def _compute_picking_count(self):
        for session in self:
            session.picking_count = self.env['stock.picking'].search_count([('pos_session_id', '=', session.id)])
            session.failed_pickings = bool(self.env['stock.picking'].search([('pos_session_id', '=', session.id), ('state', '!=', 'done')], limit=1))

    def action_stock_picking(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('stock.action_picking_tree_ready')
        action['display_name'] = _('Pickings')
        action['context'] = {}
        action['domain'] = [('id', 'in', self.picking_ids.ids)]
        return action

    @api.depends('cash_journal_id')
    def _compute_cash_control(self):
        # Only one cash register is supported by point_of_sale.
        for session in self:
            if session.cash_journal_id:
                session.cash_control = session.config_id.cash_control
            else:
                session.cash_control = False

    @api.depends('config_id', 'payment_method_ids')
    def _compute_cash_journal(self):
        # Only one cash register is supported by point_of_sale.
        for session in self:
            cash_journal = session.payment_method_ids.filtered('is_cash_count')[:1].journal_id
            session.cash_journal_id = cash_journal

    @api.constrains('config_id')
    def _check_pos_config(self):
        onboarding_creation = self.env.context.get('onboarding_creation', False)
        if not onboarding_creation and self.search_count([
                ('state', '!=', 'closed'),
                ('config_id', '=', self.config_id.id),
                ('rescue', '=', False)
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

    def _check_invoices_are_posted(self):
        unposted_invoices = self._get_closed_orders().sudo().with_company(self.company_id).account_move.filtered(lambda x: x.state != 'posted')
        if unposted_invoices:
            raise UserError(_(
                'You cannot close the POS when invoices are not posted.\nInvoices: %s',
                '\n'.join(f'{invoice.name} - {invoice.state}' for invoice in unposted_invoices)
            ))

    def _create_sequences(self):
        for session in self:
            order_seq = self.env['ir.sequence'].sudo().create({
                'name': _("PoS Order Sequence of Session %s", session.id),
                'code': f'pos.order_{session.id}',
            })
            login_number_seq = self.env['ir.sequence'].sudo().create({
                'name': _("Login Number Sequence of Session %s", session.id),
                'code': f'pos.login_number_{session.id}',
            })
            session.write({
                'order_seq_id': order_seq.id,
                'login_number_seq_id': login_number_seq.id
            })

    def get_next_order_refs(self, login_number=0, ref_prefix=None, tracking_prefix=''):
        """
        Generates a consistent set of tracking_number, sequence_number and pos_reference for a new pos.order.
        Side-effect: Calling this will increment the order_seq_id.
        Convention: `login_number != 0` means the order is created in the classic PoS UI.
            During self-ordering workflow (kiosk and mobile), login_number = 0 is used.
        Returns:
            (pos_reference: string, sequence_number: int, tracking_number: string)
        """
        self.ensure_one()

        if ref_prefix is None:
            ref_prefix = _("Order")

        sequence_num = int(self.order_seq_id._next())

        YY = fields.Datetime.now().strftime('%y')
        LL = f"{login_number % 100:02}"
        SSS = f"{self.id:03}"
        F = 0  # -> means server-generated pos_reference
        OOOO = f"{sequence_num:04}"
        order_ref = f"{ref_prefix} {YY}{LL}-{SSS}-{F}{OOOO}"

        return order_ref, sequence_num, tracking_prefix + f"{sequence_num:03}"

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
            pos_config = self.env['pos.config'].browse(config_id)

            pos_name = self.env['ir.sequence'].with_context(
                company_id=pos_config.company_id.id
            ).next_by_code('pos.session')
            if vals.get('name'):
                pos_name += ' ' + vals['name']

            update_stock_at_closing = pos_config.company_id.point_of_sale_update_stock_quantities == "closing"

            vals.update({
                'name': pos_name,
                'config_id': config_id,
                'update_stock_at_closing': update_stock_at_closing,
            })

        if self.env.user.has_group('point_of_sale.group_pos_user'):
            sessions = super(PosSession, self.sudo()).create(vals_list)
        else:
            sessions = super().create(vals_list)

        sessions._create_sequences()
        sessions.action_pos_session_open()

        return sessions

    def unlink(self):
        self.statement_line_ids.unlink()
        (self.order_seq_id | self.login_number_seq_id).unlink()
        return super(PosSession, self).unlink()

    def login(self):
        self.ensure_one()
        return self.login_number_seq_id._next()

    def action_pos_session_open(self):
        # we only open sessions that haven't already been opened
        for session in self.filtered(lambda session: session.state == 'opening_control'):
            values = {}
            if not session.start_at:
                values['start_at'] = fields.Datetime.now()
            if session.config_id.cash_control and not session.rescue:
                last_session = self.search([('config_id', '=', session.config_id.id), ('id', '!=', session.id)], limit=1)
                session.cash_register_balance_start = last_session.cash_register_balance_end_real  # defaults to 0 if lastsession is empty
            session.write(values)
        return True

    def action_pos_session_closing_control(self, balancing_account=False, amount_to_balance=0, bank_payment_method_diffs=None):
        bank_payment_method_diffs = bank_payment_method_diffs or {}
        for session in self:
            if any(order.state == 'draft' for order in session.order_ids):
                raise UserError(_("You cannot close the POS when orders are still in draft"))
            if session.state == 'closed':
                raise UserError(_('This session is already closed.'))
            stop_at = self.stop_at or fields.Datetime.now()
            session.write({'state': 'closing_control', 'stop_at': stop_at})
            if not session.config_id.cash_control:
                return session.action_pos_session_close(balancing_account, amount_to_balance, bank_payment_method_diffs)
            # If the session is in rescue, we only compute the payments in the cash register
            # It is not yet possible to close a rescue session through the front end, see `close_session_from_ui`
            if session.rescue and session.config_id.cash_control:
                default_cash_payment_method_id = self.payment_method_ids.filtered(lambda pm: pm.type == 'cash')[0]
                orders = self._get_closed_orders()
                total_cash = sum(
                    orders.payment_ids.filtered(lambda p: p.payment_method_id == default_cash_payment_method_id).mapped('amount')
                ) + self.cash_register_balance_start

                session.cash_register_balance_end_real = total_cash

            return session.action_pos_session_validate(balancing_account, amount_to_balance, bank_payment_method_diffs)


    def action_pos_session_validate(self, balancing_account=False, amount_to_balance=0, bank_payment_method_diffs=None):
        bank_payment_method_diffs = bank_payment_method_diffs or {}
        return self.action_pos_session_close(balancing_account, amount_to_balance, bank_payment_method_diffs)

    def action_pos_session_close(self, balancing_account=False, amount_to_balance=0, bank_payment_method_diffs=None):
        bank_payment_method_diffs = bank_payment_method_diffs or {}
        # Session without cash payment method will not have a cash register.
        # However, there could be other payment methods, thus, session still
        # needs to be validated.
        return self._validate_session(balancing_account, amount_to_balance, bank_payment_method_diffs)

    def _validate_session(self, balancing_account=False, amount_to_balance=0, bank_payment_method_diffs=None):
        bank_payment_method_diffs = bank_payment_method_diffs or {}
        self.ensure_one()
        data = {}
        sudo = self.env.user.has_group('point_of_sale.group_pos_user')
        if self.order_ids.filtered(lambda o: o.state != 'cancel') or self.sudo().statement_line_ids:
            self.cash_real_transaction = sum(self.sudo().statement_line_ids.mapped('amount'))
            if self.state == 'closed':
                raise UserError(_('This session is already closed.'))
            self._check_if_no_draft_orders()
            self._check_invoices_are_posted()
            cash_difference_before_statements = self.cash_register_difference
            if self.update_stock_at_closing:
                self._create_picking_at_end_of_session()
                self._get_closed_orders().filtered(lambda o: not o.is_total_cost_computed)._compute_total_cost_at_session_closing(self.picking_ids.move_ids)
            try:
                with self.env.cr.savepoint():
                    data = self.with_company(self.company_id).with_context(check_move_validity=False, skip_invoice_sync=True)._create_account_move(balancing_account, amount_to_balance, bank_payment_method_diffs)
            except AccessError as e:
                if sudo:
                    data = self.sudo().with_company(self.company_id).with_context(check_move_validity=False, skip_invoice_sync=True)._create_account_move(balancing_account, amount_to_balance, bank_payment_method_diffs)
                else:
                    raise e

            balance = sum(self.move_id.line_ids.mapped('balance'))
            try:
                with self.move_id._check_balanced({'records': self.move_id.sudo()}):
                    pass
            except UserError:
                # Creating the account move is just part of a big database transaction
                # when closing a session. There are other database changes that will happen
                # before attempting to create the account move, such as, creating the picking
                # records.
                # We don't, however, want them to be committed when the account move creation
                # failed; therefore, we need to roll back this transaction before showing the
                # close session wizard.
                self.env.cr.rollback()
                return self._close_session_action(balance)

            self.sudo()._post_statement_difference(cash_difference_before_statements)
            if self.move_id.line_ids:
                self.move_id.sudo().with_company(self.company_id)._post()
                # Set the uninvoiced orders' state to 'done'
                self.env['pos.order'].search([('session_id', '=', self.id), ('state', '=', 'paid')]).write({'state': 'done'})
            else:
                self.move_id.sudo().unlink()
            self.sudo().with_company(self.company_id)._reconcile_account_move_lines(data)
        else:
            self.sudo()._post_statement_difference(self.cash_register_difference)

        if self.config_id.order_edit_tracking:
            edited_orders = self.order_ids.filtered(lambda o: o.is_edited)
            if len(edited_orders) > 0:
                body = _("Edited order(s) during the session:%s",
                    Markup("<br/><ul>%s</ul>") % Markup().join(Markup("<li>%s</li>") % order._get_html_link() for order in edited_orders)
                )
                self.message_post(body=body)

        # Make sure to trigger reordering rules
        self.picking_ids.move_ids.sudo()._trigger_scheduler()

        self.write({'state': 'closed'})
        return True

    def _post_statement_difference(self, amount):
        if amount:
            if self.config_id.cash_control:
                st_line_vals = {
                    'journal_id': self.cash_journal_id.id,
                    'amount': amount,
                    'date': self.statement_line_ids.sorted()[-1:].date or fields.Date.context_today(self),
                    'pos_session_id': self.id,
                }

            if amount < 0.0:
                if not self.cash_journal_id.loss_account_id:
                    raise UserError(
                        _('Please go on the %s journal and define a Loss Account. This account will be used to record cash difference.',
                          self.cash_journal_id.name))

                st_line_vals['payment_ref'] = _("Cash difference observed during the counting (Loss) - closing")
                st_line_vals['counterpart_account_id'] = self.cash_journal_id.loss_account_id.id
            else:
                # self.cash_register_difference  > 0.0
                if not self.cash_journal_id.profit_account_id:
                    raise UserError(
                        _('Please go on the %s journal and define a Profit Account. This account will be used to record cash difference.',
                          self.cash_journal_id.name))

                st_line_vals['payment_ref'] = _("Cash difference observed during the counting (Profit) - closing")
                st_line_vals['counterpart_account_id'] = self.cash_journal_id.profit_account_id.id

            created_line = self.env['account.bank.statement.line'].create(st_line_vals)

            if created_line:
                created_line.move_id.message_post(body=_(
                    "Related Session: %(link)s",
                    link=self._get_html_link()
                ))

    def _close_session_action(self, amount_to_balance):
        # NOTE This can't handle `bank_payment_method_diffs` because there is no field in the wizard that can carry it.
        default_account = self._get_balancing_account()
        wizard = self.env['pos.close.session.wizard'].create({
            'amount_to_balance': amount_to_balance,
            'account_id': default_account.id,
            'account_readonly': not self.env.user.has_group('account.group_account_readonly'),
            'message': _("There is a difference between the amounts to post and the amounts of the orders, it is probably caused by taxes or accounting configurations changes.")
        })
        return {
            'name': _("Force Close Session"),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'pos.close.session.wizard',
            'res_id': wizard.id,
            'target': 'new',
            'context': {**self.env.context, 'active_ids': self.ids, 'active_model': 'pos.session'},
        }

    def close_session_from_ui(self, bank_payment_method_diff_pairs=None):
        """Calling this method will try to close the session.

        param bank_payment_method_diff_pairs: list[(int, float)]
            Pairs of payment_method_id and diff_amount which will be used to post
            loss/profit when closing the session.

        If successful, it returns {'successful': True}
        Otherwise, it returns {'successful': False, 'message': str, 'redirect': bool}.
        'redirect' is a boolean used to know whether we redirect the user to the back end or not.
        When necessary, error (i.e. UserError, AccessError) is raised which should redirect the user to the back end.
        """
        bank_payment_method_diffs = dict(bank_payment_method_diff_pairs or [])
        self.ensure_one()
        # Even if this is called in `post_closing_cash_details`, we need to call this here too for case
        # where cash_control = False
        open_order_ids = self.order_ids.filtered(lambda o: o.state == 'draft').ids
        check_closing_session = self._cannot_close_session(bank_payment_method_diffs)
        if check_closing_session:
            check_closing_session['open_order_ids'] = open_order_ids
            return check_closing_session

        validate_result = self.action_pos_session_closing_control(bank_payment_method_diffs=bank_payment_method_diffs)

        # If an error is raised, the user will still be redirected to the back end to manually close the session.
        # If the return result is a dict, this means that normally we have a redirection or a wizard => we redirect the user
        if isinstance(validate_result, dict):
            # imbalance accounting entry
            return {
                'open_order_ids': open_order_ids,
                'successful': False,
                'message': validate_result.get('name'),
                'redirect': True
            }

        self.post_close_register_message()

        return {'successful': True}

    def post_close_register_message(self):
        self.message_post(body=_('Closed Register'))

    def update_closing_control_state_session(self, notes):
        # Prevent closing the session again if it was already closed
        if self.state == 'closed':
            raise UserError(_('This session is already closed.'))
        # Prevent the session to be opened again.
        self.write({'state': 'closing_control', 'stop_at': fields.Datetime.now(), 'closing_notes': notes})
        self._post_cash_details_message('Closing', self.cash_register_balance_end, self.cash_register_difference, notes)

    def post_closing_cash_details(self, counted_cash):
        """
        Calling this method will try store the cash details during the session closing.

        :param counted_cash: float, the total cash the user counted from its cash register
        If successful, it returns {'successful': True}
        Otherwise, it returns {'successful': False, 'message': str, 'redirect': bool}.
        'redirect' is a boolean used to know whether we redirect the user to the back end or not.
        When necessary, error (i.e. UserError, AccessError) is raised which should redirect the user to the back end.
        """
        self.ensure_one()
        check_closing_session = self._cannot_close_session()
        if check_closing_session:
            open_order_ids = self.order_ids.filtered(lambda o: o.state == 'draft').ids
            check_closing_session['open_order_ids'] = open_order_ids
            return check_closing_session

        if not self.cash_journal_id:
            # The user is blocked anyway, this user error is mostly for developers that try to call this function
            raise UserError(_("There is no cash register in this session."))

        self.cash_register_balance_end_real = counted_cash

        return {'successful': True}

    def _create_diff_account_move_for_split_payment_method(self, payment_method, diff_amount):
        self.ensure_one()

        get_diff_vals_result = self._get_diff_vals(payment_method.id, diff_amount)
        if not get_diff_vals_result:
            return

        source_vals, dest_vals = get_diff_vals_result
        diff_move = self.env['account.move'].create({
            'journal_id': payment_method.journal_id.id,
            'date': fields.Date.context_today(self),
            'ref': self._get_diff_account_move_ref(payment_method),
            'line_ids': [Command.create(source_vals), Command.create(dest_vals)]
        })
        diff_move._post()

    def _get_diff_account_move_ref(self, payment_method):
        return _('Closing difference in %(payment_method)s (%(session)s)', payment_method=payment_method.name, session=self.name)

    def _get_diff_vals(self, payment_method_id, diff_amount):
        payment_method = self.env['pos.payment.method'].browse(payment_method_id)
        diff_compare_to_zero = self.currency_id.compare_amounts(diff_amount, 0)
        source_account = payment_method.outstanding_account_id
        destination_account = self.env['account.account']

        if (diff_compare_to_zero > 0):
            destination_account = payment_method.journal_id.profit_account_id
        elif (diff_compare_to_zero < 0):
            destination_account = payment_method.journal_id.loss_account_id

        if (diff_compare_to_zero == 0 or not source_account):
            return False

        amounts = self._update_amounts({'amount': 0, 'amount_converted': 0}, {'amount': diff_amount}, self.stop_at)
        source_vals = self._debit_amounts({'account_id': source_account.id}, amounts['amount'], amounts['amount_converted'])
        dest_vals = self._credit_amounts({'account_id': destination_account.id}, amounts['amount'], amounts['amount_converted'])
        return [source_vals, dest_vals]

    def _cannot_close_session(self, bank_payment_method_diffs=None):
        """
        Add check in this method if you want to return or raise an error when trying to either post cash details
        or close the session. Raising an error will always redirect the user to the back end.
        It should return {'successful': False, 'message': str, 'redirect': bool} if we can't close the session
        """
        bank_payment_method_diffs = bank_payment_method_diffs or {}
        if any(order.state == 'draft' for order in self.order_ids):
            return {'successful': False, 'message': _("You cannot close the POS when orders are still in draft"), 'redirect': False}
        if self.state == 'closed':
            return {
                'successful': False,
                'type': 'alert',
                'title': 'Session already closed',
                'message': _("The session has been already closed by another User. "
                            "All sales completed in the meantime have been saved in a "
                            "Rescue Session, which can be reviewed anytime and posted "
                            "to Accounting from Point of Sale's dashboard."),
                'redirect': True
            }
        if bank_payment_method_diffs:
            no_loss_account = self.env['account.journal']
            no_profit_account = self.env['account.journal']
            for payment_method in self.env['pos.payment.method'].browse(bank_payment_method_diffs.keys()):
                journal = payment_method.journal_id
                compare_to_zero = self.currency_id.compare_amounts(bank_payment_method_diffs.get(payment_method.id), 0)
                if compare_to_zero == -1 and not journal.loss_account_id:
                    no_loss_account |= journal
                elif compare_to_zero == 1 and not journal.profit_account_id:
                    no_profit_account |= journal
            message = ''
            if no_loss_account:
                message += _("Need loss account for the following journals to post the lost amount: %s\n", ', '.join(no_loss_account.mapped('name')))
            if no_profit_account:
                message += _("Need profit account for the following journals to post the gained amount: %s", ', '.join(no_profit_account.mapped('name')))
            if message:
                return {'successful': False, 'message': message, 'redirect': False}

    def get_closing_control_data(self):
        if not self.env.user.has_group('point_of_sale.group_pos_user'):
            raise AccessError(_("You don't have the access rights to get the point of sale closing control data."))
        self.ensure_one()
        orders = self._get_closed_orders()
        payments = orders.payment_ids.filtered(lambda p: p.payment_method_id.type != "pay_later")
        cash_payment_method_ids = self.payment_method_ids.filtered(lambda pm: pm.type == 'cash')
        default_cash_payment_method_id = cash_payment_method_ids[0] if cash_payment_method_ids else None
        default_cash_payments = payments.filtered(lambda p: p.payment_method_id == default_cash_payment_method_id) if default_cash_payment_method_id else []
        total_default_cash_payment_amount = sum(default_cash_payments.mapped('amount')) if default_cash_payment_method_id else 0
        non_cash_payment_method_ids = self.payment_method_ids - default_cash_payment_method_id if default_cash_payment_method_id else self.payment_method_ids
        non_cash_payments_grouped_by_method_id = {pm: orders.payment_ids.filtered(lambda p: p.payment_method_id == pm) for pm in non_cash_payment_method_ids}

        cash_in_count = 0
        cash_out_count = 0
        cash_in_out_list = []
        for cash_move in self.sudo().statement_line_ids.sorted('create_date'):
            if cash_move.amount > 0:
                cash_in_count += 1
                name = f'Cash in {cash_in_count}'
            else:
                cash_out_count += 1
                name = f'Cash out {cash_out_count}'
            cash_in_out_list.append({
                'name': cash_move.payment_ref if cash_move.payment_ref else name,
                'amount': cash_move.amount
            })

        return {
            'orders_details': {
                'quantity': len(orders),
                'amount': sum(orders.mapped('amount_total'))
            },
            'opening_notes': self.opening_notes,
            'default_cash_details': {
                'name': default_cash_payment_method_id.name,
                'amount': self.cash_register_balance_start
                          + total_default_cash_payment_amount
                          + sum(self.sudo().statement_line_ids.mapped('amount')),
                'opening': self.cash_register_balance_start,
                'payment_amount': total_default_cash_payment_amount,
                'moves': cash_in_out_list,
                'id': default_cash_payment_method_id.id
            } if default_cash_payment_method_id else {},
            'non_cash_payment_methods': [{
                'name': pm.name,
                'amount': sum(non_cash_payments_grouped_by_method_id[pm].mapped('amount')),
                'number': len(non_cash_payments_grouped_by_method_id[pm]),
                'id': pm.id,
                'type': pm.type,
            } for pm in non_cash_payment_method_ids],
            'is_manager': self.env.user.has_group("point_of_sale.group_pos_manager"),
            'amount_authorized_diff': self.config_id.amount_authorized_diff if self.config_id.set_maximum_difference else None
        }

    def _create_picking_at_end_of_session(self):
        self.ensure_one()
        lines_grouped_by_dest_location = {}
        picking_type = self.config_id.picking_type_id

        if not picking_type or not picking_type.default_location_dest_id:
            session_destination_id = self.env['stock.warehouse']._get_partner_locations()[0].id
        else:
            session_destination_id = picking_type.default_location_dest_id.id

        for order in self._get_closed_orders():
            if order.company_id.anglo_saxon_accounting and order.is_invoiced or order.shipping_date:
                continue
            destination_id = order.partner_id.property_stock_customer.id or session_destination_id
            if destination_id in lines_grouped_by_dest_location:
                lines_grouped_by_dest_location[destination_id] |= order.lines
            else:
                lines_grouped_by_dest_location[destination_id] = order.lines

        for location_dest_id, lines in lines_grouped_by_dest_location.items():
            pickings = self.env['stock.picking']._create_picking_from_pos_order_lines(location_dest_id, lines, picking_type)
            pickings.write({'pos_session_id': self.id, 'origin': self.name})

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
            imbalance_amount_session = self.company_id.currency_id._convert(imbalance_amount, self.currency_id, self.company_id, fields.Date.context_today(self))
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

        data = {'bank_payment_method_diffs': bank_payment_method_diffs or {}}
        data = self._accumulate_amounts(data)
        data = self._create_non_reconciliable_move_lines(data)
        data = self._create_bank_payment_moves(data)
        data = self._create_pay_later_receivable_lines(data)
        data = self._create_cash_statement_lines_and_cash_move_lines(data)
        data = self._create_invoice_receivable_lines(data)
        data = self._create_stock_output_lines(data)
        if balancing_account and amount_to_balance:
            data = self._create_balancing_line(data, balancing_account, amount_to_balance)

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
        stock_expense = defaultdict(amounts)
        stock_return = defaultdict(amounts)
        stock_output = defaultdict(amounts)
        rounding_difference = {'amount': 0.0, 'amount_converted': 0.0}
        # Track the receivable lines of the order's invoice payment moves for reconciliation
        # These receivable lines are reconciled to the corresponding invoice receivable lines
        # of this session's move_id.
        combine_inv_payment_receivable_lines = defaultdict(lambda: self.env['account.move.line'])
        split_inv_payment_receivable_lines = defaultdict(lambda: self.env['account.move.line'])
        pos_receivable_account = self.company_id.account_default_pos_receivable_account_id
        currency_rounding = self.currency_id.rounding
        closed_orders = self._get_closed_orders()
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
                AccountTax._add_accounting_data_in_base_lines_tax_details(base_lines, order.company_id)
                tax_results = AccountTax._prepare_tax_lines(base_lines, order.company_id)
                total_amount_currency = 0.0
                for base_line, to_update in tax_results['base_lines_to_update']:
                    # Combine sales/refund lines
                    sale_key = (
                        # account
                        base_line['account_id'].id,
                        # sign
                        -1 if base_line['is_refund'] else 1,
                        # for taxes
                        tuple(base_line['record'].tax_ids_after_fiscal_position.flatten_taxes_hierarchy().ids),
                        tuple(base_line['tax_tag_ids'].ids),
                        base_line['product_id'].id if self.config_id.is_closing_entry_by_product else False,
                    )
                    total_amount_currency += to_update['amount_currency']
                    sales[sale_key] = self._update_amounts(
                        sales[sale_key],
                        {
                            'amount': to_update['amount_currency'],
                            'amount_converted': to_update['balance'],
                        },
                        order.date_order,
                    )
                    if self.config_id.is_closing_entry_by_product:
                        sales[sale_key] = self._update_quantities(sales[sale_key], base_line['quantity'])

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

        if self.company_id.anglo_saxon_accounting:
            all_picking_ids = self.order_ids.filtered(lambda p: not p.is_invoiced and not p.shipping_date).picking_ids.ids + self.picking_ids.filtered(lambda p: not p.pos_order_id).ids
            if all_picking_ids:
                # Combine stock lines
                stock_move_sudo = self.env['stock.move'].sudo()
                stock_moves = stock_move_sudo.search([
                    ('picking_id', 'in', all_picking_ids),
                    ('company_id.anglo_saxon_accounting', '=', True),
                    ('product_id.categ_id.property_valuation', '=', 'real_time'),
                    ('product_id.is_storable', '=', True),
                ])
                for stock_moves_batch in split_every(PREFETCH_MAX, stock_moves._ids, stock_moves.browse):
                    candidates = stock_moves_batch\
                        .filtered(lambda m: not bool(m.origin_returned_move_id and sum(m.stock_valuation_layer_ids.mapped('quantity')) >= 0))\
                        .mapped('stock_valuation_layer_ids')
                    for move in stock_moves_batch.with_context(candidates_prefetch_ids=candidates._prefetch_ids):
                        exp_key = move.product_id._get_product_accounts()['expense']
                        out_key = move.product_id.categ_id.property_stock_account_output_categ_id
                        signed_product_qty = move.product_qty
                        if move._is_in():
                            signed_product_qty *= -1
                        amount = signed_product_qty * move.product_id._compute_average_price(0, move.quantity, move)
                        stock_expense[exp_key] = self._update_amounts(stock_expense[exp_key], {'amount': amount}, move.picking_id.date, force_company_currency=True)
                        if move._is_in():
                            stock_return[out_key] = self._update_amounts(stock_return[out_key], {'amount': amount}, move.picking_id.date, force_company_currency=True)
                        else:
                            stock_output[out_key] = self._update_amounts(stock_output[out_key], {'amount': amount}, move.picking_id.date, force_company_currency=True)
        MoveLine = self.env['account.move.line'].with_context(check_move_validity=False, skip_invoice_sync=True)

        data.update({
            'taxes':                               taxes,
            'sales':                               sales,
            'stock_expense':                       stock_expense,
            'split_receivables_bank':              split_receivables_bank,
            'combine_receivables_bank':            combine_receivables_bank,
            'split_receivables_cash':              split_receivables_cash,
            'combine_receivables_cash':            combine_receivables_cash,
            'combine_invoice_receivables':         combine_invoice_receivables,
            'split_receivables_pay_later':         split_receivables_pay_later,
            'combine_receivables_pay_later':       combine_receivables_pay_later,
            'stock_return':                        stock_return,
            'stock_output':                        stock_output,
            'combine_inv_payment_receivable_lines': combine_inv_payment_receivable_lines,
            'rounding_difference':                 rounding_difference,
            'MoveLine':                            MoveLine,
            'split_invoice_receivables': split_invoice_receivables,
            'split_inv_payment_receivable_lines': split_inv_payment_receivable_lines,
        })
        return data

    def _create_non_reconciliable_move_lines(self, data):
        # Create account.move.line records for
        #   - sales
        #   - taxes
        #   - stock expense
        #   - non-cash split receivables (not for automatic reconciliation)
        #   - non-cash combine receivables (not for automatic reconciliation)
        taxes = data.get('taxes')
        sales = data.get('sales')
        stock_expense = data.get('stock_expense')
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

        MoveLine.create(tax_vals)
        move_line_ids = MoveLine.create(list(starmap(self._get_sale_vals, sales.items())))
        for key, ml_id in zip(sales.keys(), move_line_ids.ids):
            sales[key]['move_line_id'] = ml_id
        MoveLine.create(
            [self._get_stock_expense_vals(key, amounts['amount'], amounts['amount_converted']) for key, amounts in stock_expense.items()]
            + rounding_vals
        )

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
        MoveLine.create(vals)
        return data

    def _create_combine_account_payment(self, payment_method, amounts, diff_amount):
        outstanding_account = payment_method.outstanding_account_id
        destination_account = self._get_receivable_account(payment_method)

        if float_compare(amounts['amount'], 0, precision_rounding=self.currency_id.rounding) < 0:
            # revert the accounts because account.payment doesn't accept negative amount.
            outstanding_account, destination_account = destination_account, outstanding_account

        account_payment = self.env['account.payment'].create({
            'amount': abs(amounts['amount']),
            'journal_id': payment_method.journal_id.id,
            'force_outstanding_account_id': outstanding_account.id,
            'destination_account_id': destination_account.id,
            'memo': _('Combine %(payment_method)s POS payments from %(session)s', payment_method=payment_method.name, session=self.name),
            'pos_payment_method_id': payment_method.id,
            'pos_session_id': self.id,
            'company_id': self.company_id.id,
        })
        account_payment.action_post()

        diff_amount_compare_to_zero = self.currency_id.compare_amounts(diff_amount, 0)
        if diff_amount_compare_to_zero != 0:
            self._apply_diff_on_account_payment_move(account_payment, payment_method, diff_amount)

        return account_payment.move_id.line_ids.filtered(lambda line: line.account_id == self._get_receivable_account(payment_method))

    def _apply_diff_on_account_payment_move(self, account_payment, payment_method, diff_amount):
        diff_vals = self._get_diff_vals(payment_method.id, diff_amount)
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
        account_payment.move_id.action_post()

    def _create_split_account_payment(self, payment, amounts):
        payment_method = payment.payment_method_id
        if not payment_method.journal_id:
            return self.env['account.move.line']
        outstanding_account = payment_method.outstanding_account_id
        accounting_partner = self.env["res.partner"]._find_accounting_partner(payment.partner_id)
        destination_account = accounting_partner.property_account_receivable_id

        if float_compare(amounts['amount'], 0, precision_rounding=self.currency_id.rounding) < 0:
            # revert the accounts because account.payment doesn't accept negative amount.
            outstanding_account, destination_account = destination_account, outstanding_account

        account_payment = self.env['account.payment'].create({
            'amount': abs(amounts['amount']),
            'partner_id': payment.partner_id.id,
            'journal_id': payment_method.journal_id.id,
            'force_outstanding_account_id': outstanding_account.id,
            'destination_account_id': destination_account.id,
            'memo': _('%(payment_method)s POS payment of %(partner)s in %(session)s', payment_method=payment_method.name, partner=payment.partner_id.display_name, session=self.name),
            'pos_payment_method_id': payment_method.id,
            'pos_session_id': self.id,
        })
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
            journal_id = payment.payment_method_id.journal_id.id
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
                        payment_method.journal_id.id,
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
        BankStatementLine = self.env['account.bank.statement.line']
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

    def _create_stock_output_lines(self, data):
        # Keep reference to the stock output lines because
        # they are reconciled with output lines in the stock.move's account.move.line
        MoveLine = data.get('MoveLine')
        stock_output = data.get('stock_output')
        stock_return = data.get('stock_return')

        stock_output_vals = defaultdict(list)
        stock_output_lines = {}
        for stock_moves in [stock_output, stock_return]:
            for account, amounts in stock_moves.items():
                stock_output_vals[account].append(self._get_stock_output_vals(account, amounts['amount'], amounts['amount_converted']))

        for output_account, vals in stock_output_vals.items():
            stock_output_lines[output_account] = MoveLine.create(vals)

        data.update({'stock_output_lines': stock_output_lines})
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
        stock_output_lines = data.get('stock_output_lines')
        payment_method_to_receivable_lines = data.get('payment_method_to_receivable_lines')
        payment_to_receivable_lines = data.get('payment_to_receivable_lines')


        all_lines = (
              split_cash_statement_lines
            | combine_cash_statement_lines
            | split_cash_receivable_lines
            | combine_cash_receivable_lines
        )
        all_lines.filtered(lambda line: line.move_id.state != 'posted').move_id._post(soft=False)

        accounts = all_lines.mapped('account_id')
        lines_by_account = [all_lines.filtered(lambda l: l.account_id == account and not l.reconciled) for account in accounts if account.reconcile]
        for lines in lines_by_account:
            lines.reconcile()


        for payment_method, lines in payment_method_to_receivable_lines.items():
            receivable_account = self._get_receivable_account(payment_method)
            if receivable_account.reconcile:
                lines.filtered(lambda line: not line.reconciled).reconcile()

        for payment, lines in payment_to_receivable_lines.items():
            if payment.partner_id.property_account_receivable_id.reconcile:
                lines.filtered(lambda line: not line.reconciled).reconcile()

        # Reconcile invoice payments' receivable lines. But we only do when the account is reconcilable.
        # Though `account_default_pos_receivable_account_id` should be of type receivable, there is currently
        # no constraint for it. Therefore, it is possible to put set a non-reconcilable account to it.
        if self.company_id.account_default_pos_receivable_account_id.reconcile:
            for payment_method in combine_inv_payment_receivable_lines:
                lines = combine_inv_payment_receivable_lines[payment_method] | combine_invoice_receivable_lines.get(payment_method, self.env['account.move.line'])
                lines.filtered(lambda line: not line.reconciled).reconcile()

            for payment in split_inv_payment_receivable_lines:
                lines = split_inv_payment_receivable_lines[payment] | split_invoice_receivable_lines.get(payment, self.env['account.move.line'])
                lines.filtered(lambda line: not line.reconciled).reconcile()

        # reconcile stock output lines
        pickings = self.picking_ids.filtered(lambda p: not p.pos_order_id)
        pickings |= self._get_closed_orders().filtered(lambda o: not o.is_invoiced).mapped('picking_ids')
        stock_moves = self.env['stock.move'].search([('picking_id', 'in', pickings.ids)])
        stock_account_move_lines = self.env['account.move'].search([('stock_move_id', 'in', stock_moves.ids)]).mapped('line_ids')
        for account_id in stock_output_lines:
            ( stock_output_lines[account_id]
            | stock_account_move_lines.filtered(lambda aml: aml.account_id == account_id)
            ).filtered(lambda aml: not aml.reconciled).reconcile()
        return data

    def _get_rounding_difference_vals(self, amount, amount_converted):
        if self.config_id.cash_rounding:
            partial_args = {
                'name': 'Rounding line',
                'move_id': self.move_id.id,
            }
            if float_compare(0.0, amount, precision_rounding=self.currency_id.rounding) > 0:    # loss
                partial_args['account_id'] = self.config_id.rounding_method.loss_account_id.id
                return self._debit_amounts(partial_args, -amount, -amount_converted)

            if float_compare(0.0, amount, precision_rounding=self.currency_id.rounding) < 0:   # profit
                partial_args['account_id'] = self.config_id.rounding_method.profit_account_id.id
                return self._credit_amounts(partial_args, amount, amount_converted)

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

    def _get_sale_vals(self, key, sale_vals):
        account_id, sign, tax_ids, base_tag_ids, product_id = key
        amount = sale_vals['amount']
        amount_converted = sale_vals['amount_converted']
        applied_taxes = self.env['account.tax'].browse(tax_ids)
        if product_id:
            product = self.env['product.product'].browse(product_id)
            product_name = product.display_name
            product_uom = product.uom_id.id
        else:
            product_name = ""
            product_uom = False
        title = 'Sales' if sign == 1 else 'Refund'
        name = '%s untaxed' % title
        if applied_taxes:
            name = '%s %s with %s' % (title, product_name, ', '.join([tax.name for tax in applied_taxes]))
        partial_vals = {
            'name': name,
            'account_id': account_id,
            'move_id': self.move_id.id,
            'tax_ids': [(6, 0, tax_ids)],
            'tax_tag_ids': [(6, 0, base_tag_ids)],
            'product_id': product_id,
            'display_type': 'product',
            'product_uom_id': product_uom,
            'currency_id': self.currency_id.id,
            'amount_currency': amount,
            'balance': amount_converted,
        }
        if partial_vals.get('product_id'):
            partial_vals['quantity'] = sale_vals.get('quantity', 1.00) * sign
        return partial_vals

    def _get_tax_vals(self, key, amount, amount_converted, base_amount_converted):
        account_id, repartition_line_id, tag_ids = key
        tax_rep = self.env['account.tax.repartition.line'].browse(repartition_line_id)
        tax = tax_rep.tax_id
        return {
            'name': tax.name,
            'account_id': account_id,
            'move_id': self.move_id.id,
            'tax_base_amount': abs(base_amount_converted),
            'tax_repartition_line_id': repartition_line_id,
            'tax_tag_ids': [(6, 0, tag_ids)],
            'display_type': 'tax',
            'currency_id': self.currency_id.id,
            'amount_currency': amount,
            'balance': amount_converted,
        }

    def _get_stock_expense_vals(self, exp_account, amount, amount_converted):
        partial_args = {'account_id': exp_account.id, 'move_id': self.move_id.id}
        return self._debit_amounts(partial_args, amount, amount_converted, force_company_currency=True)

    def _get_stock_output_vals(self, out_account, amount, amount_converted):
        partial_args = {'account_id': out_account.id, 'move_id': self.move_id.id}
        return self._credit_amounts(partial_args, amount, amount_converted, force_company_currency=True)

    def _get_combine_statement_line_vals(self, journal_id, amount, payment_method):
        return {
            'date': fields.Date.context_today(self),
            'amount': amount,
            'payment_ref': self.name,
            'pos_session_id': self.id,
            'journal_id': journal_id,
            'counterpart_account_id': self._get_receivable_account(payment_method).id,
        }

    def _get_split_statement_line_vals(self, journal_id, amount, payment):
        accounting_partner = self.env["res.partner"]._find_accounting_partner(payment.partner_id)
        return {
            'date': fields.Date.context_today(self, timestamp=payment.payment_date),
            'amount': amount,
            'payment_ref': payment.name,
            'pos_session_id': self.id,
            'journal_id': journal_id,
            'counterpart_account_id': accounting_partner.property_account_receivable_id.id,
            'partner_id': accounting_partner.id,
        }

    def _update_quantities(self, vals, qty_to_add):
        vals.setdefault('quantity', 0)
        # update quantity
        vals['quantity'] += qty_to_add
        return vals

    def _update_amounts(self, old_amounts, amounts_to_add, date, round=True, force_company_currency=False):
        """Responsible for adding `amounts_to_add` to `old_amounts` considering the currency of the session.

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

        :params old_amounts dict:
            Amounts to update
        :params amounts_to_add dict:
            Amounts used to update the old_amounts
        :params date date:
            Date used for conversion
        :params round bool:
            Same as round parameter of `res.currency._convert`.
            Defaults to True because that is the default of `res.currency._convert`.
            We put it to False if we want to round globally.
        :params force_company_currency bool:
            If True, the values in amounts_to_add are in company's currency.
            Defaults to False because it is only used to anglo-saxon lines.

        :return dict: new amounts combining the values of `old_amounts` and `amounts_to_add`.
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
        if not amounts_to_add.get('base_amount') == None:
            base_amount = amounts_to_add.get('base_amount')
            if self.is_in_company_currency or force_company_currency:
                base_amount_converted = base_amount
            else:
                base_amount_converted = self._amount_converter(base_amount, date, round)

            # update base_amount and base_amount_converted
            new_amounts['base_amount'] += base_amount
            new_amounts['base_amount_converted'] += base_amount_converted

        return new_amounts

    def _round_amounts(self, amounts):
        new_amounts = {}
        for key, amount in amounts.items():
            if key == 'amount_converted':
                # round the amount_converted using the company currency.
                new_amounts[key] = self.company_id.currency_id.round(amount)
            else:
                new_amounts[key] = self.currency_id.round(amount)
        return new_amounts

    def _credit_amounts(self, partial_move_line_vals, amount, amount_converted, force_company_currency=False):
        """ `partial_move_line_vals` is completed by `credit`ing the given amounts.

        NOTE Amounts in PoS are in the currency of journal_id in the session.config_id.
        This means that amount fields in any pos record are actually equivalent to amount_currency
        in account module. Understanding this basic is important in correctly assigning values for
        'amount' and 'amount_currency' in the account.move.line record.

        :param partial_move_line_vals dict:
            initial values in creating account.move.line
        :param amount float:
            amount derived from pos.payment, pos.order, or pos.order.line records
        :param amount_converted float:
            converted value of `amount` from the given `session_currency` to company currency

        :return dict: complete values for creating 'amount.move.line' record
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
        """ `partial_move_line_vals` is completed by `debit`ing the given amounts.

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
        }

    def _amount_converter(self, amount, date, round):
        # self should be single record as this method is only called in the subfunctions of self._validate_session
        return self.currency_id._convert(amount, self.company_id.currency_id, self.company_id, date, round=round)

    def show_cash_register(self):
        return {
            'name': _('Cash register'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.bank.statement.line',
            'view_mode': 'list,kanban',
            'domain': [('id', 'in', self.statement_line_ids.ids)],
        }

    def show_journal_items(self):
        self.ensure_one()
        all_related_moves = self._get_related_account_moves()
        return {
            'name': _('Journal Items'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'list',
            'view_id':self.env.ref('account.view_move_line_tree').id,
            'domain': [('id', 'in', all_related_moves.mapped('line_ids').ids)],
            'context': {
                'journal_type':'general',
                'search_default_group_by_move': 1,
                'group_by':'move_id', 'search_default_posted':1,
            },
        }

    def _get_other_related_moves(self):
        # TODO This is not an ideal way to get the diff account.move's for
        # the session. It would be better if there is a relation field where
        # these moves are saved.

        # Unfortunately, the 'ref' of account.move is not indexed, so
        # we are querying over the account.move.line because its 'ref' is indexed.
        # And yes, we are only concern for split bank payment methods.
        diff_lines_ref = [self._get_diff_account_move_ref(pm) for pm in self.payment_method_ids if pm.type == 'bank' and pm.split_transactions]
        cost_move_lines = ['pos_order_'+str(rec.id) for rec in self._get_closed_orders()]
        return self.env['account.move.line'].search([('ref', 'in', diff_lines_ref + cost_move_lines)]).mapped('move_id')

    def _get_related_account_moves(self):
        pickings = self.picking_ids | self._get_closed_orders().mapped('picking_ids')
        invoices = self.mapped('order_ids.account_move')
        invoice_payments = self.mapped('order_ids.payment_ids.account_move_id')
        stock_account_moves = pickings.mapped('move_ids.account_move_ids')
        cash_moves = self.statement_line_ids.mapped('move_id')
        bank_payment_moves = self.bank_payment_ids.mapped('move_id')
        other_related_moves = self._get_other_related_moves()
        return invoices | invoice_payments | self.move_id | stock_account_moves | cash_moves | bank_payment_moves | other_related_moves

    def _get_receivable_account(self, payment_method):
        """Returns the default pos receivable account if no receivable_account_id is set on the payment method."""
        return payment_method.receivable_account_id or self.company_id.account_default_pos_receivable_account_id

    def action_show_payments_list(self):
        return {
            'name': _('Payments'),
            'type': 'ir.actions.act_window',
            'res_model': 'pos.payment',
            'view_mode': 'list,form',
            'domain': [('session_id', '=', self.id)],
            'context': {'search_default_group_by_payment_method': 1}
        }

    def open_frontend_cb(self):
        """Open the pos interface with config_id as an extra argument.

        In vanilla PoS each user can only have one active session, therefore it was not needed to pass the config_id
        on opening a session. It is also possible to login to sessions created by other users.

        :returns: dict
        """
        if not self.ids:
            return {}
        return self.config_id.open_ui()

    def set_opening_control(self, cashbox_value: int, notes: str):
        self.state = 'opened'

        cash_payment_method_ids = self.config_id.payment_method_ids.filtered(lambda pm: pm.is_cash_count)
        if cash_payment_method_ids:
            self.opening_notes = notes
            difference = cashbox_value - self.cash_register_balance_start
            self.cash_register_balance_start = cashbox_value
            self._post_cash_details_message('Opening cash', self.cash_register_balance_start, difference, notes)
        elif notes:
            message = _('Opening control message: ')
            message += notes
            self.message_post(body=plaintext2html(message))

    def _post_cash_details_message(self, state, expected, difference, notes):
        message = (state + " difference: " + self.currency_id.format(difference) + '\n' +
           state + " expected: " + self.currency_id.format(expected) + '\n' +
           state + " counted: " + self.currency_id.format(expected + difference) + '\n')

        if notes:
            message += _('Opening control message: ')
            message += notes
        if message:
            self.message_post(body=plaintext2html(message))

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
                    )
                )

    def _check_if_no_draft_orders(self):
        draft_orders = self.order_ids.filtered(lambda order: order.state == 'draft')
        if draft_orders:
            raise UserError(_(
                    'There are still orders in draft state in the session. '
                    'Pay or cancel the following orders to validate the session:\n%s',
                    ', '.join(draft_orders.mapped('name'))
            ))
        return True

    def _prepare_account_bank_statement_line_vals(self, session, sign, amount, reason, extras):
        return {
            'pos_session_id': session.id,
            'journal_id': session.cash_journal_id.id,
            'amount': sign * amount,
            'date': fields.Date.context_today(self),
            'payment_ref': '-'.join([session.name, extras['translatedType'], reason]),
        }

    def try_cash_in_out(self, _type, amount, reason, extras):
        sign = 1 if _type == 'in' else -1
        sessions = self.filtered('cash_journal_id')
        if not sessions:
            raise UserError(_("There is no cash payment method for this PoS Session"))

        vals_list = [
            self._prepare_account_bank_statement_line_vals(session, sign, amount, reason, extras)
            for session in sessions
        ]

        self.env['account.bank.statement.line'].create(vals_list)

    def _get_attributes_by_ptal_id(self):
        # performance trick: prefetch fields with search_fetch() and fetch()
        product_attributes = self.env['product.attribute'].search_fetch(
            [('create_variant', '=', 'no_variant')],
            ['name', 'display_type'],
        )
        product_template_attribute_values = self.env['product.template.attribute.value'].search_fetch(
            [('attribute_id', 'in', product_attributes.ids)],
            ['attribute_id', 'attribute_line_id', 'product_attribute_value_id', 'price_extra'],
        )
        product_template_attribute_values.product_attribute_value_id.fetch(['name', 'is_custom', 'html_color', 'image'])

        key1 = lambda ptav: (ptav.attribute_line_id.id, ptav.attribute_id.id)
        key2 = lambda ptav: (ptav.attribute_line_id.id, ptav.attribute_id)
        res = {}
        for key, group in groupby(sorted(product_template_attribute_values, key=key1), key=key2):
            attribute_line_id, attribute = key
            values = [{**ptav.product_attribute_value_id.read(['name', 'is_custom', 'html_color', 'image'])[0],
                       'price_extra': ptav.price_extra,
                       # id of a value should be from the "product.template.attribute.value" record
                       'id': ptav.id,
                       } for ptav in list(group)]
            res[attribute_line_id] = {
                'id': attribute_line_id,
                'name': attribute.name,
                'display_type': attribute.display_type,
                'values': values,
                'sequence': attribute.sequence,
            }

        return res

    def _get_pos_fallback_nomenclature_id(self):
        """
        Retrieve the fallback barcode nomenclature.
        If a fallback_nomenclature_id is specified in the config parameters,
        it retrieves the nomenclature with that ID. Otherwise, it retrieves
        the first non-GS1 nomenclature if the main nomenclature is GS1.
        """
        def convert_to_int(string_value):
            try:
                return int(string_value)
            except (TypeError, ValueError, OverflowError):
                return None

        fallback_nomenclature_id = self.env['ir.config_parameter'].sudo().get_param('point_of_sale.fallback_nomenclature_id')

        if not self.company_id.nomenclature_id.is_gs1_nomenclature and not fallback_nomenclature_id:
            return None

        if fallback_nomenclature_id:
            fallback_nomenclature_id = convert_to_int(fallback_nomenclature_id)
            if not fallback_nomenclature_id or self.company_id.nomenclature_id.id == fallback_nomenclature_id:
                return None
            domain = [('id', '=', fallback_nomenclature_id)]
        else:
            domain = [('is_gs1_nomenclature', '=', False)]

        record = self.env['barcode.nomenclature'].search(domain=domain, limit=1)

        return record.id if record else None

    def _get_partners_domain(self):
        return []

    def find_product_by_barcode(self, barcode, config_id):
        product_fields = self.env['product.product']._load_pos_data_fields(config_id)
        product_template_fields = self.env['product.template']._load_pos_data_fields(config_id)
        product_packaging_fields = self.env['product.packaging']._load_pos_data_fields(config_id)
        product_tmpl_attr_value_fields = self.env['product.template.attribute.value']._load_pos_data_fields(config_id)
        product_context = {**self.env.context, 'display_default_code': False}
        product = self.env['product.product'].search([
            ('barcode', '=', barcode),
            ('sale_ok', '=', True),
            ('available_in_pos', '=', True),
        ])
        if product:
            product = product.with_context(product_context)
            return {
                'product.product': product.read(product_fields, load=False),
                'product.template': product.product_tmpl_id.read(product_template_fields, load=False),
                'product.template.attribute.value': product.product_template_attribute_value_ids.read(product_tmpl_attr_value_fields, load=False)
            }

        domain = [('barcode', 'not in', ['', False])]
        loaded_data = self._context.get('loaded_data')
        if loaded_data:
            loaded_product_ids = [x['id'] for x in loaded_data['product.product']]
            domain = AND([domain, [('product_id', 'in', [x['id'] for x in self._context.get('loaded_data')['product.product']])]]) if self._context.get('loaded_data') else []
            domain = AND([domain, [('product_id', 'in', loaded_product_ids)]])
        packaging_params = {
            'search_params': {
                'domain': domain,
                'fields': ['name', 'barcode', 'product_id', 'qty'],
            },
        }
        packaging_params['search_params']['domain'] = [['barcode', '=', barcode]]
        packaging = self.env['product.packaging'].search(packaging_params['search_params']['domain'])
        product = packaging.product_id.with_context(product_context)
        condition = packaging and packaging.product_id
        return {
            'product.product': product.read(product_fields, load=False) if condition else [],
            'product.template.attribute.value': product.product_template_attribute_value_ids.read(product_tmpl_attr_value_fields, load=False) if condition else [],
            'product.template': product.product_tmpl_id.read(product_template_fields, load=False) if condition else [],
            'product.packaging': packaging.read(product_packaging_fields, load=False) if condition else [],
        }

    def get_total_discount(self):
        amount = 0
        for line in self.env['pos.order.line'].search([('order_id', 'in', self._get_closed_orders().ids), ('discount', '>', 0)]):
            amount += line._get_discount_amount()

        return amount

    def _get_invoice_total_list(self):
        invoice_list = []
        for order in self.order_ids.filtered(lambda o: o.is_invoiced):
            invoice = {
                'total': order.account_move.amount_total,
                'name': order.account_move.name,
                'order_ref': order.pos_reference,
            }
            invoice_list.append(invoice)

        return invoice_list

    def _get_total_invoice(self):
        amount = 0
        for order in self.order_ids.filtered(lambda o: o.is_invoiced):
            amount += order.amount_paid

        return amount

    def log_partner_message(self, partner_id, action, message_type):
        if message_type == 'ACTION_CANCELLED':
            body = 'Action cancelled ({ACTION})'.format(ACTION=action)
        elif message_type == 'CASH_DRAWER_ACTION':
            body = 'Cash drawer opened ({ACTION})'.format(ACTION=action)

        self.message_post(body=body, author_id=partner_id)

    def _pos_has_valid_product(self):
        return self.env['product.product'].sudo().search_count([('available_in_pos', '=', True), ('list_price', '>=', 0), ('id', 'not in', self.env['pos.config']._get_special_products().ids), '|', ('active', '=', False), ('active', '=', True)], limit=1) > 0

    def _get_closed_orders(self):
        return self.order_ids.filtered(lambda o: o.state not in ['draft', 'cancel'])


class ProcurementGroup(models.Model):
    _inherit = 'procurement.group'

    @api.model
    def _run_scheduler_tasks(self, use_new_cursor=False, company_id=False):
        super(ProcurementGroup, self)._run_scheduler_tasks(use_new_cursor=use_new_cursor, company_id=company_id)
        self.env['pos.session']._alert_old_session()
        if use_new_cursor:
            self.env.cr.commit()
