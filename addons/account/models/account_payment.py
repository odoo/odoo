# -*- coding: utf-8 -*-
from odoo import models, fields, api, _, Command
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import format_date, formatLang


class AccountPayment(models.Model):
    _name = "account.payment"
    _inherits = {'account.move': 'move_id'}
    _inherit = ['mail.thread.main.attachment', 'mail.activity.mixin']
    _description = "Payments"
    _order = "date desc, name desc"
    _check_company_auto = True

    # == Business fields ==
    move_id = fields.Many2one(
        comodel_name='account.move',
        string='Journal Entry', required=True, readonly=True, ondelete='cascade',
        index='btree_not_null',
        check_company=True)

    is_reconciled = fields.Boolean(string="Is Reconciled", store=True,
        compute='_compute_reconciliation_status')
    is_matched = fields.Boolean(string="Is Matched With a Bank Statement", store=True,
        compute='_compute_reconciliation_status')
    available_partner_bank_ids = fields.Many2many(
        comodel_name='res.partner.bank',
        compute='_compute_available_partner_bank_ids',
    )
    partner_bank_id = fields.Many2one('res.partner.bank', string="Recipient Bank Account",
        readonly=False, store=True, tracking=True,
        compute='_compute_partner_bank_id',
        domain="[('id', 'in', available_partner_bank_ids)]",
        check_company=True,
        ondelete='restrict',
    )
    is_internal_transfer = fields.Boolean(string="Internal Transfer",
        readonly=False, store=True,
        tracking=True,
        compute="_compute_is_internal_transfer")
    qr_code = fields.Html(string="QR Code URL",
        compute="_compute_qr_code")
    paired_internal_transfer_payment_id = fields.Many2one('account.payment',
        help="When an internal transfer is posted, a paired payment is created. "
        "They are cross referenced through this field", copy=False)

    # == Payment methods fields ==
    payment_method_line_id = fields.Many2one('account.payment.method.line', string='Payment Method',
        readonly=False, store=True, copy=False,
        compute='_compute_payment_method_line_id',
        domain="[('id', 'in', available_payment_method_line_ids)]",
        help="Manual: Pay or Get paid by any method outside of Odoo.\n"
        "Payment Providers: Each payment provider has its own Payment Method. Request a transaction on/to a card thanks to a payment token saved by the partner when buying or subscribing online.\n"
        "Check: Pay bills by check and print it from Odoo.\n"
        "Batch Deposit: Collect several customer checks at once generating and submitting a batch deposit to your bank. Module account_batch_payment is necessary.\n"
        "SEPA Credit Transfer: Pay in the SEPA zone by submitting a SEPA Credit Transfer file to your bank. Module account_sepa is necessary.\n"
        "SEPA Direct Debit: Get paid in the SEPA zone thanks to a mandate your partner will have granted to you. Module account_sepa is necessary.\n")
    available_payment_method_line_ids = fields.Many2many('account.payment.method.line',
        compute='_compute_payment_method_line_fields')
    payment_method_id = fields.Many2one(
        related='payment_method_line_id.payment_method_id',
        string="Method",
        tracking=True,
        store=True
    )
    available_journal_ids = fields.Many2many(
        comodel_name='account.journal',
        compute='_compute_available_journal_ids'
    )

    # == Synchronized fields with the account.move.lines ==
    amount = fields.Monetary(currency_field='currency_id')
    payment_type = fields.Selection([
        ('outbound', 'Send'),
        ('inbound', 'Receive'),
    ], string='Payment Type', default='inbound', required=True, tracking=True)
    partner_type = fields.Selection([
        ('customer', 'Customer'),
        ('supplier', 'Vendor'),
    ], default='customer', tracking=True, required=True)
    payment_reference = fields.Char(string="Payment Reference", copy=False, tracking=True,
        help="Reference of the document used to issue this payment. Eg. check number, file name, etc.")
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        compute='_compute_currency_id', store=True, readonly=False, precompute=True,
        help="The payment's currency.")
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string="Customer/Vendor",
        store=True, readonly=False, ondelete='restrict',
        compute='_compute_partner_id',
        domain="['|', ('parent_id','=', False), ('is_company','=', True)]",
        tracking=True,
        check_company=True)
    outstanding_account_id = fields.Many2one(
        comodel_name='account.account',
        string="Outstanding Account",
        store=True,
        compute='_compute_outstanding_account_id',
        check_company=True)
    destination_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Destination Account',
        store=True, readonly=False,
        compute='_compute_destination_account_id',
        domain="[('account_type', 'in', ('asset_receivable', 'liability_payable'))]",
        check_company=True)
    destination_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Destination Journal',
        domain="[('type', 'in', ('bank','cash')), ('id', '!=', journal_id)]",
        check_company=True,
    )

    # == Stat buttons ==
    reconciled_invoice_ids = fields.Many2many('account.move', string="Reconciled Invoices",
        compute='_compute_stat_buttons_from_reconciliation',
        help="Invoices whose journal items have been reconciled with these payments.")
    reconciled_invoices_count = fields.Integer(string="# Reconciled Invoices",
        compute="_compute_stat_buttons_from_reconciliation")

    # used to determine label 'invoice' or 'credit note' in view
    reconciled_invoices_type = fields.Selection(
        [('credit_note', 'Credit Note'), ('invoice', 'Invoice')],
        compute='_compute_stat_buttons_from_reconciliation')
    reconciled_bill_ids = fields.Many2many('account.move', string="Reconciled Bills",
        compute='_compute_stat_buttons_from_reconciliation',
        help="Invoices whose journal items have been reconciled with these payments.")
    reconciled_bills_count = fields.Integer(string="# Reconciled Bills",
        compute="_compute_stat_buttons_from_reconciliation")
    reconciled_statement_line_ids = fields.Many2many(
        comodel_name='account.bank.statement.line',
        string="Reconciled Statement Lines",
        compute='_compute_stat_buttons_from_reconciliation',
        help="Statements lines matched to this payment",
    )
    reconciled_statement_lines_count = fields.Integer(
        string="# Reconciled Statement Lines",
        compute="_compute_stat_buttons_from_reconciliation",
    )

    # == Display purpose fields ==
    payment_method_code = fields.Char(
        related='payment_method_line_id.code')

    # used to know whether the field `partner_bank_id` needs to be displayed or not in the payments form views
    show_partner_bank_account = fields.Boolean(
        compute='_compute_show_require_partner_bank')
    # used to know whether the field `partner_bank_id` needs to be required or not in the payments form views
    require_partner_bank_account = fields.Boolean(
        compute='_compute_show_require_partner_bank')
    country_code = fields.Char(related='company_id.account_fiscal_country_id.code')
    amount_signed = fields.Monetary(
        currency_field='currency_id', compute='_compute_amount_signed', tracking=True,
        help='Negative value of amount field if payment_type is outbound')
    amount_company_currency_signed = fields.Monetary(
        currency_field='company_currency_id', compute='_compute_amount_company_currency_signed', store=True)

    _sql_constraints = [
        (
            'check_amount_not_negative',
            'CHECK(amount >= 0.0)',
            "The payment amount cannot be negative.",
        ),
    ]

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    @api.model
    def _get_valid_payment_account_types(self):
        return ['asset_receivable', 'liability_payable']

    def _seek_for_lines(self):
        ''' Helper used to dispatch the journal items between:
        - The lines using the temporary liquidity account.
        - The lines using the counterpart account.
        - The lines being the write-off lines.
        :return: (liquidity_lines, counterpart_lines, writeoff_lines)
        '''
        self.ensure_one()

        liquidity_lines = self.env['account.move.line']
        counterpart_lines = self.env['account.move.line']
        writeoff_lines = self.env['account.move.line']

        valid_account_types = self._get_valid_payment_account_types()
        for line in self.move_id.line_ids:
            if line.account_id in self._get_valid_liquidity_accounts():
                liquidity_lines += line
            elif line.account_id.account_type in valid_account_types or line.account_id == self.company_id.transfer_account_id:
                counterpart_lines += line
            else:
                writeoff_lines += line

        return liquidity_lines, counterpart_lines, writeoff_lines

    def _get_valid_liquidity_accounts(self):
        return (
            self.journal_id.default_account_id |
            self.payment_method_line_id.payment_account_id |
            self.journal_id.company_id.account_journal_payment_debit_account_id |
            self.journal_id.company_id.account_journal_payment_credit_account_id |
            self.journal_id.inbound_payment_method_line_ids.payment_account_id |
            self.journal_id.outbound_payment_method_line_ids.payment_account_id
        )

    def _get_aml_default_display_map(self):
        return {
            ('outbound', 'customer'): _("Customer Reimbursement"),
            ('inbound', 'customer'): _("Customer Payment"),
            ('outbound', 'supplier'): _("Vendor Payment"),
            ('inbound', 'supplier'): _("Vendor Reimbursement"),
        }

    def _get_aml_default_display_name_list(self):
        """ Hook allowing custom values when constructing the default label to set on the journal items.

        :return: A list of terms to concatenate all together. E.g.
            [
                ('label', "Vendor Reimbursement"),
                ('sep', ' '),
                ('amount', "$ 1,555.00"),
                ('sep', ' - '),
                ('date', "05/14/2020"),
            ]
        """
        self.ensure_one()
        display_map = self._get_aml_default_display_map()
        values = [
            ('label', _("Internal Transfer") if self.is_internal_transfer else display_map[(self.payment_type, self.partner_type)]),
            ('sep', ' '),
            ('amount', formatLang(self.env, self.amount, currency_obj=self.currency_id)),
        ]
        if self.partner_id:
            values += [
                ('sep', ' - '),
                ('partner', self.partner_id.display_name),
            ]
        values += [
            ('sep', ' - '),
            ('date', format_date(self.env, fields.Date.to_string(self.date))),
        ]
        return values

    def _get_liquidity_aml_display_name_list(self):
        """ Hook allowing custom values when constructing the label to set on the liquidity line.

        :return: A list of terms to concatenate all together. E.g.
            [('reference', "INV/2018/0001")]
        """
        self.ensure_one()
        if self.is_internal_transfer:
            if self.payment_type == 'inbound':
                return [('transfer_to', _('Transfer to %s', self.journal_id.name))]
            else: # payment.payment_type == 'outbound':
                return [('transfer_from', _('Transfer from %s', self.journal_id.name))]
        elif self.payment_reference:
            return [('reference', self.payment_reference)]
        else:
            return self._get_aml_default_display_name_list()

    def _get_counterpart_aml_display_name_list(self):
        """ Hook allowing custom values when constructing the label to set on the counterpart line.

        :return: A list of terms to concatenate all together. E.g.
            [('reference', "INV/2018/0001")]
        """
        self.ensure_one()
        if self.payment_reference:
            return [('reference', self.payment_reference)]
        else:
            return self._get_aml_default_display_name_list()

    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        ''' Prepare the dictionary to create the default account.move.lines for the current payment.
        :param write_off_line_vals: Optional list of dictionaries to create a write-off account.move.line easily containing:
            * amount:       The amount to be added to the counterpart amount.
            * name:         The label to set on the line.
            * account_id:   The account on which create the write-off.
        :return: A list of python dictionary to be passed to the account.move.line's 'create' method.
        '''
        self.ensure_one()
        write_off_line_vals = write_off_line_vals or {}

        if not self.outstanding_account_id:
            raise UserError(_(
                "You can't create a new payment without an outstanding payments/receipts account set either on the company or the %s payment method in the %s journal.",
                self.payment_method_line_id.name, self.journal_id.display_name))

        # Compute amounts.
        write_off_line_vals_list = write_off_line_vals or []
        write_off_amount_currency = sum(x['amount_currency'] for x in write_off_line_vals_list)
        write_off_balance = sum(x['balance'] for x in write_off_line_vals_list)

        if self.payment_type == 'inbound':
            # Receive money.
            liquidity_amount_currency = self.amount
        elif self.payment_type == 'outbound':
            # Send money.
            liquidity_amount_currency = -self.amount
        else:
            liquidity_amount_currency = 0.0

        liquidity_balance = self.currency_id._convert(
            liquidity_amount_currency,
            self.company_id.currency_id,
            self.company_id,
            self.date,
        )
        counterpart_amount_currency = -liquidity_amount_currency - write_off_amount_currency
        counterpart_balance = -liquidity_balance - write_off_balance
        currency_id = self.currency_id.id

        # Compute a default label to set on the journal items.
        liquidity_line_name = ''.join(x[1] for x in self._get_liquidity_aml_display_name_list())
        counterpart_line_name = ''.join(x[1] for x in self._get_counterpart_aml_display_name_list())

        line_vals_list = [
            # Liquidity line.
            {
                'name': liquidity_line_name,
                'date_maturity': self.date,
                'amount_currency': liquidity_amount_currency,
                'currency_id': currency_id,
                'debit': liquidity_balance if liquidity_balance > 0.0 else 0.0,
                'credit': -liquidity_balance if liquidity_balance < 0.0 else 0.0,
                'partner_id': self.partner_id.id,
                'account_id': self.outstanding_account_id.id,
            },
            # Receivable / Payable.
            {
                'name': counterpart_line_name,
                'date_maturity': self.date,
                'amount_currency': counterpart_amount_currency,
                'currency_id': currency_id,
                'debit': counterpart_balance if counterpart_balance > 0.0 else 0.0,
                'credit': -counterpart_balance if counterpart_balance < 0.0 else 0.0,
                'partner_id': self.partner_id.id,
                'account_id': self.destination_account_id.id,
            },
        ]
        return line_vals_list + write_off_line_vals_list

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('move_id.line_ids.amount_residual', 'move_id.line_ids.amount_residual_currency', 'move_id.line_ids.account_id')
    def _compute_reconciliation_status(self):
        ''' Compute the field indicating if the payments are already reconciled with something.
        This field is used for display purpose (e.g. display the 'reconcile' button redirecting to the reconciliation
        widget).
        '''
        for pay in self:
            liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()

            if not pay.currency_id or not pay.id:
                pay.is_reconciled = False
                pay.is_matched = False
            elif pay.currency_id.is_zero(pay.amount):
                pay.is_reconciled = True
                pay.is_matched = True
            else:
                residual_field = 'amount_residual' if pay.currency_id == pay.company_id.currency_id else 'amount_residual_currency'
                if pay.journal_id.default_account_id and pay.journal_id.default_account_id in liquidity_lines.account_id:
                    # Allow user managing payments without any statement lines by using the bank account directly.
                    # In that case, the user manages transactions only using the register payment wizard.
                    pay.is_matched = True
                else:
                    pay.is_matched = pay.currency_id.is_zero(sum(liquidity_lines.mapped(residual_field)))

                reconcile_lines = (counterpart_lines + writeoff_lines).filtered(lambda line: line.account_id.reconcile)
                pay.is_reconciled = pay.currency_id.is_zero(sum(reconcile_lines.mapped(residual_field)))

    @api.model
    def _get_method_codes_using_bank_account(self):
        return ['manual']

    @api.model
    def _get_method_codes_needing_bank_account(self):
        return []

    @api.depends('payment_method_code')
    def _compute_show_require_partner_bank(self):
        """ Computes if the destination bank account must be displayed in the payment form view. By default, it
        won't be displayed but some modules might change that, depending on the payment type."""
        for payment in self:
            if payment.journal_id.type == 'cash':
                payment.show_partner_bank_account = False
            else:
                payment.show_partner_bank_account = payment.payment_method_code in self._get_method_codes_using_bank_account()
            payment.require_partner_bank_account = payment.state == 'draft' and payment.payment_method_code in self._get_method_codes_needing_bank_account()

    @api.depends('amount_total_signed', 'payment_type')
    def _compute_amount_company_currency_signed(self):
        for payment in self:
            liquidity_lines = payment._seek_for_lines()[0]
            payment.amount_company_currency_signed = sum(liquidity_lines.mapped('balance'))

    @api.depends('amount', 'payment_type')
    def _compute_amount_signed(self):
        for payment in self:
            if payment.payment_type == 'outbound':
                payment.amount_signed = -payment.amount
            else:
                payment.amount_signed = payment.amount

    @api.depends('partner_id', 'company_id', 'payment_type', 'destination_journal_id', 'is_internal_transfer')
    def _compute_available_partner_bank_ids(self):
        for pay in self:
            if pay.payment_type == 'inbound':
                pay.available_partner_bank_ids = pay.journal_id.bank_account_id
            elif pay.is_internal_transfer:
                pay.available_partner_bank_ids = pay.destination_journal_id.bank_account_id
            else:
                pay.available_partner_bank_ids = pay.partner_id.bank_ids\
                        .filtered(lambda x: x.company_id.id in (False, pay.company_id.id))._origin

    @api.depends('available_partner_bank_ids', 'journal_id')
    def _compute_partner_bank_id(self):
        ''' The default partner_bank_id will be the first available on the partner. '''
        for pay in self:
            pay.partner_bank_id = pay.available_partner_bank_ids[:1]._origin

    @api.depends('partner_id', 'journal_id', 'destination_journal_id')
    def _compute_is_internal_transfer(self):
        for payment in self:
            payment.is_internal_transfer = payment.partner_id \
                                           and payment.partner_id == payment.journal_id.company_id.partner_id \
                                           and payment.destination_journal_id

    @api.depends('available_payment_method_line_ids')
    def _compute_payment_method_line_id(self):
        ''' Compute the 'payment_method_line_id' field.
        This field is not computed in '_compute_payment_method_line_fields' because it's a stored editable one.
        '''
        for pay in self:
            available_payment_method_lines = pay.available_payment_method_line_ids

            # Select the first available one by default.
            if pay.payment_method_line_id in available_payment_method_lines:
                pay.payment_method_line_id = pay.payment_method_line_id
            elif available_payment_method_lines:
                pay.payment_method_line_id = available_payment_method_lines[0]._origin
            else:
                pay.payment_method_line_id = False

    @api.depends('payment_type', 'journal_id', 'currency_id')
    def _compute_payment_method_line_fields(self):
        for pay in self:
            pay.available_payment_method_line_ids = pay.journal_id._get_available_payment_method_lines(pay.payment_type)
            to_exclude = pay._get_payment_method_codes_to_exclude()
            if to_exclude:
                pay.available_payment_method_line_ids = pay.available_payment_method_line_ids.filtered(lambda x: x.code not in to_exclude)

    @api.depends('payment_type')
    def _compute_available_journal_ids(self):
        """
        Get all journals having at least one payment method for inbound/outbound depending on the payment_type.
        """
        journals = self.env['account.journal'].search([
            '|',
            ('company_id', 'parent_of', self.env.company.id),
            ('company_id', 'child_of', self.env.company.id),
            ('type', 'in', ('bank', 'cash')),
        ])
        for pay in self:
            if pay.payment_type == 'inbound':
                pay.available_journal_ids = journals.filtered('inbound_payment_method_line_ids')
            else:
                pay.available_journal_ids = journals.filtered('outbound_payment_method_line_ids')

    def _get_payment_method_codes_to_exclude(self):
        # can be overriden to exclude payment methods based on the payment characteristics
        self.ensure_one()
        return []

    @api.depends('journal_id')
    def _compute_currency_id(self):
        for pay in self:
            pay.currency_id = pay.journal_id.currency_id or pay.journal_id.company_id.currency_id

    @api.depends('is_internal_transfer')
    def _compute_partner_id(self):
        for pay in self:
            if pay.is_internal_transfer:
                pay.partner_id = pay.journal_id.company_id.partner_id
            elif pay.partner_id == pay.journal_id.company_id.partner_id:
                pay.partner_id = False
            else:
                pay.partner_id = pay.partner_id

    @api.depends('journal_id', 'payment_type', 'payment_method_line_id')
    def _compute_outstanding_account_id(self):
        for pay in self:
            if pay.payment_type == 'inbound':
                pay.outstanding_account_id = (pay.payment_method_line_id.payment_account_id
                                              or pay.journal_id.company_id.account_journal_payment_debit_account_id)
            elif pay.payment_type == 'outbound':
                pay.outstanding_account_id = (pay.payment_method_line_id.payment_account_id
                                              or pay.journal_id.company_id.account_journal_payment_credit_account_id)
            else:
                pay.outstanding_account_id = False

    @api.depends('journal_id', 'partner_id', 'partner_type', 'is_internal_transfer', 'destination_journal_id')
    def _compute_destination_account_id(self):
        self.destination_account_id = False
        for pay in self:
            if pay.is_internal_transfer:
                pay.destination_account_id = pay.destination_journal_id.company_id.transfer_account_id
            elif pay.partner_type == 'customer':
                # Receive money from invoice or send money to refund it.
                if pay.partner_id:
                    pay.destination_account_id = pay.partner_id.with_company(pay.company_id).property_account_receivable_id
                else:
                    pay.destination_account_id = self.env['account.account'].search([
                        *self.env['account.account']._check_company_domain(pay.company_id),
                        ('account_type', '=', 'asset_receivable'),
                        ('deprecated', '=', False),
                    ], limit=1)
            elif pay.partner_type == 'supplier':
                # Send money to pay a bill or receive money to refund it.
                if pay.partner_id:
                    pay.destination_account_id = pay.partner_id.with_company(pay.company_id).property_account_payable_id
                else:
                    pay.destination_account_id = self.env['account.account'].search([
                        *self.env['account.account']._check_company_domain(pay.company_id),
                        ('account_type', '=', 'liability_payable'),
                        ('deprecated', '=', False),
                    ], limit=1)

    @api.depends('partner_bank_id', 'amount', 'ref', 'currency_id', 'journal_id', 'move_id.state',
                 'payment_method_line_id', 'payment_type')
    def _compute_qr_code(self):
        for pay in self:
            if pay.state in ('draft', 'posted') \
                and pay.partner_bank_id \
                and pay.partner_bank_id.allow_out_payment \
                and pay.payment_method_line_id.code == 'manual' \
                and pay.payment_type == 'outbound' \
                and pay.currency_id:

                if pay.partner_bank_id:
                    qr_code = pay.partner_bank_id.build_qr_code_base64(pay.amount, pay.ref, pay.ref, pay.currency_id, pay.partner_id)
                else:
                    qr_code = None

                if qr_code:
                    pay.qr_code = '''
                        <br/>
                        <img class="border border-dark rounded" src="{qr_code}"/>
                        <br/>
                        <strong class="text-center">{txt}</strong>
                        '''.format(txt = _('Scan me with your banking app.'),
                                   qr_code = qr_code)
                    continue

            pay.qr_code = None

    @api.depends('move_id.line_ids.matched_debit_ids', 'move_id.line_ids.matched_credit_ids')
    def _compute_stat_buttons_from_reconciliation(self):
        ''' Retrieve the invoices reconciled to the payments through the reconciliation (account.partial.reconcile). '''
        stored_payments = self.filtered('id')
        if not stored_payments:
            self.reconciled_invoice_ids = False
            self.reconciled_invoices_count = 0
            self.reconciled_invoices_type = ''
            self.reconciled_bill_ids = False
            self.reconciled_bills_count = 0
            self.reconciled_statement_line_ids = False
            self.reconciled_statement_lines_count = 0
            return

        self.env['account.payment'].flush_model(fnames=['move_id', 'outstanding_account_id'])
        self.env['account.move'].flush_model(fnames=['move_type', 'payment_id', 'statement_line_id'])
        self.env['account.move.line'].flush_model(fnames=['move_id', 'account_id', 'statement_line_id'])
        self.env['account.partial.reconcile'].flush_model(fnames=['debit_move_id', 'credit_move_id'])

        self._cr.execute('''
            SELECT
                payment.id,
                ARRAY_AGG(DISTINCT invoice.id) AS invoice_ids,
                invoice.move_type
            FROM account_payment payment
            JOIN account_move move ON move.id = payment.move_id
            JOIN account_move_line line ON line.move_id = move.id
            JOIN account_partial_reconcile part ON
                part.debit_move_id = line.id
                OR
                part.credit_move_id = line.id
            JOIN account_move_line counterpart_line ON
                part.debit_move_id = counterpart_line.id
                OR
                part.credit_move_id = counterpart_line.id
            JOIN account_move invoice ON invoice.id = counterpart_line.move_id
            JOIN account_account account ON account.id = line.account_id
            WHERE account.account_type IN ('asset_receivable', 'liability_payable')
                AND payment.id IN %(payment_ids)s
                AND line.id != counterpart_line.id
                AND invoice.move_type in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund', 'out_receipt', 'in_receipt')
            GROUP BY payment.id, invoice.move_type
        ''', {
            'payment_ids': tuple(stored_payments.ids)
        })
        query_res = self._cr.dictfetchall()
        self.reconciled_invoice_ids = self.reconciled_invoices_count = False
        self.reconciled_bill_ids = self.reconciled_bills_count = False
        for res in query_res:
            pay = self.browse(res['id'])
            if res['move_type'] in self.env['account.move'].get_sale_types(True):
                pay.reconciled_invoice_ids += self.env['account.move'].browse(res.get('invoice_ids', []))
                pay.reconciled_invoices_count = len(res.get('invoice_ids', []))
            else:
                pay.reconciled_bill_ids += self.env['account.move'].browse(res.get('invoice_ids', []))
                pay.reconciled_bills_count = len(res.get('invoice_ids', []))

        self._cr.execute('''
            SELECT
                payment.id,
                ARRAY_AGG(DISTINCT counterpart_line.statement_line_id) AS statement_line_ids
            FROM account_payment payment
            JOIN account_move move ON move.id = payment.move_id
            JOIN account_move_line line ON line.move_id = move.id
            JOIN account_account account ON account.id = line.account_id
            JOIN account_partial_reconcile part ON
                part.debit_move_id = line.id
                OR
                part.credit_move_id = line.id
            JOIN account_move_line counterpart_line ON
                part.debit_move_id = counterpart_line.id
                OR
                part.credit_move_id = counterpart_line.id
            WHERE account.id = payment.outstanding_account_id
                AND payment.id IN %(payment_ids)s
                AND line.id != counterpart_line.id
                AND counterpart_line.statement_line_id IS NOT NULL
            GROUP BY payment.id
        ''', {
            'payment_ids': tuple(stored_payments.ids)
        })
        query_res = dict((payment_id, statement_line_ids) for payment_id, statement_line_ids in self._cr.fetchall())

        for pay in self:
            statement_line_ids = query_res.get(pay.id, [])
            pay.reconciled_statement_line_ids = [Command.set(statement_line_ids)]
            pay.reconciled_statement_lines_count = len(statement_line_ids)
            if len(pay.reconciled_invoice_ids.mapped('move_type')) == 1 and pay.reconciled_invoice_ids[0].move_type == 'out_refund':
                pay.reconciled_invoices_type = 'credit_note'
            else:
                pay.reconciled_invoices_type = 'invoice'

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------

    @api.onchange('posted_before', 'state', 'journal_id', 'date')
    def _onchange_journal_date(self):
        # Before the record is created, the move_id doesn't exist yet, and the name will not be
        # recomputed correctly if we change the journal or the date, leading to inconsitencies
        if not self.move_id:
            self.name = False

    # -------------------------------------------------------------------------
    # CONSTRAINT METHODS
    # -------------------------------------------------------------------------

    @api.constrains('payment_method_line_id')
    def _check_payment_method_line_id(self):
        ''' Ensure the 'payment_method_line_id' field is not null.
        Can't be done using the regular 'required=True' because the field is a computed editable stored one.
        '''
        for pay in self:
            if not pay.payment_method_line_id:
                raise ValidationError(_("Please define a payment method line on your payment."))

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------

    def new(self, values=None, origin=None, ref=None):
        payment = super().new(values, origin, ref)
        if not payment.journal_id and not payment.default_get(['journal_id']):  # might not be computed because declared by inheritance
            payment.move_id.payment_id = payment
            payment.move_id._compute_journal_id()
        return payment

    @api.model_create_multi
    def create(self, vals_list):
        # OVERRIDE
        write_off_line_vals_list = []

        for vals in vals_list:

            # Hack to add a custom write-off line.
            write_off_line_vals_list.append(vals.pop('write_off_line_vals', None))

            # Force the move_type to avoid inconsistency with residual 'default_move_type' inside the context.
            vals['move_type'] = 'entry'
            vals['journal_id'] = vals.get('journal_id') or self.move_id.with_context(is_payment=True)._search_default_journal().id

        payments = super().create([{
            'name': False,
            **vals,
        } for vals in vals_list])

        for i, pay in enumerate(payments):
            write_off_line_vals = write_off_line_vals_list[i]

            # Write payment_id on the journal entry plus the fields being stored in both models but having the same
            # name, e.g. partner_bank_id. The ORM is currently not able to perform such synchronization and make things
            # more difficult by creating related fields on the fly to handle the _inherits.
            # Then, when partner_bank_id is in vals, the key is consumed by account.payment but is never written on
            # account.move.
            to_write = {'payment_id': pay.id}
            for k, v in vals_list[i].items():
                if k in self._fields and self._fields[k].store and k in pay.move_id._fields and pay.move_id._fields[k].store:
                    to_write[k] = v

            if 'line_ids' not in vals_list[i]:
                to_write['line_ids'] = [(0, 0, line_vals) for line_vals in pay._prepare_move_line_default_vals(write_off_line_vals=write_off_line_vals)]

            pay.move_id.write(to_write)
            self.env.add_to_compute(self.env['account.move']._fields['name'], pay.move_id)

        # We need to reset the cached name, since it was recomputed on the delegate account.move model
        payments.invalidate_recordset(fnames=['name'])
        return payments

    def write(self, vals):
        # OVERRIDE
        res = super().write(vals)
        self._synchronize_to_moves(set(vals.keys()))
        return res

    def unlink(self):
        # OVERRIDE to unlink the inherited account.move (move_id field) as well.
        moves = self.with_context(force_delete=True).move_id
        res = super().unlink()
        moves.unlink()
        return res

    @api.depends('move_id.name')
    def _compute_display_name(self):
        for payment in self:
            payment.display_name = payment.move_id.name if payment.move_id.name != '/' else _('Draft Payment')

    # -------------------------------------------------------------------------
    # SYNCHRONIZATION account.payment <-> account.move
    # -------------------------------------------------------------------------

    def _synchronize_from_moves(self, changed_fields):
        ''' Update the account.payment regarding its related account.move.
        Also, check both models are still consistent.
        :param changed_fields: A set containing all modified fields on account.move.
        '''
        if self._context.get('skip_account_move_synchronization'):
            return

        for pay in self.with_context(skip_account_move_synchronization=True):

            # After the migration to 14.0, the journal entry could be shared between the account.payment and the
            # account.bank.statement.line. In that case, the synchronization will only be made with the statement line.
            if pay.move_id.statement_line_id:
                continue

            move = pay.move_id
            move_vals_to_write = {}
            payment_vals_to_write = {}

            if 'journal_id' in changed_fields:
                if pay.journal_id.type not in ('bank', 'cash'):
                    raise UserError(_("A payment must always belongs to a bank or cash journal."))

            if 'line_ids' in changed_fields:
                all_lines = move.line_ids
                liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()

                if len(liquidity_lines) != 1:
                    raise UserError(_(
                        "Journal Entry %s is not valid. In order to proceed, the journal items must "
                        "include one and only one outstanding payments/receipts account.",
                        move.display_name,
                    ))

                if len(counterpart_lines) != 1:
                    raise UserError(_(
                        "Journal Entry %s is not valid. In order to proceed, the journal items must "
                        "include one and only one receivable/payable account (with an exception of "
                        "internal transfers).",
                        move.display_name,
                    ))

                if any(line.currency_id != all_lines[0].currency_id for line in all_lines):
                    raise UserError(_(
                        "Journal Entry %s is not valid. In order to proceed, the journal items must "
                        "share the same currency.",
                        move.display_name,
                    ))

                if any(line.partner_id != all_lines[0].partner_id for line in all_lines):
                    raise UserError(_(
                        "Journal Entry %s is not valid. In order to proceed, the journal items must "
                        "share the same partner.",
                        move.display_name,
                    ))

                if counterpart_lines.account_id.account_type == 'asset_receivable':
                    partner_type = 'customer'
                else:
                    partner_type = 'supplier'

                liquidity_amount = liquidity_lines.amount_currency

                move_vals_to_write.update({
                    'currency_id': liquidity_lines.currency_id.id,
                    'partner_id': liquidity_lines.partner_id.id,
                })
                payment_vals_to_write.update({
                    'amount': abs(liquidity_amount),
                    'partner_type': partner_type,
                    'currency_id': liquidity_lines.currency_id.id,
                    'destination_account_id': counterpart_lines.account_id.id,
                    'partner_id': liquidity_lines.partner_id.id,
                })
                if liquidity_amount > 0.0:
                    payment_vals_to_write.update({'payment_type': 'inbound'})
                elif liquidity_amount < 0.0:
                    payment_vals_to_write.update({'payment_type': 'outbound'})

            move.write(move._cleanup_write_orm_values(move, move_vals_to_write))
            pay.write(move._cleanup_write_orm_values(pay, payment_vals_to_write))

    @api.model
    def _get_trigger_fields_to_synchronize(self):
        return (
            'date', 'amount', 'payment_type', 'partner_type', 'payment_reference', 'is_internal_transfer',
            'currency_id', 'partner_id', 'destination_account_id', 'partner_bank_id', 'journal_id'
        )

    def _synchronize_to_moves(self, changed_fields):
        ''' Update the account.move regarding the modified account.payment.
        :param changed_fields: A list containing all modified fields on account.payment.
        '''
        if self._context.get('skip_account_move_synchronization'):
            return

        if not any(field_name in changed_fields for field_name in self._get_trigger_fields_to_synchronize()):
            return

        for pay in self.with_context(skip_account_move_synchronization=True):
            liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()

            # Make sure to preserve the write-off amount.
            # This allows to create a new payment with custom 'line_ids'.

            write_off_line_vals = []
            if liquidity_lines and counterpart_lines and writeoff_lines:
                write_off_line_vals.append({
                    'name': writeoff_lines[0].name,
                    'account_id': writeoff_lines[0].account_id.id,
                    'partner_id': writeoff_lines[0].partner_id.id,
                    'currency_id': writeoff_lines[0].currency_id.id,
                    'amount_currency': sum(writeoff_lines.mapped('amount_currency')),
                    'balance': sum(writeoff_lines.mapped('balance')),
                })

            line_vals_list = pay._prepare_move_line_default_vals(write_off_line_vals=write_off_line_vals)

            line_ids_commands = [
                Command.update(liquidity_lines.id, line_vals_list[0]) if liquidity_lines else Command.create(line_vals_list[0]),
                Command.update(counterpart_lines.id, line_vals_list[1]) if counterpart_lines else Command.create(line_vals_list[1])
            ]

            for line in writeoff_lines:
                line_ids_commands.append((2, line.id))

            for extra_line_vals in line_vals_list[2:]:
                line_ids_commands.append((0, 0, extra_line_vals))

            # Update the existing journal items.
            # If dealing with multiple write-off lines, they are dropped and a new one is generated.

            pay.move_id\
                .with_context(skip_invoice_sync=True)\
                .write({
                    'partner_id': pay.partner_id.id,
                    'currency_id': pay.currency_id.id,
                    'partner_bank_id': pay.partner_bank_id.id,
                    'line_ids': line_ids_commands,
                })

    def _create_paired_internal_transfer_payment(self):
        ''' When an internal transfer is posted, a paired payment is created
        with opposite payment_type and swapped journal_id & destination_journal_id.
        Both payments liquidity transfer lines are then reconciled.
        '''
        for payment in self:

            paired_payment = payment.copy({
                'journal_id': payment.destination_journal_id.id,
                'destination_journal_id': payment.journal_id.id,
                'payment_type': payment.payment_type == 'outbound' and 'inbound' or 'outbound',
                'move_id': None,
                'ref': payment.ref,
                'paired_internal_transfer_payment_id': payment.id,
                'date': payment.date,
            })
            paired_payment.move_id._post(soft=False)
            payment.paired_internal_transfer_payment_id = paired_payment
            body = _("This payment has been created from:") + payment._get_html_link()
            paired_payment.message_post(body=body)
            body = _("A second payment has been created:") + paired_payment._get_html_link()
            payment.message_post(body=body)

            lines = (payment.move_id.line_ids + paired_payment.move_id.line_ids).filtered(
                lambda l: l.account_id == payment.destination_account_id and not l.reconciled)
            lines.reconcile()

    def _get_payment_receipt_report_values(self):
        """ Get the extra values when rendering the Payment Receipt PDF report.

        :return: A dictionary:
            * display_invoices: Display the invoices table.
            * display_payment_method: Display the payment method value.
        """
        self.ensure_one()
        return {
            'display_invoices': True,
            'display_payment_method': True,
        }

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------

    def mark_as_sent(self):
        self.write({'is_move_sent': True})

    def unmark_as_sent(self):
        self.write({'is_move_sent': False})

    def action_post(self):
        ''' draft -> posted '''
        # Do not allow to post if the account is required but not trusted
        for payment in self:
            if payment.require_partner_bank_account and not payment.partner_bank_id.allow_out_payment:
                raise UserError(_('To record payments with %s, the recipient bank account must be manually validated. You should go on the partner bank account in order to validate it.', self.payment_method_line_id.name))

        self.move_id._post(soft=False)

        self.filtered(
            lambda pay: pay.is_internal_transfer and not pay.paired_internal_transfer_payment_id
        )._create_paired_internal_transfer_payment()

    def action_cancel(self):
        ''' draft -> cancelled '''
        self.move_id.button_cancel()

    def button_request_cancel(self):
        self.move_id.button_request_cancel()

    def action_draft(self):
        ''' posted -> draft '''
        self.move_id.button_draft()

    def button_open_invoices(self):
        ''' Redirect the user to the invoice(s) paid by this payment.
        :return:    An action on account.move.
        '''
        self.ensure_one()

        action = {
            'name': _("Paid Invoices"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'context': {'create': False},
        }
        if len(self.reconciled_invoice_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.reconciled_invoice_ids.id,
            })
        else:
            action.update({
                'view_mode': 'list,form',
                'domain': [('id', 'in', self.reconciled_invoice_ids.ids)],
            })
        return action

    def button_open_bills(self):
        ''' Redirect the user to the bill(s) paid by this payment.
        :return:    An action on account.move.
        '''
        self.ensure_one()

        action = {
            'name': _("Paid Bills"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'context': {'create': False},
        }
        if len(self.reconciled_bill_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.reconciled_bill_ids.id,
            })
        else:
            action.update({
                'view_mode': 'list,form',
                'domain': [('id', 'in', self.reconciled_bill_ids.ids)],
            })
        return action

    def button_open_statement_lines(self):
        ''' Redirect the user to the statement line(s) reconciled to this payment.
        :return:    An action on account.move.
        '''
        self.ensure_one()

        action = {
            'name': _("Matched Transactions"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.bank.statement.line',
            'context': {'create': False},
        }
        if len(self.reconciled_statement_line_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.reconciled_statement_line_ids.id,
            })
        else:
            action.update({
                'view_mode': 'list,form',
                'domain': [('id', 'in', self.reconciled_statement_line_ids.ids)],
            })
        return action

    def button_open_journal_entry(self):
        ''' Redirect the user to this payment journal.
        :return:    An action on account.move.
        '''
        self.ensure_one()
        return {
            'name': _("Journal Entry"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'context': {'create': False},
            'view_mode': 'form',
            'res_id': self.move_id.id,
        }

    def action_open_destination_journal(self):
        ''' Redirect the user to this destination journal.
        :return:    An action on account.move.
        '''
        self.ensure_one()

        action = {
            'name': _("Destination journal"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.journal',
            'context': {'create': False},
            'view_mode': 'form',
            'target': 'new',
            'res_id': self.destination_journal_id.id,
        }
        return action

# For optimization purpose, creating the reverse relation of m2o in _inherits saves
# a lot of SQL queries
class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ['account.move']

    payment_ids = fields.One2many('account.payment', 'move_id', string='Payments')
