from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class PosPaymentMethod(models.Model):
    _name = 'pos.payment.method'
    _description = "Point of Sale Payment Methods"
    _order = "sequence, id"
    _inherit = ['pos.load.mixin']

    def _get_payment_terminal_selection(self):
        return []

    def _get_payment_method_type(self):
        selection = [('none', 'None required'), ('terminal', 'Terminal')]
        if self.env['res.partner.bank'].get_available_qr_methods_in_sequence():
            selection.append(('qr_code', 'Bank App (QR Code)'))
        return selection

    name = fields.Char(string="Method", required=True, translate=True, help='Defines the name of the payment method that will be displayed in the Point of Sale when the payments are selected.')
    sequence = fields.Integer(copy=False)
    outstanding_account_id = fields.Many2one('account.account',
        string='Outstanding Account',
        ondelete='restrict',
        help='Account used as outstanding account when creating accounting payment records for bank payments.')
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
    default_pos_receivable_account_name = fields.Char(related="company_id.account_default_pos_receivable_account_id.display_name", string="Default Receivable Account Name")
    use_payment_terminal = fields.Selection(selection=lambda self: self._get_payment_terminal_selection(), string='Use a Payment Terminal', help='Record payments with a terminal on this journal.')
    # used to hide use_payment_terminal when no payment interfaces are installed
    hide_use_payment_terminal = fields.Boolean(compute='_compute_hide_use_payment_terminal')
    active = fields.Boolean(default=True)
    type = fields.Selection(selection=[('cash', 'Cash'), ('bank', 'Bank'), ('pay_later', 'Customer Account')], compute="_compute_type")
    image = fields.Image("Image", max_width=50, max_height=50)
    payment_method_type = fields.Selection(selection=_get_payment_method_type, string="Integration", default='none', required=True)
    default_qr = fields.Char(compute='_compute_qr')
    qr_code_method = fields.Selection(
        string='QR Code Format', copy=False,
        selection=lambda self: self.env['res.partner.bank'].get_available_qr_methods_in_sequence(),
        help='Type of QR-code to be generated for this payment method.',
    )
    hide_qr_code_method = fields.Boolean(compute='_compute_hide_qr_code_method')

    @api.model
    def get_provider_status(self, modules_list):
        return {
            'state': self.env['ir.module.module'].search_read([('name', 'in', modules_list)], ['name', 'state']),
        }

    @api.model
    def _load_pos_data_domain(self, data):
        return ['|', ('active', '=', False), ('active', '=', True)]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'name', 'is_cash_count', 'use_payment_terminal', 'split_transactions', 'type', 'image', 'sequence', 'payment_method_type', 'default_qr']

    @api.depends('type', 'payment_method_type')
    def _compute_hide_use_payment_terminal(self):
        no_terminals = not bool(self._fields['use_payment_terminal'].selection(self))
        for payment_method in self:
            payment_method.hide_use_payment_terminal = no_terminals or payment_method.type in ('cash', 'pay_later') or payment_method.payment_method_type != 'terminal'

    @api.depends('payment_method_type')
    def _compute_hide_qr_code_method(self):
        for payment_method in self:
            payment_method.hide_qr_code_method = payment_method.payment_method_type != 'qr_code' or len(self.env['res.partner.bank'].get_available_qr_methods_in_sequence()) == 1

    @api.onchange('payment_method_type')
    def _onchange_payment_method_type(self):
        # We don't display the field if there is only one option and cannot set a default on it
        if self.payment_method_type == 'none':
            self.use_payment_terminal = False

        selection_options = self.env['res.partner.bank'].get_available_qr_methods_in_sequence()
        if len(selection_options) == 1:
            self.qr_code_method = selection_options[0][0]

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

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('payment_method_type', False):
                self._force_payment_method_type_values(vals, vals['payment_method_type'])
        return super().create(vals_list)

    def write(self, vals):
        if self._is_write_forbidden(set(vals.keys())):
            raise UserError(_('Please close and validate the following open PoS Sessions before modifying this payment method.\n'
                            'Open sessions: %s', (' '.join(self.open_session_ids.mapped('name')),)))

        if 'payment_method_type' in vals:
            self._force_payment_method_type_values(vals, vals['payment_method_type'])
            return super().write(vals)

        pmt_terminal = self.filtered(lambda pm: pm.payment_method_type == 'terminal')
        pmt_qr = self.filtered(lambda pm: pm.payment_method_type == 'qr_code')
        not_pmt = self - pmt_terminal - pmt_qr

        res = True
        forced_vals = vals.copy()
        if pmt_terminal:
            self._force_payment_method_type_values(forced_vals, 'terminal', True)
            res = super(PosPaymentMethod, pmt_terminal).write(forced_vals) and res
        if pmt_qr:
            self._force_payment_method_type_values(forced_vals, 'qr_code', True)
            res = super(PosPaymentMethod, pmt_qr).write(forced_vals) and res
        if not_pmt:
            res = super(PosPaymentMethod, not_pmt).write(vals) and res

        return res

    @staticmethod
    def _force_payment_method_type_values(vals, payment_method_type, if_present=False):
        if payment_method_type == 'terminal':
            disabled_fields_name = ['qr_code_method']
        elif payment_method_type == 'qr_code':
            disabled_fields_name = ['use_payment_terminal']
        else:
            disabled_fields_name = ['use_payment_terminal', 'qr_code_method']
        if if_present:
            for name in disabled_fields_name:
                if name in vals:
                    vals[name] = False
        else:
            for name in disabled_fields_name:
                vals[name] = False

    def copy_data(self, default=None):
        default = dict(default or {}, config_ids=[(5, 0, 0)])
        vals_list = super().copy_data(default=default)

        for pm, vals in zip(self, vals_list):
            if pm.journal_id and pm.journal_id.type == 'cash':
                if ('journal_id' in default and default['journal_id'] == pm.journal_id.id) or ('journal_id' not in default):
                    vals['journal_id'] = False
        return vals_list

    @api.constrains('payment_method_type', 'journal_id', 'qr_code_method')
    def _check_payment_method(self):
        for rec in self:
            if rec.payment_method_type == "qr_code":
                if (rec.journal_id.type != 'bank' or not rec.journal_id.bank_account_id):
                    raise ValidationError(_("At least one bank account must be defined on the journal to allow registering QR code payments with Bank apps."))
                if not rec.qr_code_method:
                    raise ValidationError(_("You must select a QR-code method to generate QR-codes for this payment method."))
                error_msg = self.journal_id.bank_account_id._get_error_messages_for_qr(self.qr_code_method, False, rec.company_id.currency_id)
                if error_msg:
                    raise ValidationError(error_msg)

    @api.depends('payment_method_type', 'journal_id')
    def _compute_qr(self):
        for pm in self:
            if pm.payment_method_type != "qr_code":
                pm.default_qr = False
                continue
            try:
                # Generate QR without amount that can then be used when the POS is offline
                pm.default_qr = pm.get_qr_code(False, '', '', pm.company_id.currency_id.id, False)
            except UserError:
                pm.default_qr = False

    def get_qr_code(self, amount, free_communication, structured_communication, currency, debtor_partner):
        """ Generates and returns a QR-code
        """
        self.ensure_one()
        if self.payment_method_type != "qr_code" or not self.qr_code_method:
            raise UserError(_("This payment method is not configured to generate QR codes."))
        payment_bank = self.journal_id.bank_account_id
        debtor_partner = self.env['res.partner'].browse(debtor_partner)
        currency = self.env['res.currency'].browse(currency)

        return payment_bank.with_context(is_online_qr=True).build_qr_code_base64(
            float(amount), free_communication, structured_communication, currency, debtor_partner, self.qr_code_method, silent_errors=False)
