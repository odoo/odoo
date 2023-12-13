from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PosPaymentMethod(models.Model):
    _name = "pos.payment.method"
    _description = "Point of Sale Payment Methods"
    _order = "sequence, id"

    def _get_payment_terminal_selection(self):
        return []

    name = fields.Char(string="Method", required=True, translate=True, help='Defines the name of the payment method that will be displayed in the Point of Sale when the payments are selected.')
    sequence = fields.Integer(copy=False)
    outstanding_account_id = fields.Many2one('account.account',
        string='Outstanding Account',
        ondelete='restrict',
        help='Leave empty to use the default account from the company setting.\n'
             'Account used as outstanding account when creating accounting payment records for bank payments.')
    receivable_account_id = fields.Many2one('account.account',
        string='Intermediary Account',
        ondelete='restrict',
        domain=[('reconcile', '=', True), ('account_type', '=', 'asset_receivable')],
        help="Leave empty to use the default account from the company setting.\n"
             "Overrides the company's receivable account (for Point of Sale) used in the journal entries.")
    is_cash_count = fields.Boolean(string='Cash', compute="_compute_is_cash_count", store=True)
    journal_id = fields.Many2one('account.journal',
        string='Journal',
        domain=['|', '&', ('type', '=', 'cash'), ('pos_payment_method_ids', '=', False), ('type', '=', 'bank')],
        ondelete='restrict',
        help='Leave empty to use the receivable account of customer.\n'
             'Defines the journal where to book the accumulated payments (or individual payment if Identify Customer is true) after closing the session.\n'
             'For cash journal, we directly write to the default account in the journal via statement lines.\n'
             'For bank journal, we write to the outstanding account specified in this payment method.\n'
             'Only cash and bank journals are allowed.')
    split_transactions = fields.Boolean(
        string='Identify Customer',
        default=False,
        help='Forces to set a customer when using this payment method and splits the journal entries for each customer. It could slow down the closing process.')
    open_session_ids = fields.Many2many('pos.session', string='Pos Sessions', compute='_compute_open_session_ids', help='Open PoS sessions that are using this payment method.')
    config_ids = fields.Many2many('pos.config', string='Point of Sale')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    use_payment_terminal = fields.Selection(selection=lambda self: self._get_payment_terminal_selection(), string='Use a Payment Terminal', help='Record payments with a terminal on this journal.')
    # used to hide use_payment_terminal when no payment interfaces are installed
    hide_use_payment_terminal = fields.Boolean(compute='_compute_hide_use_payment_terminal')
    active = fields.Boolean(default=True)
    type = fields.Selection(selection=[('cash', 'Cash'), ('bank', 'Bank'), ('pay_later', 'Customer Account')], compute="_compute_type")
    image = fields.Image("Image", max_width=50, max_height=50)

    @api.depends('type')
    def _compute_hide_use_payment_terminal(self):
        no_terminals = not bool(self._fields['use_payment_terminal'].selection(self))
        for payment_method in self:
            payment_method.hide_use_payment_terminal = no_terminals or payment_method.type in ('cash', 'pay_later')

    @api.onchange('use_payment_terminal')
    def _onchange_use_payment_terminal(self):
        """Used by inheriting model to unset the value of the field related to the unselected payment terminal."""
        pass

    @api.depends('config_ids')
    def _compute_open_session_ids(self):
        for payment_method in self:
            payment_method.open_session_ids = self.env['pos.session'].search([('config_id', 'in', payment_method.config_ids.ids), ('state', '!=', 'closed')])

    @api.depends('journal_id', 'split_transactions')
    def _compute_type(self):
        for pm in self:
            if pm.journal_id.type in {'cash', 'bank'}:
                pm.type = pm.journal_id.type
            else:
                pm.type = 'pay_later'

    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        for pm in self:
            if pm.journal_id and pm.journal_id.type not in ['cash', 'bank']:
                raise UserError(_("Only journals of type 'Cash' or 'Bank' could be used with payment methods."))
        if self.is_cash_count:
            self.use_payment_terminal = False

    @api.depends('type')
    def _compute_is_cash_count(self):
        for pm in self:
            pm.is_cash_count = pm.type == 'cash'

    def _is_write_forbidden(self, fields):
        whitelisted_fields = {'sequence'}
        return bool(fields - whitelisted_fields and self.open_session_ids)

    def write(self, vals):
        if self._is_write_forbidden(set(vals.keys())):
            raise UserError(_('Please close and validate the following open PoS Sessions before modifying this payment method.\n'
                            'Open sessions: %s', (' '.join(self.open_session_ids.mapped('name')),)))
        return super(PosPaymentMethod, self).write(vals)

    def copy(self, default=None):
        default = dict(default or {}, config_ids=[(5, 0, 0)])
        return super().copy(default)
