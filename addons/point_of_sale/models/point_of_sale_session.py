# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import time

from openerp import models, fields, api, _
from openerp.exceptions import UserError


class PosSession(models.Model):
    _name = 'pos.session'
    _order = 'id desc'

    POS_SESSION_STATE = [
        ('opening_control', 'Opening Control'),  # Signal open
        ('opened', 'In Progress'),                    # Signal closing
        ('closing_control', 'Closing Control'),  # Signal close
        ('closed', 'Closed & Posted'),
    ]

    config_id = fields.Many2one(
        'pos.config', string='Point of Sale',
        help="The physical point of sale you will use.",
        required=True,
        index=True,
        domain="[('state', '=', 'active')]")
    name = fields.Char(string='Session ID', required=True, readonly=True, default='/')
    user_id = fields.Many2one(
        'res.users', string='Responsible',
        required=True,
        index=True,
        readonly=True,
        states={'opening_control': [('readonly', False)]},
        default=lambda self: self.env.uid)
    currency_id = fields.Many2one('res.currency', related='config_id.currency_id', string="Currency")
    start_at = fields.Datetime(string='Opening Date', readonly=True)
    stop_at = fields.Datetime(string='Closing Date', readonly=True, copy=False)

    state = fields.Selection(
        POS_SESSION_STATE, string='Status',
        required=True, readonly=True,
        index=True, copy=False, default='opening_control')
    rescue = fields.Boolean(
        string='Rescue session', readonly=True,
        help="Auto-generated session for orphan orders, ignored in constraints")

    sequence_number = fields.Integer(string='Order Sequence Number', help='A sequence number that is incremented with each order', default=1)
    login_number = fields.Integer(string='Login Sequence Number', help='A sequence number that is incremented each time a user resumes the pos session', default=0)

    cash_control = fields.Boolean(compute='_compute_cash_all', string='Has Cash Control')
    cash_journal_id = fields.Many2one('account.journal', compute='_compute_cash_all', string='Cash Journal', store=True)
    cash_register_id = fields.Many2one('account.bank.statement', compute='_compute_cash_all', string='Cash Register', store=True)

    cash_register_balance_end_real = fields.Monetary(
        related='cash_register_id.balance_end_real',
        string="Ending Balance",
        help="Total of closing cash control lines.",
        readonly=True)
    cash_register_balance_start = fields.Monetary(
        related='cash_register_id.balance_start',
        string="Starting Balance",
        help="Total of opening cash control lines.",
        readonly=True)
    cash_register_total_entry_encoding = fields.Monetary(
        related='cash_register_id.total_entry_encoding',
        string='Total Cash Transaction',
        readonly=True,
        help="Total of all paid sale orders")
    cash_register_balance_end = fields.Monetary(
        related='cash_register_id.balance_end',
        digits=0,
        string="Theoretical Closing Balance",
        help="Sum of opening balance and transactions.",
        readonly=True)
    cash_register_difference = fields.Monetary(
        related='cash_register_id.difference',
        string='Difference',
        help="Difference between the theoretical closing balance and the real closing balance.",
        readonly=True)

    journal_ids = fields.Many2many(
        'account.journal',
        related='config_id.journal_ids',
        readonly=True,
        string='Available Payment Methods')
    order_ids = fields.One2many('pos.order', 'session_id',  string='Orders')
    statement_ids = fields.One2many('account.bank.statement', 'pos_session_id', string='Bank Statement', readonly=True)

    _sql_constraints = [
        ('uniq_name', 'unique(name)', _("The name of this POS Session must be unique !")),
    ]

    @api.multi
    @api.depends('cash_control', 'cash_journal_id', 'cash_register_id')
    def _compute_cash_all(self):
        for pos_session in self:
            pos_session.cash_journal_id = False
            pos_session.cash_register_id = False
            pos_session.cash_control = False

    @api.constrains('user_id', 'state')
    @api.one
    def _check_unicity(self):
        # open if there is no session in 'opening_control', 'opened', 'closing_control' for one user
        domain = [
            ('state', 'not in', ('closed', 'closing_control')),
            ('user_id', '=', self.user_id.id),
            ('rescue', '=', False)
        ]
        if self.search_count(domain) > 1:
            raise UserError(_("You cannot create two active sessions with the same responsible!"))

    @api.constrains('config_id')
    @api.one
    def _check_pos_config(self):
        domain = [
            ('state', '!=', 'closed'),
            ('config_id', '=', self.config_id.id),
            ('rescue', '=', False)
        ]
        if self.search_count(domain) > 1:
            raise UserError(_("You cannot create two active sessions related to the same point of sale!"))

    @api.model
    def create(self, values):
        config_id = values.get('config_id') or self.env.context.get('default_config_id')
        if not config_id:
            raise UserError(_("You should assign a Point of Sale to your session."))

        # journal_id is not required on the pos_config because it does not
        # exists at the installation. If nothing is configured at the
        # installation we do the minimal configuration. Impossible to do in
        # the .xml files as the CoA is not yet installed.
        Config = self.env['pos.config']
        pos_config = Config.browse(config_id)
        ctx = dict(self.env.context, company_id=pos_config.company_id.id)
        if not pos_config.journal_id:
            jid = Config.with_context(ctx).default_get(['journal_id'])['journal_id']
            if jid:
                pos_config.with_context(ctx).sudo().write({'journal_id': jid})
            else:
                raise UserError(_("Unable to open the session. You have to assign a sale journal to your point of sale."))

        # define some cash journal if no payment method exists

        if not pos_config.journal_ids:
            journal_proxy = self.env['account.journal']
            Journals = journal_proxy.with_context(ctx).search([('journal_user', '=', True), ('type', '=', 'cash')])
            if not Journals:
                Journals = journal_proxy.with_context(ctx).search([('type', '=', 'cash')])
                if not Journals:
                    Journals = journal_proxy.with_context(ctx).search([('journal_user', '=', True)])

            Journals.sudo().write({'journal_user': True})
            pos_config.sudo().write({'journal_ids': [(6, 0, Journals.ids)]})

        statements = [(0, 0, {
            'journal_id': journal.id,
            'user_id': self.env.uid,
            'company_id': pos_config.company_id.id
        }) for journal in pos_config.journal_ids]

        values.update({
            'name': self.env['ir.sequence'].next_by_code('pos.session'),
            'statement_ids': statements,
            'config_id': config_id
        })

        return super(PosSession, self.with_context(ctx)).create(values)

    @api.multi
    def unlink(self):
        for session in self:
            for statement in session.statement_ids:
                statement.unlink()
        return super(PosSession, self).unlink()

    @api.multi
    def open_cb(self):
        """
        call the Point Of Sale interface and set the pos.session to 'opened' (in progress)
        """
        self.ensure_one()
        self.signal_workflow('open')
        return {
            'type': 'ir.actions.act_url',
            'url': '/pos/web/',
            'target': 'self',
        }

    @api.multi
    def login(self):
        self.ensure_one()
        self.write({
            'login_number': self.login_number+1,
        })

    @api.multi
    def wkf_action_open(self):
        # second browse because we need to refetch the data from the DB for cash_register_id
        for session in self:
            values = {}
            if not session.start_at:
                values['start_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
            values['state'] = 'opened'
            session.write(values)
            for st in session.statement_ids:
                st.button_open()

        return self.open_frontend_cb()

    @api.multi
    def wkf_action_opening_control(self):
        return self.write({'state': 'opening_control'})

    @api.multi
    def wkf_action_closing_control(self):
        for session in self:
            for statement in session.statement_ids:
                if (statement != session.cash_register_id) and (statement.balance_end != statement.balance_end_real):
                    statement.write({'balance_end_real': statement.balance_end})
            session.write({'state': 'closing_control', 'stop_at': time.strftime('%Y-%m-%d %H:%M:%S')})

    @api.multi
    def wkf_action_close(self):
        # Close CashBox
        for session in self:
            company_id = session.config_id.company_id.id
            ctx = dict(self.env.context, force_company=company_id, company_id=company_id)
            for st in session.statement_ids:
                if abs(st.difference) > st.journal_id.amount_authorized_diff:
                    # The pos manager can close statements with maximums.
                    if not self.env['ir.model.access'].check_groups("point_of_sale.group_pos_manager"):
                        raise UserError(_("Your ending balance is too different from the theoretical cash closing (%.2f), the maximum allowed is: %.2f. You can contact your manager to force it.") % (st.difference, st.journal_id.amount_authorized_diff))
                if (st.journal_id.type not in ['bank', 'cash']):
                    raise UserError(_("The type of the journal for your payment method should be bank or cash "))
                st.with_context(ctx).sudo().button_confirm_bank()
        self.with_context(ctx)._confirm_orders()
        self.write({'state': 'closed'})
        menu_id = self.env.ref('point_of_sale.menu_point_root').id
        return {
            'type': 'ir.actions.client',
            'name': 'Point of Sale Menu',
            'tag': 'reload',
            'params': {'menu_id': menu_id},
        }

    @api.multi
    def _confirm_orders(self):
        PosOrder = self.env['pos.order']
        for session in self:
            company_id = session.config_id.journal_id.company_id.id
            local_context = dict(self.env.context, force_company=company_id)
            order_ids = session.order_ids.filtered(lambda order: order.state == 'paid')

            move_id = PosOrder.with_context(local_context)._create_account_move(session.start_at, session.name, session.config_id.journal_id.id, company_id)

            order_ids.with_context(local_context)._create_account_move_line(session, move_id)

            for order in session.order_ids:
                if order.state == 'done':
                    continue
                if order.state not in ('paid', 'invoiced'):
                    raise UserError(_("You cannot confirm all orders of this session, because they have not the 'paid' status"))
                else:
                    order.signal_workflow('done')
        return True

    @api.multi
    def open_frontend_cb(self):
        if not self.ids:
            return
        for session in self:
            if session.user_id.id != self.env.uid:
                raise UserError(_("You cannot use the session of another users. This session is owned by %s. "
                                    "Please first close this one to use this point of sale.") % session.user_id.name)
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url':   '/pos/web/',
        }
