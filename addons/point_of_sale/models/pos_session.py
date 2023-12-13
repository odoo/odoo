# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import secrets
from collections import defaultdict
from datetime import timedelta
from itertools import groupby
from markupsafe import Markup, escape

from odoo import api, fields, models, _, Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import float_is_zero, float_compare, convert
from odoo.service.common import exp_version
from odoo.osv.expression import AND


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
    access_token = fields.Char('Security Token', copy=False)
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

    sequence_number = fields.Integer(string='Order Sequence Number', help='A sequence number that is incremented with each order', default=1)
    login_number = fields.Integer(string='Login Sequence Number', help='A sequence number that is incremented each time a user resumes the pos session', default=0)

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

    _sql_constraints = [('uniq_name', 'unique(name)', "The name of this POS Session must be unique!")]

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
                last_session = session.search([('config_id', '=', session.config_id.id), ('id', '<', session.id)], limit=1)
                result = self.env['pos.payment']._read_group([('session_id', '=', session.id), ('payment_method_id', '=', cash_payment_method.id)], aggregates=['amount:sum'])
                total_cash_payment = result[0][0] or 0.0
                if session.state == 'closed':
                    session.cash_register_total_entry_encoding = session.cash_real_transaction + total_cash_payment
                else:
                    session.cash_register_total_entry_encoding = sum(session.statement_line_ids.mapped('amount')) + total_cash_payment

                session.cash_register_balance_end = last_session.cash_register_balance_end_real + session.cash_register_total_entry_encoding
                session.cash_register_difference = session.cash_register_balance_end_real - session.cash_register_balance_end
            else:
                session.cash_register_total_entry_encoding = 0.0
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
            company = record.config_id.journal_id.company_id
            start_date = record.start_at.date()
            if (company.period_lock_date and start_date <= company.period_lock_date) or (start_date <= company._get_user_fiscal_lock_date()):
                raise ValidationError(_("You cannot create a session before the accounting lock date."))

    def _check_invoices_are_posted(self):
        unposted_invoices = self._get_closed_orders().sudo().with_company(self.company_id).account_move.filtered(lambda x: x.state != 'posted')
        if unposted_invoices:
            raise UserError(_(
                'You cannot close the POS when invoices are not posted.\nInvoices: %s',
                '\n'.join(f'{invoice.name} - {invoice.state}' for invoice in unposted_invoices)
            ))

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

        if self.user_has_groups('point_of_sale.group_pos_user'):
            sessions = super(PosSession, self.sudo()).create(vals_list)
        else:
            sessions = super().create(vals_list)
        sessions.action_pos_session_open()

        date_string = fields.Date.today().isoformat()
        ir_sequence = self.env['ir.sequence'].sudo().search([('code', '=', f'pos.order_{date_string}')])
        if not ir_sequence:
            self.env['ir.sequence'].sudo().create({
                'name': _("PoS Order"),
                'padding': 0,
                'code': f'pos.order_{date_string}',
                'number_next': 1,
                'number_increment': 1,
                'company_id': self.env.company.id,
            })

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
        sudo = self.user_has_groups('point_of_sale.group_pos_user')
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

            self.sudo()._post_statement_difference(cash_difference_before_statements, False)
            if self.move_id.line_ids:
                self.move_id.sudo().with_company(self.company_id)._post()
                #We need to write the price_subtotal and price_total here because if we do it earlier the compute functions will overwrite it here /account/models/account_move_line.py _compute_totals
                for dummy, amount_data in data['sales'].items():
                    self.env['account.move.line'].browse(amount_data['move_line_id']).sudo().with_company(self.company_id).write({
                        'price_subtotal': abs(amount_data['amount_converted']),
                        'price_total': abs(amount_data['amount_converted']) + abs(amount_data['tax_amount']),
                    })
                # Set the uninvoiced orders' state to 'done'
                self.env['pos.order'].search([('session_id', '=', self.id), ('state', '=', 'paid')]).write({'state': 'done'})
            else:
                self.move_id.sudo().unlink()
            self.sudo().with_company(self.company_id)._reconcile_account_move_lines(data)
        else:
            self.sudo()._post_statement_difference(self.cash_register_difference, False)

        self.write({'state': 'closed'})
        return True

    def _post_statement_difference(self, amount, is_opening):
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

                st_line_vals['payment_ref'] = _("Cash difference observed during the counting (Loss)") + (_(' - opening') if is_opening else _(' - closing'))
                if not is_opening:
                    st_line_vals['counterpart_account_id'] = self.cash_journal_id.loss_account_id.id
            else:
                # self.cash_register_difference  > 0.0
                if not self.cash_journal_id.profit_account_id:
                    raise UserError(
                        _('Please go on the %s journal and define a Profit Account. This account will be used to record cash difference.',
                          self.cash_journal_id.name))

                st_line_vals['payment_ref'] = _("Cash difference observed during the counting (Profit)") + (_(' - opening') if is_opening else _(' - closing'))
                if not is_opening:
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
        # Prevent closing the session again if it was already closed
        if self.state == 'closed':
            raise UserError(_('This session is already closed.'))
        # Prevent the session to be opened again.
        self.write({'state': 'closing_control', 'stop_at': fields.Datetime.now(), 'closing_notes': notes})
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
        return _('Closing difference in %s (%s)', payment_method.name, self.name)

    def _get_diff_vals(self, payment_method_id, diff_amount):
        payment_method = self.env['pos.payment.method'].browse(payment_method_id)
        diff_compare_to_zero = self.currency_id.compare_amounts(diff_amount, 0)
        source_account = payment_method.outstanding_account_id or self.company_id.account_journal_payment_debit_account_id
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
        total_default_cash_payment_amount = sum(payments.filtered(lambda p: p.payment_method_id == default_cash_payment_method_id).mapped('amount')) if default_cash_payment_method_id else 0
        other_payment_method_ids = self.payment_method_ids - default_cash_payment_method_id if default_cash_payment_method_id else self.payment_method_ids
        cash_in_count = 0
        cash_out_count = 0
        cash_in_out_list = []
        last_session = self.search([('config_id', '=', self.config_id.id), ('id', '!=', self.id)], limit=1)
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
                'amount': last_session.cash_register_balance_end_real
                          + total_default_cash_payment_amount
                          + sum(self.sudo().statement_line_ids.mapped('amount')),
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
        if (not float_is_zero(amount_to_balance, precision_rounding=self.currency_id.rounding)):
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
        propoerty_account = self.env['ir.property']._get('property_account_receivable_id', 'res.partner')
        return self.company_id.account_default_pos_receivable_account_id or propoerty_account or self.env['account.account']

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
        rounded_globally = self.company_id.tax_calculation_rounding_method == 'round_globally'
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
                order_taxes = defaultdict(tax_amounts)
                for order_line in order.lines:
                    line = self._prepare_line(order_line)
                    # Combine sales/refund lines
                    sale_key = (
                        # account
                        line['income_account_id'],
                        # sign
                        -1 if line['amount'] < 0 else 1,
                        # for taxes
                        tuple((tax['id'], tax['account_id'], tax['tax_repartition_line_id']) for tax in line['taxes']),
                        line['base_tags'],
                    )
                    sales[sale_key] = self._update_amounts(sales[sale_key], {'amount': line['amount']}, line['date_order'], round=False)
                    sales[sale_key].setdefault('tax_amount', 0.0)
                    # Combine tax lines
                    for tax in line['taxes']:
                        tax_key = (tax['account_id'] or line['income_account_id'], tax['tax_repartition_line_id'], tax['id'], tuple(tax['tag_ids']))
                        sales[sale_key]['tax_amount'] += tax['amount']
                        order_taxes[tax_key] = self._update_amounts(
                            order_taxes[tax_key],
                            {'amount': tax['amount'], 'base_amount': tax['base']},
                            tax['date_order'],
                            round=not rounded_globally
                        )
                for tax_key, amounts in order_taxes.items():
                    if rounded_globally:
                        amounts = self._round_amounts(amounts)
                    for amount_key, amount in amounts.items():
                        taxes[tax_key][amount_key] += amount

                if self.company_id.anglo_saxon_accounting and order.picking_ids.ids:
                    # Combine stock lines
                    stock_moves = self.env['stock.move'].sudo().search([
                        ('picking_id', 'in', order.picking_ids.ids),
                        ('company_id.anglo_saxon_accounting', '=', True),
                        ('product_id.categ_id.property_valuation', '=', 'real_time')
                    ])
                    for move in stock_moves:
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

                if self.config_id.cash_rounding:
                    diff = order.amount_paid - order.amount_total
                    rounding_difference = self._update_amounts(rounding_difference, {'amount': diff}, order.date_order)

                # Increasing current partner's customer_rank
                partners = (order.partner_id | order.partner_id.commercial_partner_id)
                partners._increase_rank('customer_rank')

        if self.company_id.anglo_saxon_accounting:
            global_session_pickings = self.picking_ids.filtered(lambda p: not p.pos_order_id)
            if global_session_pickings:
                stock_moves = self.env['stock.move'].sudo().search([
                    ('picking_id', 'in', global_session_pickings.ids),
                    ('company_id.anglo_saxon_accounting', '=', True),
                    ('product_id.categ_id.property_valuation', '=', 'real_time'),
                ])
                for move in stock_moves:
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
        move_line_ids = MoveLine.create([self._get_sale_vals(key, amounts['amount'], amounts['amount_converted']) for key, amounts in sales.items()])
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
        outstanding_account = payment_method.outstanding_account_id or self.company_id.account_journal_payment_debit_account_id
        destination_account = self._get_receivable_account(payment_method)

        if float_compare(amounts['amount'], 0, precision_rounding=self.currency_id.rounding) < 0:
            # revert the accounts because account.payment doesn't accept negative amount.
            outstanding_account, destination_account = destination_account, outstanding_account

        account_payment = self.env['account.payment'].create({
            'amount': abs(amounts['amount']),
            'journal_id': payment_method.journal_id.id,
            'force_outstanding_account_id': outstanding_account.id,
            'destination_account_id':  destination_account.id,
            'ref': _('Combine %s POS payments from %s', payment_method.name, self.name),
            'pos_payment_method_id': payment_method.id,
            'pos_session_id': self.id,
        })

        diff_amount_compare_to_zero = self.currency_id.compare_amounts(diff_amount, 0)
        if diff_amount_compare_to_zero != 0:
            self._apply_diff_on_account_payment_move(account_payment, payment_method, diff_amount)

        account_payment.action_post()
        return account_payment.move_id.line_ids.filtered(lambda line: line.account_id == account_payment.destination_account_id)

    def _apply_diff_on_account_payment_move(self, account_payment, payment_method, diff_amount):
        source_vals, dest_vals = self._get_diff_vals(payment_method.id, diff_amount)
        outstanding_line = account_payment.move_id.line_ids.filtered(lambda line: line.account_id.id == source_vals['account_id'])
        new_balance = outstanding_line.balance + diff_amount
        new_balance_compare_to_zero = self.currency_id.compare_amounts(new_balance, 0)
        account_payment.move_id.write({
            'line_ids': [
                Command.create(dest_vals),
                Command.update(outstanding_line.id, {
                    'debit': new_balance_compare_to_zero > 0 and new_balance or 0.0,
                    'credit': new_balance_compare_to_zero < 0 and -new_balance or 0.0
                })
            ]
        })

    def _create_split_account_payment(self, payment, amounts):
        payment_method = payment.payment_method_id
        if not payment_method.journal_id:
            return self.env['account.move.line']
        outstanding_account = payment_method.outstanding_account_id or self.company_id.account_journal_payment_debit_account_id
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
            'ref': _('%s POS payment of %s in %s', payment_method.name, payment.partner_id.display_name, self.name),
            'pos_payment_method_id': payment_method.id,
            'pos_session_id': self.id,
        })
        account_payment.action_post()
        return account_payment.move_id.line_ids.filtered(lambda line: line.account_id == account_payment.destination_account_id)

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

    def _prepare_line(self, order_line):
        """ Derive from order_line the order date, income account, amount and taxes information.

        These information will be used in accumulating the amounts for sales and tax lines.
        """
        def get_income_account(order_line):
            product = order_line.product_id
            income_account = product.with_company(order_line.company_id)._get_product_accounts()['income'] or self.config_id.journal_id.default_account_id
            if not income_account:
                raise UserError(_('Please define income account for this product: "%s" (id:%d).',
                                  product.name, product.id))
            return order_line.order_id.fiscal_position_id.map_account(income_account)

        company_domain = self.env['account.tax']._check_company_domain(order_line.order_id.company_id)
        tax_ids = order_line.tax_ids_after_fiscal_position.filtered_domain(company_domain)
        sign = -1 if order_line.qty >= 0 else 1
        price = sign * order_line.price_unit * (1 - (order_line.discount or 0.0) / 100.0)
        # The 'is_refund' parameter is used to compute the tax tags. Ultimately, the tags are part
        # of the key used for summing taxes. Since the POS UI doesn't support the tags, inconsistencies
        # may arise in 'Round Globally'.
        check_refund = lambda x: x.qty * x.price_unit < 0
        is_refund = check_refund(order_line)
        tax_data = tax_ids.compute_all(price_unit=price, quantity=abs(order_line.qty), currency=self.currency_id, is_refund=is_refund, fixed_multiplicator=sign)
        taxes = tax_data['taxes']
        # For Cash based taxes, use the account from the repartition line immediately as it has been paid already
        for tax in taxes:
            tax_rep = self.env['account.tax.repartition.line'].browse(tax['tax_repartition_line_id'])
            tax['account_id'] = tax_rep.account_id.id
        date_order = order_line.order_id.date_order
        taxes = [{'date_order': date_order, **tax} for tax in taxes]
        return {
            'date_order': order_line.order_id.date_order,
            'income_account_id': get_income_account(order_line).id,
            'amount': order_line.price_subtotal,
            'taxes': taxes,
            'base_tags': tuple(tax_data['base_tags']),
        }

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
            raise UserError(_("You have enabled the \"Identify Customer\" option for %s payment method,"
                              "but the order %s does not contain a customer.",
                              payment.payment_method_id.name,
                              payment.pos_order_id.name))
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
            'name': '%s - %s' % (self.name, payment_method.name)
        }
        return self._debit_amounts(partial_vals, amount, amount_converted)

    def _get_invoice_receivable_vals(self, amount, amount_converted):
        partial_vals = {
            'account_id': self.company_id.account_default_pos_receivable_account_id.id,
            'move_id': self.move_id.id,
            'name': _('From invoice payments'),
        }
        return self._credit_amounts(partial_vals, amount, amount_converted)

    def _get_sale_vals(self, key, amount, amount_converted):
        account_id, sign, tax_keys, base_tag_ids = key
        tax_ids = set(tax[0] for tax in tax_keys)
        applied_taxes = self.env['account.tax'].browse(tax_ids)
        title = 'Sales' if sign == 1 else 'Refund'
        name = '%s untaxed' % title
        if applied_taxes:
            name = '%s with %s' % (title, ', '.join([tax.name for tax in applied_taxes]))
        partial_vals = {
            'name': name,
            'account_id': account_id,
            'move_id': self.move_id.id,
            'tax_ids': [(6, 0, tax_ids)],
            'tax_tag_ids': [(6, 0, base_tag_ids)],
        }
        return self._credit_amounts(partial_vals, amount, amount_converted)

    def _get_tax_vals(self, key, amount, amount_converted, base_amount_converted):
        account_id, repartition_line_id, tax_id, tag_ids = key
        tax = self.env['account.tax'].browse(tax_id)
        partial_args = {
            'name': tax.name,
            'account_id': account_id,
            'move_id': self.move_id.id,
            'tax_base_amount': abs(base_amount_converted),
            'tax_repartition_line_id': repartition_line_id,
            'tax_tag_ids': [(6, 0, tag_ids)],
        }
        return self._debit_amounts(partial_args, amount, amount_converted)

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
            'view_mode': 'tree,kanban',
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

    def set_cashbox_pos(self, cashbox_value: int, notes: str):
        self.state = 'opened'
        self.opening_notes = notes
        difference = cashbox_value - self.cash_register_balance_start
        self.cash_register_balance_start = cashbox_value
        self.sudo()._post_statement_difference(difference, True)
        self._post_cash_details_message('Opening', difference, notes)

    def _post_cash_details_message(self, state, difference, notes):
        message = ""
        if difference:
            message = f"{state} difference: " \
                      f"{self.currency_id.symbol + ' ' if self.currency_id.position == 'before' else ''}" \
                      f"{self.currency_id.round(difference)} " \
                      f"{self.currency_id.symbol if self.currency_id.position == 'after' else ''}" + Markup('<br/>')
        if notes:
            message += escape(notes).replace('\n', Markup('<br/>'))
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
                    'Pay or cancel the following orders to validate the session:\n%s',
                    ', '.join(draft_orders.mapped('name'))
            ))
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

    def get_onboarding_data(self):
        return {
            'pos.category': self._load_model('pos.category'),
            'product.product': self._load_model('product.product'),
            'pos.order': self.env['pos.order'].search([('session_id', '=', self.id), ('state', '=', 'draft')]).export_for_ui()
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

    def _pos_data_process(self, loaded_data):
        """
        This is where we need to process the data if we can't do it in the loader/getter
        """
        loaded_data['version'] = exp_version()

        loaded_data['units_by_id'] = {unit['id']: unit for unit in loaded_data['uom.uom']}

        loaded_data['taxes_by_id'] = {tax['id']: tax for tax in loaded_data['account.tax']}
        for tax in loaded_data['taxes_by_id'].values():
            tax['children_tax_ids'] = [loaded_data['taxes_by_id'][id] for id in tax['children_tax_ids']]

        if self.config_id.use_pricelist:
            default_pricelist = next(
                (pl for pl in loaded_data['product.pricelist'] if pl['id'] == self.config_id.pricelist_id.id),
                False
            )
            if default_pricelist:
                loaded_data['default_pricelist'] = default_pricelist

        fiscal_position_by_id = {fpt['id']: fpt for fpt in self._get_pos_ui_account_fiscal_position_tax(
            self._loader_params_account_fiscal_position_tax())}
        for fiscal_position in loaded_data['account.fiscal.position']:
            fiscal_position['fiscal_position_taxes_by_id'] = {tax_id: fiscal_position_by_id[tax_id] for tax_id in fiscal_position['tax_ids']}

        loaded_data['attributes_by_ptal_id'] = self._get_attributes_by_ptal_id()
        loaded_data['base_url'] = self.get_base_url()
        loaded_data['pos_has_valid_product'] = self._pos_has_valid_product()
        loaded_data['pos_special_products_ids'] = self.env['pos.config']._get_special_products().ids
        loaded_data['open_orders'] = self.env['pos.order'].search([('session_id', '=', self.id), ('state', '=', 'draft')]).export_for_ui()
        loaded_data['partner_commercial_fields'] = self.env['res.partner']._commercial_fields()

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
            'pos.printer',
            'pos.bill',
            'res.partner',
            'stock.picking.type',
            'res.users',
            'product.product',
            'product.pricelist',
            'res.currency',
            'pos.category',
            'pos.combo',
            'pos.combo.line',
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
                    'point_of_sale_ticket_unique_code',
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
                'domain': self.env['account.tax']._check_company_domain(self.company_id),
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
        groups = self.env['account.tax.repartition.line']._read_group(
            domain=[
                ('tax_id', 'in', tuple([t['id'] for t in taxes])),
                ('document_type', '=', 'invoice'),
                ('repartition_type', '=', 'tax'),
            ],
            groupby=["tax_id"],
            aggregates=["factor_percent:sum"],
        )
        tax_id_to_factor_sum = {tax.id: factor_sum / 100 for tax, factor_sum in groups}
        for tax in filter(lambda t: t['amount_type'] != 'group', taxes):
            tax['sum_repartition_factor'] = tax_id_to_factor_sum.get(tax['id'], 0)

        return taxes

    def _ensure_access_token(self):
        # Code taken from addons/portal/models/portal_mixin.py
        if not self.access_token:
            self.sudo().write({'access_token': secrets.token_hex(16)})
        return self.access_token

    def _get_bus_channel_name(self):
        return f'pos_session-{self.id}-{self._ensure_access_token()}'

    def _loader_params_pos_session(self):
        self._ensure_access_token()
        return {
            'search_params': {
                'domain': [('id', '=', self.id)],
                'fields': [
                    'id', 'name', 'user_id', 'config_id', 'start_at', 'stop_at', 'sequence_number',
                    'payment_method_ids', 'state', 'update_stock_at_closing', 'cash_register_balance_start', 'access_token'
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
        config['has_cash_move_permission'] = self.user_has_groups('account.group_account_invoice')
        return config

    def _loader_params_pos_bill(self):
        return {'search_params': {'domain': ['|', ('id', 'in', self.config_id.default_bill_ids.ids), ('pos_config_ids', '=', False)], 'fields': ['name', 'value']}}

    def _get_pos_ui_pos_bill(self, params):
        return self.env['pos.bill'].search_read(**params['search_params'])

    def _get_partners_domain(self):
        return []

    def _loader_params_res_partner(self):
        return {
            'search_params': {
                'domain': self._get_partners_domain(),
                'fields': [
                    'name', 'street', 'city', 'state_id', 'country_id', 'vat', 'lang', 'phone', 'zip', 'mobile', 'email',
                    'barcode', 'write_date', 'property_account_position_id', 'property_product_pricelist', 'parent_name'
                ],
            },
        }

    def _get_pos_ui_res_partner(self, params):
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
                'fields': ['name', 'groups_id', 'partner_id'],
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

    def _product_pricelist_item_domain_by_product(self, product_tmpl_ids, product_ids, pricelists):
        return [
            ('pricelist_id', 'in', [p['id'] for p in pricelists]),
            '|', ('product_tmpl_id', '=', False), ('product_tmpl_id', 'in', product_tmpl_ids),
            '|', ('product_id', '=', False), ('product_id', 'in', product_ids),
        ]

    def _get_pos_ui_product_pricelist(self, params):
        pricelists = self.env['product.pricelist'].search_read(**params['search_params'])
        for pricelist in pricelists:
            pricelist['items'] = []

        return self._prepare_product_pricelists(pricelists)

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

    def _get_pos_ui_pos_printer(self, params):
        return self.env['pos.printer'].search_read(**params['search_params'])

    def _loader_params_pos_printer(self):
        return {
            'search_params': {
                'domain': [('id', 'in', self.config_id.printer_ids.ids)],
                'fields': ['name', 'proxy_ip', 'product_categories_ids', 'printer_type'],
            },
        }

    def _loader_params_pos_category(self):
        domain = []
        if self.config_id.limit_categories and self.config_id.iface_available_categ_ids:
            domain = [('id', 'in', self.config_id.iface_available_categ_ids.ids)]
        return {'search_params': {'domain': domain, 'fields': ['id', 'name', 'parent_id', 'child_id', 'write_date', 'has_image']}}

    def _get_pos_ui_pos_category(self, params):
        return self.env['pos.category'].search_read(**params['search_params'])

    def _loader_params_pos_combo(self):
        products = self._context.get('loaded_data')['product.product']
        combo_ids = set().union(*[product.get('combo_ids') for product in products])
        return {'search_params': {'fields': ['id', 'name', 'combo_line_ids', 'base_price']}, 'ids': combo_ids}

    def _get_pos_ui_pos_combo(self, params):
        return self.env['pos.combo'].browse(params['ids']).read(**params['search_params'])

    def _loader_params_pos_combo_line(self):
        combo_ids = self._context.get('loaded_data')['pos.combo']
        combo_line_ids = set().union(*[combo.get('combo_line_ids') for combo in combo_ids])
        return {'search_params': {'fields': ['id', 'product_id', 'combo_price', 'combo_id']}, 'ids': combo_line_ids}

    def _get_pos_ui_pos_combo_line(self, params):
        return self.env['pos.combo.line'].browse(params['ids']).read(**params['search_params'])

    def _loader_params_product_product(self):
        return {
            'search_params': {
                'domain': self.config_id._get_available_product_domain(),
                'fields': [
                    'display_name', 'lst_price', 'standard_price', 'categ_id', 'pos_categ_ids', 'taxes_id', 'barcode',
                    'default_code', 'to_weight', 'uom_id', 'description_sale', 'description', 'product_tmpl_id', 'tracking',
                    'write_date', 'available_in_pos', 'attribute_line_ids', 'active', 'image_128', 'combo_ids',
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
            product['image_128'] = bool(product['image_128'])

    def _get_pos_ui_product_product(self, params):
        self = self.with_context(**params['context'])
        products = self.config_id.get_limited_products_loading(params['search_params']['fields'])

        self._process_pos_ui_product_product(products)
        return products

    def _loader_params_product_packaging(self):
        domain = [('barcode', 'not in', ['', False])]
        loaded_data = self._context.get('loaded_data')
        if loaded_data:
            loaded_product_ids = [x['id'] for x in loaded_data['product.product']]
            domain = AND([domain, [('product_id', 'in', loaded_product_ids)]])

        return {
            'search_params': {
                'domain': domain,
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
                'fields': ['name', 'is_cash_count', 'use_payment_terminal', 'split_transactions', 'type', 'image', 'sequence'],
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
        self = self.with_context(**params['context'])
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

    def find_product_by_barcode(self, barcode):
        product = self.env['product.product'].search([
            ('barcode', '=', barcode),
            ('sale_ok', '=', True),
            ('available_in_pos', '=', True),
        ])
        if product:
            return {'product_id': [product.id]}

        packaging_params = self._loader_params_product_packaging()
        packaging_params['search_params']['domain'] = [['barcode', '=', barcode]]
        packaging = self.env['product.packaging'].search_read(**packaging_params['search_params'])
        if packaging:
            product_id = packaging[0]['product_id']
            if product_id:
                return {'product_id': [product_id[0]], 'packaging': packaging}
        return {}

    def get_total_discount(self):
        amount = 0
        for line in self.env['pos.order.line'].search([('order_id', 'in', self._get_closed_orders().ids), ('discount', '>', 0)]):
            original_price = line.tax_ids.compute_all(line.price_unit, line.currency_id, line.qty, product=line.product_id, partner=line.order_id.partner_id)['total_included']
            amount += original_price - line.price_subtotal_incl

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

    def get_pos_ui_product_pricelists_by_ids(self, pricelist_ids):
        params = self._loader_params_product_pricelist()
        params['search_params']['domain'] = [('id', 'in', pricelist_ids)]
        pricelists = self.env['product.pricelist'].search_read(**params['search_params'])
        for pricelist in pricelists:
            if not self.config_id.use_pricelist:
                self.config_id.use_pricelist = True
            pricelist_id = self.env['product.pricelist'].browse(pricelist['id'])
            self.config_id.available_pricelist_ids += pricelist_id
            pricelist['items'] = []

        return self._prepare_product_pricelists(pricelists)

    def _prepare_product_pricelists(self, pricelists):
        pricelist_by_id = {pricelist['id']: pricelist for pricelist in pricelists}
        pricelist_item_domain = [('pricelist_id', 'in', [p['id'] for p in pricelists])]

        loaded_data = self._context.get('loaded_data')
        if loaded_data:
            pricelist_item_domain = self._product_pricelist_item_domain_by_product(
                [p['product_tmpl_id'][0] for p in loaded_data['product.product']],
                [p['id'] for p in loaded_data['product.product']],
                pricelists)

        for item in self.env['product.pricelist.item'].search_read(pricelist_item_domain, self._product_pricelist_item_fields()):
            pricelist_by_id[item['pricelist_id'][0]]['items'].append(item)

        return pricelists

    def get_pos_ui_account_fiscal_positions_by_ids(self, fp_ids):
        params = self._loader_params_account_fiscal_position()
        params['search_params']['domain'] = [('id', 'in', fp_ids)]
        fps = self.env['account.fiscal.position'].search_read(**params['search_params'])
        fiscal_position_tax_ids = sum([fpos['tax_ids'] for fpos in fps], [])
        fiscal_position_tax = self.env['account.fiscal.position.tax'].search_read([('id', 'in', fiscal_position_tax_ids)])
        fiscal_position_by_id = {fpt['id']: fpt for fpt in fiscal_position_tax}
        for fiscal_position in fps:
            if not self.config_id.tax_regime_selection:
                self.config_id.tax_regime_selection = True
            fiscal_position_id = self.env['account.fiscal.position'].browse(fiscal_position['id'])
            self.config_id.fiscal_position_ids += fiscal_position_id
            fiscal_position['fiscal_position_taxes_by_id'] = {tax_id: fiscal_position_by_id[tax_id] for tax_id in fiscal_position['tax_ids']}

        return fps

    def log_partner_message(self, partner_id, action, message_type):
        if message_type == 'ACTION_CANCELLED':
            body = 'Action cancelled ({ACTION})'.format(ACTION=action)
        elif message_type == 'CASH_DRAWER_ACTION':
            body = 'Cash drawer opened ({ACTION})'.format(ACTION=action)

        self.message_post(body=body, author_id=partner_id)

    def _pos_has_valid_product(self):
        return self.env['product.product'].sudo().search_count([('available_in_pos', '=', True), ('list_price', '>=', 0), ('id', 'not in', self.env['pos.config']._get_special_products().ids), '|', ('active', '=', False), ('active', '=', True)], limit=1) > 0

    @api.model
    def _load_onboarding_data(self):
        convert.convert_file(self.env, 'point_of_sale', 'data/point_of_sale_onboarding.xml', None, mode='init', kind='data')
        shop_config = self.env.ref('point_of_sale.pos_config_main', raise_if_not_found=False)
        if shop_config and shop_config.active:
            convert.convert_file(self.env, 'point_of_sale', 'data/point_of_sale_onboarding_main_config.xml', None, mode='init', kind='data')
            if len(shop_config.session_ids.filtered(lambda s: s.state == 'opened')) == 0:
                self.env['pos.session'].create({
                    'config_id': shop_config.id,
                    'user_id': self.env.ref('base.user_admin').id,
                })

    def _after_load_onboarding_data(self):
        config = self.env.ref('point_of_sale.pos_config_main', raise_if_not_found=False)
        if config:
            config.with_context(bypass_categories_forbidden_change=True).write({
                'limit_categories': True,
                'iface_available_categ_ids': [Command.link(self.env.ref('point_of_sale.pos_category_miscellaneous').id), Command.link(self.env.ref('point_of_sale.pos_category_desks').id), Command.link(self.env.ref('point_of_sale.pos_category_chairs').id)]
            })

    def load_product_frontend(self):
        allowed = not self._pos_has_valid_product()
        if allowed:
            self.sudo()._load_onboarding_data()
            self._after_load_onboarding_data()

        return {
            'models_data': self.get_onboarding_data(),
            'successful': allowed,
        }

    def _get_closed_orders(self):
        return self.order_ids.filtered(lambda o: o.state not in ['draft', 'cancel'])

    def get_pos_ui_product_pricelist_item_by_product(self, product_tmpl_ids, product_ids):
        pricelists = self.env['product.pricelist'].search_read(**self._loader_params_product_pricelist()['search_params'])
        pricelist_item_domain = [
            ('pricelist_id', 'in', [p['id'] for p in pricelists]),
            '|',
            '&', ('product_id', '=', False), ('product_tmpl_id', 'in', product_tmpl_ids),
            ('product_id', 'in', product_ids)]
        return self.env['product.pricelist.item'].search_read(pricelist_item_domain, self._product_pricelist_item_fields())


class ProcurementGroup(models.Model):
    _inherit = 'procurement.group'

    @api.model
    def _run_scheduler_tasks(self, use_new_cursor=False, company_id=False):
        super(ProcurementGroup, self)._run_scheduler_tasks(use_new_cursor=use_new_cursor, company_id=company_id)
        self.env['pos.session']._alert_old_session()
        if use_new_cursor:
            self.env.cr.commit()
