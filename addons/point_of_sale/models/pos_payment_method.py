from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PosPaymentMethod(models.Model):
    _name = 'pos.payment.method'
    _description = "Point of Sale Payment Method"
    _order = "sequence, id"
    _inherit = ['pos.load.mixin']

    def _get_terminal_provider_selection(self):
        return []

    def _get_external_qr_provider_selection(self):
        return []

    def _get_provider_selection(self):
        return self._get_terminal_provider_selection() + self._get_external_qr_provider_selection()

    def _get_payment_method_type(self):
        selection = [
            ('none', self.env._('None required')),
            ('terminal', self.env._('Terminal')),
            ('external_qr', self.env._('Quick Pay (QR Code)')),
        ]
        if self.env['res.partner.bank'].get_available_qr_methods_in_sequence():
            selection.append(('bank_qr_code', self.env._('Bank App (QR Code)')))
        return selection

    def _is_online_payment(self):
        return False

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
        index='btree_not_null',
        check_company=True,
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
    active = fields.Boolean(default=True)
    type = fields.Selection(selection=[('cash', 'Cash'), ('bank', 'Bank'), ('pay_later', 'Customer Account')], compute="_compute_type")
    image = fields.Image("Image", max_width=50, max_height=50)
    payment_method_type = fields.Selection(selection=lambda self: self._get_payment_method_type(), string="Integration", default='none', required=True)
    default_qr = fields.Char(compute='_compute_qr')
    qr_code_method = fields.Selection(
        string='QR Code Format', copy=False,
        selection=lambda self: self.env['res.partner.bank'].get_available_qr_methods_in_sequence(),
        help='Type of QR-code to be generated for this payment method.',
    )
    hide_qr_code_method = fields.Boolean(compute='_compute_hide_qr_code_method')

    payment_provider = fields.Selection(selection=lambda self: self._get_provider_selection(), string='Payment Provider', help='Payment provider that will be used to process payments made with this payment method.')
    hide_payment_provider = fields.Boolean(compute='_compute_hide_payment_provider')

    @api.model
    def get_provider_status(self, modules_list):
        return {
            'state': self.env['ir.module.module'].search_read([('name', 'in', modules_list)], ['name', 'state']),
        }

    @api.model
    def _load_pos_data_domain(self, data, config):
        return ['|', ('active', '=', False), ('active', '=', True)]

    @api.model
    def _load_pos_data_fields(self, config):
        return ['id', 'name', 'is_cash_count', 'payment_provider', 'split_transactions', 'type', 'image', 'sequence', 'payment_method_type', 'default_qr']

    @api.depends('type', 'payment_method_type')
    def _compute_hide_payment_provider(self):
        no_payment_provider = not bool(self._fields['payment_provider'].selection(self))
        for payment_method in self:
            payment_method.hide_payment_provider = no_payment_provider or payment_method.payment_method_type not in ('terminal', 'external_qr')

    @api.depends('payment_method_type')
    def _compute_hide_qr_code_method(self):
        for payment_method in self:
            payment_method.hide_qr_code_method = payment_method.payment_method_type != 'bank_qr_code' or len(self.env['res.partner.bank'].get_available_qr_methods_in_sequence()) == 1

    @api.onchange('payment_method_type')
    def _onchange_payment_method_type(self):
        # When changing the payment method type, ensure the payment provider is still valid
        terminal_selection = [pm[0] for pm in self._get_terminal_provider_selection()]
        external_qr_selection = [pm[0] for pm in self._get_external_qr_provider_selection()]
        for payment_method in self:
            if (payment_method.payment_method_type == 'terminal' and payment_method.payment_provider not in terminal_selection) or \
                (payment_method.payment_method_type == 'external_qr' and payment_method.payment_provider not in external_qr_selection) or \
                (payment_method.payment_method_type not in ('terminal', 'external_qr')):
                payment_method.payment_provider = False

        # We don't display the field if there is only one option and cannot set a default on it
        selection_options = self.env['res.partner.bank'].get_available_qr_methods_in_sequence()
        if len(selection_options) == 1:
            self.qr_code_method = selection_options[0][0]

    @api.onchange('payment_provider')
    def _onchange_payment_provider(self):
        terminal_selection = [pm[0] for pm in self._get_terminal_provider_selection()]
        external_qr_selection = [pm[0] for pm in self._get_external_qr_provider_selection()]
        for payment_method in self:
            if payment_method.payment_provider in terminal_selection and payment_method.payment_method_type != 'terminal':
                payment_method.payment_method_type = 'terminal'
            elif payment_method.payment_provider in external_qr_selection and payment_method.payment_method_type != 'external_qr':
                payment_method.payment_method_type = 'external_qr'

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
            if pm.journal_id and pm.journal_id.type == 'bank':
                chart_template = self.with_context(allowed_company_ids=self.env.company.root_id.ids).env['account.chart.template']
                pm.outstanding_account_id = chart_template.ref('account_journal_payment_debit_account_id', raise_if_not_found=False) or self.company_id.transfer_account_id
        if self.is_cash_count:
            self.payment_provider = False

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
        pmt_bank_qr = self.filtered(lambda pm: pm.payment_method_type == 'bank_qr_code')
        pmt_external_qr = self.filtered(lambda pm: pm.payment_method_type == 'external_qr')
        not_pmt = self - pmt_terminal - pmt_bank_qr - pmt_external_qr

        res = True
        forced_vals = vals.copy()
        if pmt_terminal:
            self._force_payment_method_type_values(forced_vals, 'terminal', True)
            res = super(PosPaymentMethod, pmt_terminal).write(forced_vals) and res
        if pmt_bank_qr:
            self._force_payment_method_type_values(forced_vals, 'bank_qr_code', True)
            res = super(PosPaymentMethod, pmt_bank_qr).write(forced_vals) and res
        if pmt_external_qr:
            self._force_payment_method_type_values(forced_vals, 'external_qr', True)
            res = super().write(forced_vals) and res
        if not_pmt:
            res = super(PosPaymentMethod, not_pmt).write(vals) and res

        return res

    @staticmethod
    def _force_payment_method_type_values(vals, payment_method_type, if_present=False):
        if payment_method_type in ['terminal', 'external_qr']:
            disabled_fields_name = ['qr_code_method']
        elif payment_method_type == 'bank_qr_code':
            disabled_fields_name = ['payment_provider']
        else:
            disabled_fields_name = ['payment_provider', 'qr_code_method']
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
            if 'name' not in default:
                vals['name'] = _("%s (copy)", pm.name)
            if pm.journal_id and pm.journal_id.type == 'cash':
                if ('journal_id' in default and default['journal_id'] == pm.journal_id.id) or ('journal_id' not in default):
                    vals['journal_id'] = False
        return vals_list

    @api.constrains('payment_method_type', 'journal_id', 'qr_code_method')
    def _check_payment_method(self):
        for rec in self:
            if rec.payment_method_type == "bank_qr_code":
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
            if pm.payment_method_type != "bank_qr_code":
                pm.default_qr = False
                continue
            try:
                # Generate QR without amount that can then be used when the POS is offline
                pm.default_qr = pm.get_qr_code(False, '', '', pm.company_id.currency_id.id, False)
            except UserError:
                pm.default_qr = False

    @api.model
    def _allowed_actions_in_self_order(self):
        # This method is overridden by payment terminal modules to
        # allow their methods to be called from the Self Order Kiosk.
        # It is defined here rather than in `pos_self_order` so that
        # the payment terminal modules don't need to depend on it.
        return []

    def get_qr_code(self, amount, free_communication, structured_communication, currency, debtor_partner):
        """ Generates and returns a QR-code
        """
        self.ensure_one()
        if self.payment_method_type != "bank_qr_code" or not self.qr_code_method:
            raise UserError(_("This payment method is not configured to generate QR codes."))
        payment_bank = self.journal_id.bank_account_id
        debtor_partner = self.env['res.partner'].browse(debtor_partner)
        currency = self.env['res.currency'].browse(currency)

        return payment_bank.with_context(is_online_qr=True).build_qr_code_base64(
            float(amount), free_communication, structured_communication, currency, debtor_partner, self.qr_code_method, silent_errors=False)
