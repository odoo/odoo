# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import timedelta
from itertools import groupby

from odoo import api, fields, models, _, Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import frozendict
from odoo.osv.expression import AND, OR
from odoo.service.common import exp_version
from odoo.tools.float_utils import float_compare


class PosSession(models.Model):
    _name = 'pos.session'
    _order = 'id desc'
    _description = 'Point of Sale Session'
    _inherit = ['mail.thread', 'mail.activity.mixin']

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
        readonly=True,
        states={'opening_control': [('readonly', False)]},
        default=lambda self: self.env.uid,
        ondelete='restrict')
    currency_id = fields.Many2one('res.currency', related='config_id.currency_id', string="Currency", readonly=False)
    start_at = fields.Datetime(string='Opening Date', readonly=True)
    stop_at = fields.Datetime(string='Closing Date', readonly=True, copy=False)

    state = fields.Selection(
        POS_SESSION_STATE, string='Status',
        required=True, readonly=True,
        index=True, copy=False, default='opening_control')

    sequence_number = fields.Integer(string='Order Sequence Number', help='A sequence number that is incremented with each order', default=1)
    login_number = fields.Integer(string='Login Sequence Number', help='A sequence number that is incremented each time a user resumes the pos session', default=0)

    opening_notes = fields.Text(string="Opening Notes")
    cash_control = fields.Boolean(compute='_compute_cash_all', string='Has Cash Control', compute_sudo=True)
    cash_journal_id = fields.Many2one('account.journal', compute='_compute_cash_all', string='Cash Journal', store=True)

    cash_register_balance_end_real = fields.Monetary(
        string="Ending Balance",
        readonly=True)
    cash_register_balance_start = fields.Monetary(
        string="Starting Balance",
        readonly=True)
    cash_register_total_entry_encoding = fields.Monetary(
        compute='_compute_cash_balance',
        string='Total Cash Transaction',
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

    _sql_constraints = [('uniq_name', 'unique(name)', "The name of this POS Session must be unique !")]

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
                last_session = session.search([('config_id', '=', session.config_id.id), ('id', '!=', session.id)], limit=1)
                result = self.env['pos.payment']._read_group([('session_id', '=', session.id), ('payment_method_id', '=', cash_payment_method.id)], ['amount'], ['session_id'])
                if result:
                    total_cash_payment = result[0]['amount']
                session.cash_register_total_entry_encoding = sum(session.statement_line_ids.mapped('amount')) + (
                    0.0 if session.state == 'closed' else total_cash_payment
                )
                session.cash_register_balance_end = last_session.cash_register_balance_end_real + session.cash_register_total_entry_encoding
                session.cash_register_difference = session.cash_register_balance_end_real - session.cash_register_balance_end
            else:
                session.cash_register_total_entry_encoding = 0.0
                session.cash_register_balance_end = 0.0
                session.cash_register_difference = 0.0

    @api.depends('order_ids.payment_ids.amount')
    def _compute_total_payments_amount(self):
        result = self.env['pos.payment']._read_group([('session_id', 'in', self.ids)], ['amount'], ['session_id'])
        session_amount_map = dict((data['session_id'][0], data['amount']) for data in result)
        for session in self:
            session.total_payments_amount = session_amount_map.get(session.id) or 0

    def _compute_order_count(self):
        orders_data = self.env['pos.order']._read_group([('session_id', 'in', self.ids)], ['session_id'], ['session_id'])
        sessions_data = {order_data['session_id'][0]: order_data['session_id_count'] for order_data in orders_data}
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
        action['context'] = {}
        action['domain'] = [('id', 'in', self.picking_ids.ids)]
        return action

    @api.depends('config_id', 'payment_method_ids')
    def _compute_cash_all(self):
        # Only one cash register is supported by point_of_sale.
        for session in self:
            session.cash_journal_id = session.cash_control = False
            cash_journal = session.payment_method_ids.filtered('is_cash_count')[:1].journal_id
            if not cash_journal:
                continue
            session.cash_control = session.config_id.cash_control
            session.cash_journal_id = cash_journal

    @api.constrains('config_id')
    def _check_pos_config(self):
        if self.search_count([
                ('state', '!=', 'closed'),
                ('config_id', '=', self.config_id.id),
                ('rescue', '=', False)
            ]) > 1:
            raise ValidationError(_("Another session is already opened for this point of sale."))

    @api.constrains('start_at')
    def _check_start_date(self):
        for record in self:
            company = record.config_id.journal_id.company_id
            start_date = record.start_at.date()
            if (company.period_lock_date and start_date <= company.period_lock_date) or (company.fiscalyear_lock_date and start_date <= company.fiscalyear_lock_date):
                raise ValidationError(_("You cannot create a session before the accounting lock date."))

    def _check_invoices_are_posted(self):
        unposted_invoices = self.order_ids.sudo().with_company(self.company_id).account_move.filtered(lambda x: x.state != 'posted')
        if unposted_invoices:
            raise UserError(_('You cannot close the POS when invoices are not posted.\n'
                              'Invoices: %s') % str.join('\n',
                                                         ['%s - %s' % (invoice.name, invoice.state) for invoice in
                                                          unposted_invoices]))

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
            ctx = dict(self.env.context, company_id=pos_config.company_id.id)

            pos_name = self.env['ir.sequence'].with_context(ctx).next_by_code('pos.session')
            if vals.get('name'):
                pos_name += ' ' + vals['name']

            update_stock_at_closing = pos_config.company_id.point_of_sale_update_stock_quantities == "closing"

            vals.update({
                'name': pos_name,
                'config_id': config_id,
                'update_stock_at_closing': update_stock_at_closing,
            })

        if self.user_has_groups('point_of_sale.group_pos_user'):
            sessions = super(PosSession, self.with_context(ctx).sudo()).create(vals_list)
        else:
            sessions = super(PosSession, self.with_context(ctx)).create(vals_list)
        sessions.action_pos_session_open()
        return sessions

    def unlink(self):
        self.statement_line_ids.unlink()
        return super(PosSession, self).unlink()

    def login(self):
        self.ensure_one()
        login_number = self.login_number + 1
        self.write({
            'login_number': login_number,
        })
        return login_number

    def action_pos_session_open(self):
        # we only open sessions that haven't already been opened
        for session in self.filtered(lambda session: session.state == 'opening_control'):
            values = {}
            if not session.start_at:
                values['start_at'] = fields.Datetime.now()
            if session.config_id.cash_control and not session.rescue:
                last_session = self.search([('config_id', '=', session.config_id.id), ('id', '!=', session.id)], limit=1)
                session.cash_register_balance_start = last_session.cash_register_balance_end_real  # defaults to 0 if lastsession is empty
            else:
                values['state'] = 'opened'
            session.write(values)
        return True

    def action_pos_session_closing_control(self, balancing_account=False, amount_to_balance=0, bank_payment_method_diffs=None):
        bank_payment_method_diffs = bank_payment_method_diffs or {}
        for session in self:
            if any(order.state == 'draft' for order in session.order_ids):
                raise UserError(_("You cannot close the POS when orders are still in draft"))
            if session.state == 'closed':
                raise UserError(_('This session is already closed.'))
            session.write({'state': 'closing_control', 'stop_at': fields.Datetime.now()})
            if not session.config_id.cash_control:
                return session.action_pos_session_close(balancing_account, amount_to_balance, bank_payment_method_diffs)
            # If the session is in rescue, we only compute the payments in the cash register
            # It is not yet possible to close a rescue session through the front end, see `close_session_from_ui`
            if session.rescue and session.config_id.cash_control:
                default_cash_payment_method_id = self.payment_method_ids.filtered(lambda pm: pm.type == 'cash')[0]
                orders = self.order_ids.filtered(lambda o: o.state == 'paid' or o.state == 'invoiced')
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
        self.ensure_one()
        if self.order_ids or self.statement_line_ids:
            self.cash_real_transaction = sum(self.statement_line_ids.mapped('amount'))
            if self.state == 'closed':
                raise UserError(_('This session is already closed.'))
            self._check_if_no_draft_orders()
            self._check_invoices_are_posted()
            if self.update_stock_at_closing:
                self._create_picking_at_end_of_session()
                self.order_ids.filtered(lambda o: not o.is_total_cost_computed)._compute_total_cost_at_session_closing(self.picking_ids.move_ids)

            cash_difference_before_statements = self.cash_register_difference
            self._post_statement_difference(cash_difference_before_statements)

            account_move = self.sudo()._create_closing_journal_entries()
            if account_move:
                self.write({'move_id': account_move.id})

            # Set the uninvoiced orders' state to 'done'
            self.env['pos.order']\
                .search([('session_id', '=', self.id), ('state', '=', 'paid')])\
                .write({'state': 'done'})
        else:
            self._post_statement_difference(self.cash_register_difference)

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

            if self.cash_register_difference < 0.0:
                if not self.cash_journal_id.loss_account_id:
                    raise UserError(
                        _('Please go on the %s journal and define a Loss Account. This account will be used to record cash difference.',
                          self.cash_journal_id.name))

                st_line_vals['payment_ref'] = _("Cash difference observed during the counting (Loss)")
                st_line_vals['counterpart_account_id'] = self.cash_journal_id.loss_account_id.id
            else:
                # self.cash_register_difference  > 0.0
                if not self.cash_journal_id.profit_account_id:
                    raise UserError(
                        _('Please go on the %s journal and define a Profit Account. This account will be used to record cash difference.',
                          self.cash_journal_id.name))

                st_line_vals['payment_ref'] = _("Cash difference observed during the counting (Profit)")
                st_line_vals['counterpart_account_id'] = self.cash_journal_id.profit_account_id.id

            self.env['account.bank.statement.line'].create(st_line_vals)

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
        check_closing_session = self._cannot_close_session(bank_payment_method_diffs)
        if check_closing_session:
            return check_closing_session

        validate_result = self.action_pos_session_closing_control(bank_payment_method_diffs=bank_payment_method_diffs)

        # If an error is raised, the user will still be redirected to the back end to manually close the session.
        # If the return result is a dict, this means that normally we have a redirection or a wizard => we redirect the user
        if isinstance(validate_result, dict):
            # imbalance accounting entry
            return {
                'successful': False,
                'message': validate_result.get('name'),
                'redirect': True
            }

        self.message_post(body='Point of Sale Session ended')

        return {'successful': True}

    def update_closing_control_state_session(self, notes):
        # Prevent the session to be opened again.
        self.write({'state': 'closing_control', 'stop_at': fields.Datetime.now()})
        self._post_cash_details_message('Closing', self.cash_register_difference, notes)

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
            return check_closing_session

        if not self.cash_journal_id:
            # The user is blocked anyway, this user error is mostly for developers that try to call this function
            raise UserError(_("There is no cash register in this session."))

        self.cash_register_balance_end_real = counted_cash

        return {'successful': True}

    def _get_diff_account_move_ref(self, payment_method):
        return _('Closing difference in %s (%s)', payment_method.name, self.name)

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
            return {'successful': False, 'message': _("This session is already closed."), 'redirect': True}
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
        self.ensure_one()
        orders = self.order_ids.filtered(lambda o: o.state == 'paid' or o.state == 'invoiced')
        payments = orders.payment_ids.filtered(lambda p: p.payment_method_id.type != "pay_later")
        pay_later_payments = orders.payment_ids - payments
        cash_payment_method_ids = self.payment_method_ids.filtered(lambda pm: pm.type == 'cash')
        default_cash_payment_method_id = cash_payment_method_ids[0] if cash_payment_method_ids else None
        total_default_cash_payment_amount = sum(payments.filtered(lambda p: p.payment_method_id == default_cash_payment_method_id).mapped('amount')) if default_cash_payment_method_id else 0
        other_payment_method_ids = self.payment_method_ids - default_cash_payment_method_id if default_cash_payment_method_id else self.payment_method_ids
        cash_in_count = 0
        cash_out_count = 0
        cash_in_out_list = []
        last_session = self.search([('config_id', '=', self.config_id.id), ('id', '!=', self.id)], limit=1)
        for cash_move in self.statement_line_ids.sorted('create_date'):
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
            'payments_amount': sum(payments.mapped('amount')),
            'pay_later_amount': sum(pay_later_payments.mapped('amount')),
            'opening_notes': self.opening_notes,
            'default_cash_details': {
                'name': default_cash_payment_method_id.name,
                'amount': last_session.cash_register_balance_end_real
                          + total_default_cash_payment_amount
                          + sum(self.statement_line_ids.mapped('amount')),
                'opening': last_session.cash_register_balance_end_real,
                'payment_amount': total_default_cash_payment_amount,
                'moves': cash_in_out_list,
                'id': default_cash_payment_method_id.id
            } if default_cash_payment_method_id else None,
            'other_payment_methods': [{
                'name': pm.name,
                'amount': sum(orders.payment_ids.filtered(lambda p: p.payment_method_id == pm).mapped('amount')),
                'number': len(orders.payment_ids.filtered(lambda p: p.payment_method_id == pm)),
                'id': pm.id,
                'type': pm.type,
            } for pm in other_payment_method_ids],
            'is_manager': self.user_has_groups("point_of_sale.group_pos_manager"),
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

        for order in self.order_ids:
            if order.company_id.anglo_saxon_accounting and order.is_invoiced or order.to_ship:
                continue
            destination_id = order.partner_id.property_stock_customer.id or session_destination_id
            if destination_id in lines_grouped_by_dest_location:
                lines_grouped_by_dest_location[destination_id] |= order.lines
            else:
                lines_grouped_by_dest_location[destination_id] = order.lines

        for location_dest_id, lines in lines_grouped_by_dest_location.items():
            pickings = self.env['stock.picking']._create_picking_from_pos_order_lines(location_dest_id, lines, picking_type)
            pickings.write({'pos_session_id': self.id, 'origin': self.name})

    def _get_balancing_account(self):
        propoerty_account = self.env['ir.property']._get('property_account_receivable_id', 'res.partner')
        return self.company_id.account_default_pos_receivable_account_id or propoerty_account or self.env['account.account']

    def _create_closing_journal_entries(self):
        """ Create account.move and account.move.line records for this session.

        Side-effects include:
            - setting self.move_id to the created account.move record
            - reconciling cash receivable lines, invoice receivable lines and stock output lines
        """
        self.ensure_one()

        orders = self.order_ids.filtered(lambda x: not x.is_invoiced)
        if not orders:
            return None

        res = orders._prepare_pos_order_accounting_items_generation()

        if not res['closing_entry_vals']:
            return None

        # Create the session journal entry.
        closing_move = self.env['account.move'].with_context(skip_invoice_sync=True).create(res['closing_entry_vals'])
        closing_move.action_post()

        # Create the bank journal entries.
        for payment_method, res_entry in res['closing_bank_entry_per_pay_method'].items():
            if not res_entry.get('bank_entry_vals'):
                continue

            bank_account_move = self.env['account.move']\
                .with_context(skip_invoice_sync=True)\
                .create(res_entry['bank_entry_vals'])
            bank_account_move.action_post()

            # Link the pos payments to the newly created journal entry.
            res_entry['pos_payments'].write({'account_move_id': bank_account_move.id})

            # Reconcile.
            (closing_move + bank_account_move).line_ids\
                .filtered(lambda x: x.pos_payment_method_id == payment_method)\
                .reconcile()

        # Create the cash statement lines.
        pos_payments = self.env['pos.payment']
        st_lines_vals_list = []
        for pos_payment, st_line_vals in res['closing_st_line_vals_list']:
            pos_payments |= pos_payment
            st_lines_vals_list.append(st_line_vals)

        if st_lines_vals_list:
            st_lines = self.env['account.bank.statement.line']\
                .with_context(skip_invoice_sync=True)\
                .create(st_lines_vals_list)

            for pos_payment, st_line in zip(pos_payments, st_lines):
                # Link the pos payments to the newly created statement lines.
                pos_payment.statement_line_id = st_line

                # Reconcile.
                st_line_amls = st_line.move_id.line_ids\
                    .filtered(lambda x: x.account_id.account_type == 'asset_receivable')
                pos_entry_amls = closing_move.line_ids\
                    .filtered(lambda x: x.pos_payment_method_id == pos_payment.payment_method_id and not x.reconciled)
                (st_line_amls + pos_entry_amls).reconcile()

        # Reconcile stock output lines
        pickings = self.picking_ids.filtered(lambda p: not p.pos_order_id)
        pickings |= self.order_ids.filtered(lambda o: not o.is_invoiced).picking_ids
        if pickings:
            stock_moves = self.env['stock.move'].search([('picking_id', 'in', pickings.ids)])
            stock_output_accounts = stock_moves.product_id.categ_id\
                .with_company(self.company_id)\
                .property_stock_account_output_categ_id
            stock_account_move_lines = self.env['account.move']\
                .search([('stock_move_id', 'in', stock_moves.ids)])\
                .line_ids
            for account in stock_output_accounts:
                stock_output_amls = stock_account_move_lines\
                    .filtered(lambda x: x.account_id == account and not x.reconciled)
                pos_entry_amls = closing_move.line_ids\
                    .filtered(lambda x: x.account_id == account and not x.reconciled)
                (stock_output_amls + pos_entry_amls).reconcile()

        return closing_move

    def _prepare_closing_journal_entry(self, amls_per_nature, open_amount_currency, open_balance):
        self.ensure_one()

        # Get journal items from orders.
        pos_entry_amls = self._aggregate_journal_items_values_list(amls_per_nature['product'])
        for aml in pos_entry_amls:
            if aml['tax_ids'] and aml['tax_ids'][0] and aml['tax_ids'][0][2]:
                tax_ids = aml['tax_ids'][0][2]
                tax_names = self.env['account.tax'].browse(tax_ids).mapped('name')
                aml['name'] = _("Sales with %s", ", ".join(tax_names))
            else:
                aml['name'] = _("Sales")

        pos_entry_amls += self._aggregate_journal_items_values_list(amls_per_nature['tax'])
        pos_entry_amls += self._aggregate_journal_items_values_list(amls_per_nature['cash_rounding'])
        stock_amls = self._aggregate_journal_items_values_list(amls_per_nature['stock'])
        for aml in stock_amls:
            if float_compare(aml['balance'], 0, 3) == 1:
                aml['name'] = _("Stock input")
            else:
                aml['name'] = _("Stock output")
        pos_entry_amls += stock_amls

        pos_entry_amls += self._aggregate_journal_items_values_list(amls_per_nature['payment'], fields_to_aggregate={
            'name': lambda vals: _("Total %s payments", self.env['pos.payment.method'].browse(vals['pos_payment_method_id']).name),
            'pos_payment_method_id': True,
        })

        if not self.currency_id.is_zero(open_amount_currency) \
            or not self.company_id.currency_id.is_zero(open_balance):
            pos_entry_amls.append({
                'name': _("Closing difference"),
                'currency_id': self.currency_id.id,
                'account_id': self.company_id.account_default_pos_receivable_account_id.id,
                'amount_currency': open_amount_currency,
                'balance': open_balance,
            })

        return {
            'journal_id': self.config_id.journal_id.id,
            'date': fields.Date.context_today(self),
            'ref': self.name,
            'line_ids': [
                Command.create(self._convert_to_closing_journal_item(pos_entry_aml))
                for pos_entry_aml in pos_entry_amls
            ],
        }

    def _prepare_closing_bank_journal_entry(self, payment_method, amls_values_list):
        """ Prepare the values to create the journal entry corresponding of the 'bank' payment method passed as
        parameter.

        :param payment_method:      A pos.payment record.
        :param amls_values_list:    A list of dictionaries corresponding to the journal items to create.
        :return:                    A dictionary to create a new account.move.
        """
        self.ensure_one()

        # Keep the details of each transaction according to the 'split_transactions' setting.
        if not payment_method.split_transactions:
            amls_values_list = self._aggregate_journal_items_values_list(
                amls_values_list,
                fields_to_aggregate={'name': lambda vals: _("Total %s payments from %s", payment_method.name, self.name)},
            )

        return {
            'journal_id': payment_method.journal_id.id,
            'date': fields.Date.context_today(self),
            'ref': self.name,
            'line_ids': [
                Command.create(self._convert_to_closing_journal_item(x))
                for x in amls_values_list
            ],
        }

    def _prepare_reverse_closing_bank_journal_entry(self, payment_method, amls_values_list):
        """ Prepare the values to create the journal entry reversing the journal entry created by the
        '_prepare_closing_bank_journal_entry' method.

        :param payment_method:      A pos.payment record.
        :param amls_values_list:    A list of dictionaries corresponding to the journal items to create.
        :return:                    A dictionary to create a new account.move.
        """
        self.ensure_one()

        # Keep the details of each transaction according to the 'split_transactions' setting.
        if not payment_method.split_transactions:
            amls_values_list = self._aggregate_journal_items_values_list(
                amls_values_list,
                fields_to_aggregate={'name': lambda vals: _("Total %s payments from %s", payment_method.name, self.name)},
            )

        return {
            'journal_id': payment_method.journal_id.id,
            'date': fields.Date.context_today(self),
            'ref': self.name,
            'line_ids': [
                Command.create(self._convert_to_closing_journal_item(x))
                for x in amls_values_list
            ],
        }

    @api.model
    def _aggregate_journal_items_values_list(self, aml_values_list, fields_to_aggregate=None):
        """ Aggregate the list of dictionaries passed as parameter to reduce the number of journal items to be created.

        :param aml_values_list:     A list of dictionaries representing some journal items.
        :param fields_to_aggregate: The extra fields on which the journal items should be aggregated as a dictionary
                                    mapping the field to aggregate to a boolean or a lambda for a specific aggregation.
                                    By default, those journal items are already aggregated on partner/account/tax
                                    information.
        :return:                    The list of dictionaries after the aggregation.
        """
        aggregation = defaultdict(list)

        fields_to_aggregate = fields_to_aggregate or {}
        fields_to_aggregate.update({
            'partner_id': True,
            'account_id': True,
            'group_tax_id': True,
            'tax_repartition_line_id': True,
            'tax_ids': True,
        })

        # Batch lines.
        for aml_values in aml_values_list:
            grouping_dict = {
                field: aml_values.get(field)
                for field, value in fields_to_aggregate.items()
                if value is True
            }
            grouping_dict['sign'] = 1 if aml_values['amount_currency'] >= 0.0 else -1
            grouping_key = frozendict(grouping_dict)
            aggregation[grouping_key].append(aml_values)

        # Squash lines, one for each aggregation dict.
        new_aml_values_list = []
        for aggr_aml_values_list in aggregation.values():
            new_aml_values = dict(
                aggr_aml_values_list[0],
                amount_currency=sum(x['amount_currency'] for x in aggr_aml_values_list),
                balance=sum(x['balance'] for x in aggr_aml_values_list),
            )

            for field, method in fields_to_aggregate.items():
                if callable(method):
                    new_aml_values[field] = method(new_aml_values)

            new_aml_values_list.append(new_aml_values)
        return new_aml_values_list

    @api.model
    def _convert_to_closing_journal_item(self, values):
        """ Convert the python dictionary passed as parameter to a dictionary to be passed to account.move.line.create.

        :param values:  A dictionary corresponding to a journal item plus some custom values.
        :return:        The dictionary containing always the valid fields on account.move.line minus 'display_type'.
        """
        return {
            k: v for k, v in values.items()
            if k in self.env['account.move.line']._fields and k != 'display_type'
        }

    def show_cash_register(self):
        return {
            'name': _('Cash register'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.bank.statement.line',
            'view_mode': 'tree',
            'domain': [('id', 'in', self.statement_line_ids.ids)],
        }

    def show_journal_items(self):
        self.ensure_one()
        all_related_moves = self._get_related_account_moves()
        return {
            'name': _('Journal Items'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'tree',
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
        return self.env['account.move.line'].search([('ref', 'in', diff_lines_ref)]).mapped('move_id')

    def _get_related_account_moves(self):
        pickings = self.picking_ids | self.order_ids.mapped('picking_ids')
        invoices = self.mapped('order_ids.account_move')
        invoice_payments = self.mapped('order_ids.payment_ids.account_move_id')
        stock_account_moves = pickings.mapped('move_ids.account_move_ids')
        cash_moves = self.statement_line_ids.mapped('move_id')
        bank_payment_moves = self.bank_payment_ids.mapped('move_id')
        other_related_moves = self._get_other_related_moves()
        return invoices | invoice_payments | self.move_id | stock_account_moves | cash_moves | bank_payment_moves | other_related_moves

    def action_show_payments_list(self):
        return {
            'name': _('Payments'),
            'type': 'ir.actions.act_window',
            'res_model': 'pos.payment',
            'view_mode': 'tree,form',
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

    def set_cashbox_pos(self, cashbox_value, notes):
        self.state = 'opened'
        self.opening_notes = notes
        difference = cashbox_value - self.cash_register_balance_start
        self.cash_register_balance_start = cashbox_value
        self._post_statement_difference(difference)
        self._post_cash_details_message('Opening', difference, notes)

    def _post_cash_details_message(self, state, difference, notes):
        message = ""
        if difference:
            message = f"{state} difference: " \
                      f"{self.currency_id.symbol + ' ' if self.currency_id.position == 'before' else ''}" \
                      f"{self.currency_id.round(difference)} " \
                      f"{self.currency_id.symbol if self.currency_id.position == 'after' else ''}<br/>"
        if notes:
            message += notes.replace('\n', '<br/>')
        if message:
            self.message_post(body=message)

    def action_view_order(self):
        return {
            'name': _('Orders'),
            'res_model': 'pos.order',
            'view_mode': 'tree,form',
            'views': [
                (self.env.ref('point_of_sale.view_pos_order_tree_no_session_id').id, 'tree'),
                (self.env.ref('point_of_sale.view_pos_pos_form').id, 'form'),
                ],
            'type': 'ir.actions.act_window',
            'domain': [('session_id', 'in', self.ids)],
        }

    @api.model
    def _alert_old_session(self):
        # If the session is open for more then one week,
        # log a next activity to close the session.
        sessions = self.sudo().search([('start_at', '<=', (fields.datetime.now() - timedelta(days=7))), ('state', '!=', 'closed')])
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
                    'Pay or cancel the following orders to validate the session:\n%s'
                ) % ', '.join(draft_orders.mapped('name'))
            )
        return True

    def try_cash_in_out(self, _type, amount, reason, extras):
        sign = 1 if _type == 'in' else -1
        sessions = self.filtered('cash_journal_id')
        if not sessions:
            raise UserError(_("There is no cash payment method for this PoS Session"))

        self.env['account.bank.statement.line'].create([
            {
                'pos_session_id': session.id,
                'journal_id': session.cash_journal_id.id,
                'amount': sign * amount,
                'date': fields.Date.context_today(self),
                'payment_ref': '-'.join([session.name, extras['translatedType'], reason]),
            }
            for session in sessions
        ])

        message_content = [f"Cash {extras['translatedType']}", f'- Amount: {extras["formattedAmount"]}']
        if reason:
            message_content.append(f'- Reason: {reason}')
        self.message_post(body='<br/>\n'.join(message_content))

    def get_onboarding_data(self):
        return {
            "categories": self._load_model('pos.category'),
            "products": self._load_model('product.product'),
        }

    def _load_model(self, model):
        model_name = model.replace('.', '_')
        loader = getattr(self, '_get_pos_ui_%s' % model_name, None)
        params = getattr(self, '_loader_params_%s' % model_name, None)
        if loader and params:
            return loader(params())
        else:
            raise NotImplementedError(_("The function to load %s has not been implemented.", model))

    def load_pos_data(self):
        loaded_data = {}
        self = self.with_context(loaded_data=loaded_data)
        for model in self._pos_ui_models_to_load():
            loaded_data[model] = self._load_model(model)
        self._pos_data_process(loaded_data)
        return loaded_data

    def _get_attributes_by_ptal_id(self):
        product_attributes = self.env['product.attribute'].search([('create_variant', '=', 'no_variant')])
        product_attributes_by_id = {product_attribute.id: product_attribute for product_attribute in product_attributes}
        domain = [('attribute_id', 'in', product_attributes.mapped('id'))]
        product_template_attribute_values = self.env['product.template.attribute.value'].search(domain)
        key = lambda ptav: (ptav.attribute_line_id.id, ptav.attribute_id.id)
        res = {}
        for key, group in groupby(sorted(product_template_attribute_values, key=key), key=key):
            attribute_line_id, attribute_id = key
            values = [{**ptav.product_attribute_value_id.read(['name', 'is_custom', 'html_color'])[0],
                       'price_extra': ptav.price_extra} for ptav in list(group)]
            res[attribute_line_id] = {
                'id': attribute_line_id,
                'name': product_attributes_by_id[attribute_id].name,
                'display_type': product_attributes_by_id[attribute_id].display_type,
                'values': values
            }

        return res

    def _pos_data_process(self, loaded_data):
        """
        This is where we need to process the data if we can't do it in the loader/getter
        """
        loaded_data['version'] = exp_version()

        loaded_data['units_by_id'] = {unit['id']: unit for unit in loaded_data['uom.uom']}

        loaded_data['taxes_by_id'] = {tax['id']: tax for tax in loaded_data['account.tax']}
        for tax in loaded_data['taxes_by_id'].values():
            tax['children_tax_ids'] = [loaded_data['taxes_by_id'][id] for id in tax['children_tax_ids']]

        for pricelist in loaded_data['product.pricelist']:
            if pricelist['id'] == self.config_id.pricelist_id.id:
                loaded_data['default_pricelist'] = pricelist
                break

        fiscal_position_by_id = {fpt['id']: fpt for fpt in self._get_pos_ui_account_fiscal_position_tax(
            self._loader_params_account_fiscal_position_tax())}
        for fiscal_position in loaded_data['account.fiscal.position']:
            fiscal_position['fiscal_position_taxes_by_id'] = {tax_id: fiscal_position_by_id[tax_id] for tax_id in fiscal_position['tax_ids']}

        loaded_data['attributes_by_ptal_id'] = self._get_attributes_by_ptal_id()
        loaded_data['base_url'] = self.get_base_url()

    @api.model
    def _pos_ui_models_to_load(self):
        models_to_load = [
            'res.company',
            'decimal.precision',
            'uom.uom',
            'res.country.state',
            'res.country',
            'res.lang',
            'account.tax',
            'pos.session',
            'pos.config',
            'pos.bill',
            'res.partner',
            'stock.picking.type',
            'res.users',
            'product.pricelist',
            'res.currency',
            'pos.category',
            'product.product',
            'product.packaging',
            'account.cash.rounding',
            'pos.payment.method',
            'account.fiscal.position',
        ]

        return models_to_load

    def _loader_params_res_company(self):
        return {
            'search_params': {
                'domain': [('id', '=', self.company_id.id)],
                'fields': [
                    'currency_id', 'email', 'website', 'company_registry', 'vat', 'name', 'phone', 'partner_id',
                    'country_id', 'state_id', 'tax_calculation_rounding_method', 'nomenclature_id', 'point_of_sale_use_ticket_qr_code',
                ],
            }
        }

    def _get_pos_ui_res_company(self, params):
        company = self.env['res.company'].search_read(**params['search_params'])[0]
        params_country = self._loader_params_res_country()
        if company['country_id']:
            # TODO: this is redundant we have country_id and country
            params_country['search_params']['domain'] = [('id', '=', company['country_id'][0])]
            company['country'] = self.env['res.country'].search_read(**params_country['search_params'])[0]
        else:
            company['country'] = None

        return company

    def _loader_params_decimal_precision(self):
        return {'search_params': {'domain': [], 'fields': ['name', 'digits']}}

    def _get_pos_ui_decimal_precision(self, params):
        decimal_precisions = self.env['decimal.precision'].search_read(**params['search_params'])
        return {dp['name']: dp['digits'] for dp in decimal_precisions}

    def _loader_params_uom_uom(self):
        return {'search_params': {'domain': [], 'fields': []}, 'context': {'active_test': False}}

    def _get_pos_ui_uom_uom(self, params):
        return self.env['uom.uom'].with_context(**params['context']).search_read(**params['search_params'])

    def _loader_params_res_country_state(self):
        return {'search_params': {'domain': [], 'fields': ['name', 'country_id']}}

    def _get_pos_ui_res_country_state(self, params):
        return self.env['res.country.state'].search_read(**params['search_params'])

    def _loader_params_res_country(self):
        return {'search_params': {'domain': [], 'fields': ['name', 'vat_label', 'code']}}

    def _get_pos_ui_res_country(self, params):
        return self.env['res.country'].search_read(**params['search_params'])

    def _loader_params_res_lang(self):
        return {'search_params': {'domain': [], 'fields': ['name', 'code']}}

    def _get_pos_ui_res_lang(self, params):
        return self.env['res.lang'].search_read(**params['search_params'])

    def _loader_params_account_tax(self):
        return {
            'search_params': {
                'domain': [('company_id', '=', self.company_id.id)],
                'fields': [
                    'name', 'price_include', 'include_base_amount', 'is_base_affected',
                    'amount_type', 'children_tax_ids', 'amount', 'id'
                ],
            },
        }

    def _get_pos_ui_account_tax(self, params):
        taxes = self.env['account.tax'].search_read(**params['search_params'])

        # Add the 'sum_repartition_factor' as needed in the compute_all
        # Note that the factor = factor_percent/100
        tax_ids = tuple([t['id'] for t in taxes])
        self.env.cr.execute("""
            SELECT invoice_tax_id AS tax_id, sum(factor_percent)/100 AS factor_sum
            FROM account_tax_repartition_line 
            WHERE invoice_tax_id IN %s AND repartition_type = 'tax' 
            GROUP BY invoice_tax_id
        """, [tax_ids])
        res = self.env.cr.dictfetchall()
        tax_id_to_factor_sum = {d['tax_id']: d['factor_sum'] for d in res}
        for tax in taxes:
            tax['sum_repartition_factor'] = tax_id_to_factor_sum[tax['id']]

        return taxes

    def _loader_params_pos_session(self):
        return {
            'search_params': {
                'domain': [('id', '=', self.id)],
                'fields': [
                    'id', 'name', 'user_id', 'config_id', 'start_at', 'stop_at', 'sequence_number',
                    'payment_method_ids', 'state', 'update_stock_at_closing', 'cash_register_balance_start'
                ],
            },
        }

    def _get_pos_ui_pos_session(self, params):
        return self.env['pos.session'].search_read(**params['search_params'])[0]

    def _loader_params_pos_config(self):
        return {'search_params': {'domain': [('id', '=', self.config_id.id)], 'fields': []}}

    def _get_pos_ui_pos_config(self, params):
        config = self.env['pos.config'].search_read(**params['search_params'])[0]
        config['use_proxy'] = config['is_posbox'] and (config['iface_electronic_scale'] or config['iface_print_via_proxy']
                                                       or config['iface_scan_via_proxy'] or config['iface_customer_facing_display_via_proxy'])
        return config

    def _loader_params_pos_bill(self):
        return {'search_params': {'domain': [('id', 'in', self.config_id.default_bill_ids.ids)], 'fields': ['name', 'value']}}

    def _get_pos_ui_pos_bill(self, params):
        return self.env['pos.bill'].search_read(**params['search_params'])

    def _loader_params_res_partner(self):
        return {
            'search_params': {
                'domain': [],
                'fields': [
                    'name', 'street', 'city', 'state_id', 'country_id', 'vat', 'lang', 'phone', 'zip', 'mobile', 'email',
                    'barcode', 'write_date', 'property_account_position_id', 'property_product_pricelist', 'parent_name'
                ],
            },
        }

    def _get_pos_ui_res_partner(self, params):
        if not self.config_id.limited_partners_loading:
            return self.env['res.partner'].search_read(**params['search_params'])
        partner_ids = [res[0] for res in self.config_id.get_limited_partners_loading()]
        # Need to search_read because get_limited_partners_loading
        # might return a partner id that is not accessible.
        params['search_params']['domain'] = [('id', 'in', partner_ids)]
        return self.env['res.partner'].search_read(**params['search_params'])

    def _loader_params_stock_picking_type(self):
        return {
            'search_params': {
                'domain': [('id', '=', self.config_id.picking_type_id.id)],
                'fields': ['use_create_lots', 'use_existing_lots'],
            },
        }

    def _get_pos_ui_stock_picking_type(self, params):
        return self.env['stock.picking.type'].search_read(**params['search_params'])[0]

    def _loader_params_res_users(self):
        return {
            'search_params': {
                'domain': [('id', '=', self.env.user.id)],
                'fields': ['name', 'groups_id'],
            },
        }

    def _get_pos_ui_res_users(self, params):
        user = self.env['res.users'].search_read(**params['search_params'])[0]
        user['role'] = 'manager' if any(id == self.config_id.group_pos_manager_id.id for id in user['groups_id']) else 'cashier'
        del user['groups_id']
        return user

    def _loader_params_product_pricelist(self):
        if self.config_id.use_pricelist:
            domain = [('id', 'in', self.config_id.available_pricelist_ids.ids)]
        else:
            domain = [('id', '=', self.config_id.pricelist_id.id)]
        return {'search_params': {'domain': domain, 'fields': ['name', 'display_name', 'discount_policy']}}

    def _product_pricelist_item_fields(self):
        return [
                'id',
                'product_tmpl_id',
                'product_id',
                'pricelist_id',
                'price_surcharge',
                'price_discount',
                'price_round',
                'price_min_margin',
                'price_max_margin',
                'company_id',
                'currency_id',
                'date_start',
                'date_end',
                'compute_price',
                'fixed_price',
                'percent_price',
                'base_pricelist_id',
                'base',
                'categ_id',
                'min_quantity',
                ]

    def _get_pos_ui_product_pricelist(self, params):
        pricelists = self.env['product.pricelist'].search_read(**params['search_params'])
        for pricelist in pricelists:
            pricelist['items'] = []

        pricelist_by_id = {pricelist['id']: pricelist for pricelist in pricelists}
        pricelist_item_domain = [('pricelist_id', 'in', [p['id'] for p in pricelists])]
        for item in self.env['product.pricelist.item'].search_read(pricelist_item_domain, self._product_pricelist_item_fields()):
            pricelist_by_id[item['pricelist_id'][0]]['items'].append(item)

        return pricelists

    def _loader_params_product_category(self):
        return {'search_params': {'domain': [], 'fields': ['name', 'parent_id']}}

    def _get_pos_ui_product_category(self, params):
        categories = self.env['product.category'].search_read(**params['search_params'])
        category_by_id = {category['id']: category for category in categories}
        for category in categories:
            category['parent'] = category_by_id[category['parent_id'][0]] if category['parent_id'] else None
        return categories

    def _loader_params_res_currency(self):
        return {
            'search_params': {
                'domain': [('id', '=', self.config_id.currency_id.id)],
                'fields': ['name', 'symbol', 'position', 'rounding', 'rate', 'decimal_places'],
            },
        }

    def _get_pos_ui_res_currency(self, params):
        return self.env['res.currency'].search_read(**params['search_params'])[0]

    def _loader_params_pos_category(self):
        domain = []
        if self.config_id.limit_categories and self.config_id.iface_available_categ_ids:
            domain = [('id', 'in', self.config_id.iface_available_categ_ids.ids)]

        return {'search_params': {'domain': domain, 'fields': ['id', 'name', 'parent_id', 'child_id', 'write_date', 'has_image']}}

    def _get_pos_ui_pos_category(self, params):
        return self.env['pos.category'].search_read(**params['search_params'])

    def _loader_params_product_product(self):
        domain = [
            '&', '&', ('sale_ok', '=', True), ('available_in_pos', '=', True), '|',
            ('company_id', '=', self.config_id.company_id.id), ('company_id', '=', False)
        ]
        if self.config_id.limit_categories and self.config_id.iface_available_categ_ids:
            domain = AND([domain, [('pos_categ_id', 'in', self.config_id.iface_available_categ_ids.ids)]])
        if self.config_id.iface_tipproduct:
            domain = OR([domain, [('id', '=', self.config_id.tip_product_id.id)]])

        return {
            'search_params': {
                'domain': domain,
                'fields': [
                    'display_name', 'lst_price', 'standard_price', 'categ_id', 'pos_categ_id', 'taxes_id', 'barcode',
                    'default_code', 'to_weight', 'uom_id', 'description_sale', 'description', 'product_tmpl_id', 'tracking',
                    'write_date', 'available_in_pos', 'attribute_line_ids', 'active'
                ],
                'order': 'sequence,default_code,name',
            },
            'context': {'display_default_code': False},
        }

    def _process_pos_ui_product_product(self, products):
        """
        Modify the list of products to add the categories as well as adapt the lst_price
        :param products: a list of products
        """
        if self.config_id.currency_id != self.company_id.currency_id:
            for product in products:
                product['lst_price'] = self.company_id.currency_id._convert(product['lst_price'], self.config_id.currency_id,
                                                                            self.company_id, fields.Date.today())
        categories = self._get_pos_ui_product_category(self._loader_params_product_category())
        product_category_by_id = {category['id']: category for category in categories}
        for product in products:
            product['categ'] = product_category_by_id[product['categ_id'][0]]

    def _get_pos_ui_product_product(self, params):
        self = self.with_context(**params['context'])
        if not self.config_id.limited_products_loading:
            products = self.env['product.product'].search_read(**params['search_params'])
        else:
            products = self.config_id.get_limited_products_loading(params['search_params']['fields'])

        self._process_pos_ui_product_product(products)
        return products

    def _loader_params_product_packaging(self):
        return {
            'search_params': {
                'domain': [('barcode', 'not in', ['', False])],
                'fields': ['name', 'barcode', 'product_id', 'qty'],
            },
        }

    def _get_pos_ui_product_packaging(self, params):
        return self.env['product.packaging'].search_read(**params['search_params'])

    def _loader_params_account_cash_rounding(self):
        return {
            'search_params': {
                'domain': [('id', '=', self.config_id.rounding_method.id)],
                'fields': ['name', 'rounding', 'rounding_method'],
            },
        }

    def _get_pos_ui_account_cash_rounding(self, params):
        return self.env['account.cash.rounding'].search_read(**params['search_params'])

    def _loader_params_pos_payment_method(self):
        return {
            'search_params': {
                'domain': ['|', ('active', '=', False), ('active', '=', True)],
                'fields': ['name', 'is_cash_count', 'use_payment_terminal', 'split_transactions', 'type'],
                'order': 'is_cash_count desc, id',
            },
        }

    def _get_pos_ui_pos_payment_method(self, params):
        return self.env['pos.payment.method'].search_read(**params['search_params'])

    def _loader_params_account_fiscal_position(self):
        return {'search_params': {'domain': [('id', 'in', self.config_id.fiscal_position_ids.ids)], 'fields': []}}

    def _get_pos_ui_account_fiscal_position(self, params):
        return self.env['account.fiscal.position'].search_read(**params['search_params'])

    def _loader_params_account_fiscal_position_tax(self):
        loaded_data = self._context.get('loaded_data')
        fps = loaded_data['account.fiscal.position']
        fiscal_position_tax_ids = sum([fpos['tax_ids'] for fpos in fps], [])
        return {'search_params': {'domain': [('id', 'in', fiscal_position_tax_ids)], 'fields': []}}

    def _get_pos_ui_account_fiscal_position_tax(self, params):
        return self.env['account.fiscal.position.tax'].search_read(**params['search_params'])

    def get_pos_ui_product_product_by_params(self, custom_search_params):
        """
        :param custom_search_params: a dictionary containing params of a search_read()
        """
        params = self._loader_params_product_product()
        # custom_search_params will take priority
        params['search_params'] = {**params['search_params'], **custom_search_params}
        products = self.env['product.product'].with_context(active_test=False).search_read(**params['search_params'])
        if len(products) > 0:
            self._process_pos_ui_product_product(products)
        return products

    def get_pos_ui_res_partner_by_params(self, custom_search_params):
        """
        :param custom_search_params: a dictionary containing params of a search_read()
        """
        params = self._loader_params_res_partner()
        # custom_search_params will take priority
        params['search_params'] = {**params['search_params'], **custom_search_params}
        partners = self.env['res.partner'].search_read(**params['search_params'])
        return partners


class ProcurementGroup(models.Model):
    _inherit = 'procurement.group'

    @api.model
    def _run_scheduler_tasks(self, use_new_cursor=False, company_id=False):
        super(ProcurementGroup, self)._run_scheduler_tasks(use_new_cursor=use_new_cursor, company_id=company_id)
        self.env['pos.session']._alert_old_session()
        if use_new_cursor:
            self.env.cr.commit()
