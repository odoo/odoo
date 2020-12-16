from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PosPaymentMethod(models.Model):
    """ Used to classify pos.payment.

    Generic characteristics of a pos.payment is described in this model.
    E.g. A cash payment can be described by a pos.payment.method with
    fields: is_cash_count = True and a cash_journal_id set to an
    `account.journal` (type='cash') record.

    When a pos.payment.method is cash, cash_journal_id is required as
    it will be the journal where the account.bank.statement.line records
    will be created.
    """

    _name = "pos.payment.method"
    _description = "Point of Sale Payment Methods"
    _order = "id asc"

    def _get_payment_terminal_selection(self):
        return []

    name = fields.Char(string="Payment Method", required=True, translate=True)
    receivable_account_id = fields.Many2one('account.account',
        string='Intermediary Account',
        required=True,
        domain=[('reconcile', '=', True), ('user_type_id.type', '=', 'receivable')],
        default=lambda self: self.env.company.account_default_pos_receivable_account_id,
        ondelete='restrict',
        help='Account used as counterpart of the income account in the accounting entry representing the pos sales.')
    is_cash_count = fields.Boolean(string='Cash')
    cash_journal_id = fields.Many2one('account.journal',
        string='Cash Journal',
        domain=[('type', '=', 'cash')],
        ondelete='restrict',
        help='The payment method is of type cash. A cash statement will be automatically generated.')
    split_transactions = fields.Boolean(
        string='Split Transactions',
        default=False,
        help='If ticked, each payment will generate a separated journal item. Ticking that option will slow the closing of the PoS.')
    open_session_ids = fields.Many2many('pos.session', string='Pos Sessions', compute='_compute_open_session_ids', help='Open PoS sessions that are using this payment method.')
    config_ids = fields.Many2many('pos.config', string='Point of Sale Configurations')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    use_payment_terminal = fields.Selection(selection=lambda self: self._get_payment_terminal_selection(), string='Use a Payment Terminal', help='Record payments with a terminal on this journal.')
    hide_use_payment_terminal = fields.Boolean(compute='_compute_hide_use_payment_terminal', help='Technical field which is used to '
                                               'hide use_payment_terminal when no payment interfaces are installed.')
    active = fields.Boolean(default=True)

    @api.depends('is_cash_count')
    def _compute_hide_use_payment_terminal(self):
        no_terminals = not bool(self._fields['use_payment_terminal'].selection(self))
        for payment_method in self:
            payment_method.hide_use_payment_terminal = no_terminals or payment_method.is_cash_count

    @api.onchange('use_payment_terminal')
    def _onchange_use_payment_terminal(self):
        """Used by inheriting model to unset the value of the field related to the unselected payment terminal."""
        pass

    @api.depends('config_ids')
    def _compute_open_session_ids(self):
        for payment_method in self:
            payment_method.open_session_ids = self.env['pos.session'].search([('config_id', 'in', payment_method.config_ids.ids), ('state', '!=', 'closed')])

    @api.onchange('is_cash_count')
    def _onchange_is_cash_count(self):
        if not self.is_cash_count:
            self.cash_journal_id = False
        else:
            self.use_payment_terminal = False

    def _is_write_forbidden(self, fields):
        return bool(fields and self.open_session_ids)

    def write(self, vals):
        if self._is_write_forbidden(set(vals.keys())):
            raise UserError('Please close and validate the following open PoS Sessions before modifying this payment method.\n'
                            'Open sessions: %s' % (' '.join(self.open_session_ids.mapped('name')),))
        return super(PosPaymentMethod, self).write(vals)
