# -*- coding: utf-8 -*-
from odoo import models, fields, api, _, Command
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import format_date, formatLang
from odoo.tools import create_index
from odoo.tools import SQL


class AccountPayment(models.Model):
    _name = "account.payment"
    _inherit = ['mail.thread.main.attachment', 'mail.activity.mixin']
    _description = "Payments"
    _order = "date desc, name desc"
    _check_company_auto = True

    # == Business fields ==
    name = fields.Char(string="Number", compute='_compute_name', store=True)
    date = fields.Date(default=fields.Date.context_today, required=True, tracking=True)
    move_id = fields.Many2one(
        comodel_name='account.move',
        string='Journal Entry',
        index=True,
        copy=False,
        check_company=True)
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        compute='_compute_journal_id', store=True, readonly=False, precompute=True,
        check_company=True,
        index=False,  # covered by account_payment_journal_id_company_id_idx
        required=True,
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        compute='_compute_company_id', store=True, readonly=False, precompute=True,
        index=False,  # covered by account_payment_journal_id_company_id_idx
        required=True
    )
    state = fields.Selection(
        selection=[
            ('draft', "Draft"),
            ('in_process', "In Process"),
            ('paid', "Paid"),
            ('canceled', "Canceled"),
            ('rejected', "Rejected"),
        ],
        required=True,
        default='draft',
        compute='_compute_state', store=True, readonly=False,
        copy=False,
    )
    is_reconciled = fields.Boolean(string="Is Reconciled", store=True,
        compute='_compute_reconciliation_status')
    is_matched = fields.Boolean(string="Is Matched With a Bank Statement", store=True,
        compute='_compute_reconciliation_status')
    is_sent = fields.Boolean(string="Is Sent", readonly=True, copy=False)
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
    qr_code = fields.Html(string="QR Code URL",
        compute="_compute_qr_code")
    paired_internal_transfer_payment_id = fields.Many2one('account.payment',
        index='btree_not_null',
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

    amount = fields.Monetary(currency_field='currency_id')
    payment_type = fields.Selection([
        ('outbound', 'Send'),
        ('inbound', 'Receive'),
    ], string='Payment Type', default='inbound', required=True, tracking=True)
    partner_type = fields.Selection([
        ('customer', 'Customer'),
        ('supplier', 'Vendor'),
    ], default='customer', tracking=True, required=True)
    memo = fields.Char(string="Memo", tracking=True)
    payment_reference = fields.Char(string="Payment Reference", copy=False, tracking=True,
        help="Reference of the document used to issue this payment. Eg. check number, file name, etc.")
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        compute='_compute_currency_id', store=True, readonly=False, precompute=True,
        help="The payment's currency.")
    company_currency_id = fields.Many2one(string="Company Currency", related='company_id.currency_id')
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string="Customer/Vendor",
        store=True, readonly=False, ondelete='restrict',
        compute='_compute_partner_id',
        inverse='_inverse_partner_id',
        domain="['|', ('parent_id','=', False), ('is_company','=', True)]",
        tracking=True,
        check_company=True)
    outstanding_account_id = fields.Many2one(
        comodel_name='account.account',
        string="Outstanding Account",
        store=True,
        index='btree_not_null',
        compute='_compute_outstanding_account_id',
        check_company=True)
    destination_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Destination Account',
        store=True, readonly=False,
        compute='_compute_destination_account_id',
        domain="[('account_type', 'in', ('asset_receivable', 'liability_payable'))]",
        check_company=True)

    # == Stat buttons ==
    invoice_ids = fields.Many2many(  # contains the invoice even if they don't have a journal entry and are not reconciled
        string="Invoices",
        comodel_name='account.move',
        relation='account_move__account_payment',
        column1='payment_id',
        column2='invoice_id',
    )
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
    payment_receipt_title = fields.Char(
        compute='_compute_payment_receipt_title'
    )

    need_cancel_request = fields.Boolean(related='move_id.need_cancel_request')
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
    # used to get and display duplicate move warning if partner, amount and date match existing payments
    duplicate_payment_ids = fields.Many2many(comodel_name='account.payment', compute='_compute_duplicate_payment_ids')
    attachment_ids = fields.One2many('ir.attachment', 'res_id', string='Attachments')

    _sql_constraints = [
        (
            'check_amount_not_negative',
            'CHECK(amount >= 0.0)',
            "The payment amount cannot be negative.",
        ),
    ]

    def init(self):
        super().init()
        create_index(
            self.env.cr,
            indexname='account_payment_journal_id_company_id_idx',
            tablename='account_payment',
            expressions=['journal_id', 'company_id']
        )
        create_index(
            self.env.cr,
            indexname='account_payment_unmatched_idx',
            tablename='account_payment',
            expressions=['journal_id', 'company_id'],
            where="NOT is_matched OR is_matched IS NULL"
        )

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

        # liquidity_lines, counterpart_lines, writeoff_lines
        lines = [self.env['account.move.line'] for _dummy in range(3)]
        valid_account_types = self._get_valid_payment_account_types()
        for line in self.move_id.line_ids:
            if line.account_id in self._get_valid_liquidity_accounts():
                lines[0] += line  # liquidity_lines
            elif line.account_id.account_type in valid_account_types or line.account_id == line.company_id.transfer_account_id:
                lines[1] += line  # counterpart_lines
            else:
                lines[2] += line  # writeoff_lines

        # In some case, there is no liquidity or counterpart line (after changing an outstanding account on the journal for example)
        # In that case, and if there is one writeoff line, we take this line and set it as liquidity/counterpart line
        if len(lines[2]) == 1:
            for i in (0, 1):
                if not lines[i]:
                    lines[i] = lines[2]
                    lines[2] -= lines[2]

        return lines

    def _get_valid_liquidity_accounts(self):
        return (
            self.journal_id.default_account_id |
            self.payment_method_line_id.payment_account_id |
            self.journal_id.inbound_payment_method_line_ids.payment_account_id |
            self.journal_id.outbound_payment_method_line_ids.payment_account_id
        )

    def _get_aml_default_display_name_list(self):
        """ Hook allowing custom values when constructing the default label to set on the journal items.

        :return: A list of terms to concatenate all together. E.g.
            [
                ('label', "Greg's Card"),
                ('sep', ": "),
                ('memo', "New Computer"),
            ]
        """
        self.ensure_one()
        label = self.payment_method_line_id.name if self.payment_method_line_id else _("No Payment Method")

        if self.memo:
            return [
                ('label', label),
                ('sep', ": "),
                ('memo', self.memo),
            ]
        return [
            ('label', label),
        ]

    def _prepare_move_line_default_vals(self, write_off_line_vals=None, force_balance=None):
        ''' Prepare the dictionary to create the default account.move.lines for the current payment.
        :param write_off_line_vals: Optional list of dictionaries to create a write-off account.move.line easily containing:
            * amount:       The amount to be added to the counterpart amount.
            * name:         The label to set on the line.
            * account_id:   The account on which create the write-off.
        :param force_balance: Optional balance.
        :return: A list of python dictionary to be passed to the account.move.line's 'create' method.
        '''
        self.ensure_one()
        write_off_line_vals = write_off_line_vals or []

        if not self.outstanding_account_id:
            raise UserError(_(
                "You can't create a new payment without an outstanding payments/receipts account set either on the company or the %(payment_method)s payment method in the %(journal)s journal.",
                payment_method=self.payment_method_line_id.name, journal=self.journal_id.display_name))

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

        if not write_off_line_vals and force_balance is not None:
            sign = 1 if liquidity_amount_currency > 0 else -1
            liquidity_balance = sign * abs(force_balance)
        else:
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
        liquidity_line_name = ''.join(x[1] for x in self._get_aml_default_display_name_list())
        counterpart_line_name = ''.join(x[1] for x in self._get_aml_default_display_name_list())

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

    @api.depends('move_id.name', 'state')
    def _compute_name(self):
        for payment in self:
            if payment.id and not payment.name and payment.state in ('in_process', 'paid'):
                payment.name = (
                    payment.move_id.name
                    or self.env['ir.sequence'].with_company(payment.company_id).next_by_code(
                        'account.payment',
                        sequence_date=payment.date,
                    )
                )

    @api.depends('company_id')
    def _compute_journal_id(self):
        for payment in self:
            company = self.company_id or self.env.company
            payment.journal_id = self.env['account.journal'].search([
                *self.env['account.journal']._check_company_domain(company),
                ('type', 'in', ['bank', 'cash', 'credit']),
            ], limit=1)

    @api.depends('journal_id')
    def _compute_company_id(self):
        for payment in self:
            if payment.journal_id.company_id not in payment.company_id.parent_ids:
                payment.company_id = (payment.journal_id.company_id or self.env.company)._accessible_branches()[:1]

    @api.depends('invoice_ids.payment_state', 'move_id.line_ids.amount_residual')
    def _compute_state(self):
        for payment in self:
            if not payment.state:
                payment.state = 'draft'
            # in_process --> paid
            if payment.state == 'in_process' and payment.outstanding_account_id:
                move = payment.move_id
                liquidity, _counterpart, _writeoff = payment._seek_for_lines()
                if move and move.currency_id.is_zero(sum(liquidity.mapped('amount_residual'))):
                    payment.state = 'paid'
                    continue
            if payment.state == 'in_process' and payment.invoice_ids and all(invoice.payment_state == 'paid' for invoice in payment.invoice_ids):
                payment.state = 'paid'

    @api.depends('move_id.line_ids.amount_residual', 'move_id.line_ids.amount_residual_currency', 'move_id.line_ids.account_id', 'state')
    def _compute_reconciliation_status(self):
        ''' Compute the field indicating if the payments are already reconciled with something.
        This field is used for display purpose (e.g. display the 'reconcile' button redirecting to the reconciliation
        widget).
        '''
        for pay in self:
            liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()

            if not pay.outstanding_account_id:
                pay.is_reconciled = False
                pay.is_matched = pay.state == 'paid'
            elif not pay.currency_id or not pay.id or not pay.move_id:
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

    def action_open_business_doc(self):
        return {
            'name': _("Payment"),
            'type': 'ir.actions.act_window',
            'views': [(False, 'form')],
            'res_model': 'account.payment',
            'res_id': self.id,
        }

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

    @api.depends('move_id.amount_total_signed', 'amount', 'payment_type', 'currency_id', 'date', 'company_id', 'company_currency_id')
    def _compute_amount_company_currency_signed(self):
        for payment in self:
            if payment.move_id:
                liquidity_lines = payment._seek_for_lines()[0]
                payment.amount_company_currency_signed = sum(liquidity_lines.mapped('balance'))
            else:
                payment.amount_company_currency_signed = payment.currency_id._convert(
                    from_amount=payment.amount,
                    to_currency=payment.company_currency_id,
                    company=payment.company_id,
                    date=payment.date,
                )

    @api.depends('amount', 'payment_type')
    def _compute_amount_signed(self):
        for payment in self:
            if payment.payment_type == 'outbound':
                payment.amount_signed = -payment.amount
            else:
                payment.amount_signed = payment.amount

    @api.depends('partner_id', 'company_id', 'payment_type')
    def _compute_available_partner_bank_ids(self):
        for pay in self:
            if pay.payment_type == 'inbound':
                pay.available_partner_bank_ids = pay.journal_id.bank_account_id
            else:
                pay.available_partner_bank_ids = pay.partner_id.bank_ids\
                        .filtered(lambda x: x.company_id.id in (False, pay.company_id.id))._origin

    @api.depends('available_partner_bank_ids', 'journal_id')
    def _compute_partner_bank_id(self):
        ''' The default partner_bank_id will be the first available on the partner. '''
        for pay in self:
            if pay.partner_bank_id not in pay.available_partner_bank_ids:
                pay.partner_bank_id = pay.available_partner_bank_ids[:1]._origin

    @api.depends('available_payment_method_line_ids')
    def _compute_payment_method_line_id(self):
        ''' Compute the 'payment_method_line_id' field.
        This field is not computed in '_compute_payment_method_line_fields' because it's a stored editable one.
        '''
        for pay in self:
            available_payment_method_lines = pay.available_payment_method_line_ids
            inbound_payment_method = pay.partner_id.property_inbound_payment_method_line_id
            outbound_payment_method = pay.partner_id.property_outbound_payment_method_line_id
            if pay.payment_type == 'inbound' and inbound_payment_method.id in available_payment_method_lines.ids:
                pay.payment_method_line_id = inbound_payment_method
            elif pay.payment_type == 'outbound' and outbound_payment_method.id in available_payment_method_lines.ids:
                pay.payment_method_line_id = outbound_payment_method
            elif pay.payment_method_line_id.id in available_payment_method_lines.ids:
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
            ('type', 'in', ('bank', 'cash', 'credit')),
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

    @api.depends('journal_id')
    def _compute_partner_id(self):
        for pay in self:
            if pay.partner_id == pay.journal_id.company_id.partner_id:
                pay.partner_id = False
            else:
                pay.partner_id = pay.partner_id

    @api.depends('payment_method_line_id')
    def _compute_outstanding_account_id(self):
        for pay in self:
            pay.outstanding_account_id = pay.payment_method_line_id.payment_account_id

    @api.depends('journal_id', 'partner_id', 'partner_type')
    def _compute_destination_account_id(self):
        self.destination_account_id = False
        for pay in self:
            if pay.partner_type == 'customer':
                # Receive money from invoice or send money to refund it.
                if pay.partner_id:
                    pay.destination_account_id = pay.partner_id.with_company(pay.company_id).property_account_receivable_id
                else:
                    pay.destination_account_id = self.env['account.account'].with_company(pay.company_id).search([
                        *self.env['account.account']._check_company_domain(pay.company_id),
                        ('account_type', '=', 'asset_receivable'),
                        ('deprecated', '=', False),
                    ], limit=1)
            elif pay.partner_type == 'supplier':
                # Send money to pay a bill or receive money to refund it.
                if pay.partner_id:
                    pay.destination_account_id = pay.partner_id.with_company(pay.company_id).property_account_payable_id
                else:
                    pay.destination_account_id = self.env['account.account'].with_company(pay.company_id).search([
                        *self.env['account.account']._check_company_domain(pay.company_id),
                        ('account_type', '=', 'liability_payable'),
                        ('deprecated', '=', False),
                    ], limit=1)

    @api.depends('partner_bank_id', 'amount', 'memo', 'currency_id', 'journal_id', 'move_id.state',
                 'payment_method_line_id', 'payment_type')
    def _compute_qr_code(self):
        for pay in self:
            if pay.state in ('draft', 'in_process') \
                and pay.partner_bank_id \
                and pay.partner_bank_id.allow_out_payment \
                and pay.payment_method_line_id.code == 'manual' \
                and pay.payment_type == 'outbound' \
                and pay.currency_id:

                if pay.partner_bank_id:
                    qr_code = pay.partner_bank_id.build_qr_code_base64(pay.amount, pay.memo, pay.memo, pay.currency_id, pay.partner_id)
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
            self.reconciled_invoices_type = False
            self.reconciled_bill_ids = False
            self.reconciled_bills_count = 0
            self.reconciled_statement_line_ids = False
            self.reconciled_statement_lines_count = 0
            return

        self.env['account.payment'].flush_model(fnames=['move_id', 'outstanding_account_id'])
        self.env['account.move'].flush_model(fnames=['move_type', 'origin_payment_id', 'statement_line_id'])
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

        for pay in self:
            pay.reconciled_invoice_ids = pay.invoice_ids.filtered(lambda m: m.is_sale_document(True))
            pay.reconciled_bill_ids = pay.invoice_ids.filtered(lambda m: m.is_purchase_document(True))

        for res in query_res:
            pay = self.browse(res['id'])
            if res['move_type'] in self.env['account.move'].get_sale_types(True):
                pay.reconciled_invoice_ids |= self.env['account.move'].browse(res.get('invoice_ids', []))
            else:
                pay.reconciled_bill_ids |= self.env['account.move'].browse(res.get('invoice_ids', []))

        for pay in self:
            pay.reconciled_invoices_count = len(pay.reconciled_invoice_ids)
            pay.reconciled_bills_count = len(pay.reconciled_bill_ids)

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

    def _compute_payment_receipt_title(self):
        """ To override in order to change the title displayed on the payment receipt report """
        self.payment_receipt_title = _('Payment Receipt')

    @api.depends('partner_id', 'amount', 'date', 'payment_type')
    def _compute_duplicate_payment_ids(self):
        """ Retrieve move ids with same partner_id, amount and date as the current payment """
        payment_to_duplicate_move = self._fetch_duplicate_reference()
        for payment in self:
            # Uses payment._origin.id to handle records in edition/existing records and 0 for new records
            payment.duplicate_payment_ids = payment_to_duplicate_move.get(payment._origin.id, self.env['account.payment'])

    def _fetch_duplicate_reference(self, matching_states=('draft', 'in_process')):
        """ Retrieve move ids for possible duplicates of payments. Duplicates moves:
        - Have the same partner_id, amount and date as the payment
        - Are not reconciled
        - Represent a credit in the same account receivable or a debit in the same account payable as the payment, or
        - Represent a credit in outstanding receipts or debit in outstanding payments, so bank statement lines with an
         outstanding counterpart can be matched, or
        - Are in the suspense account
        """
        # Does not perform unnecessary check if partner_id or amount are not set, nor if payment is posted
        payments = self.filtered(lambda p: p.partner_id and p.amount and p.state != 'in_process')
        if not payments:
            return {}

        # Update tables involved in the query
        used_fields = ("company_id", "partner_id", "date", "state", "amount", 'payment_type')
        self.flush_model(used_fields)

        payment_table_and_alias = SQL("account_payment AS payment")
        if not self[0].id:  # if record is under creation/edition in UI, safely inject values in the query
            # Necessary since new record aren't searchable in the DB and record in edition aren't up to date yet
            values = {
                field_name: self._fields[field_name].convert_to_write(self[field_name], self) or None
                for field_name in used_fields
            }
            values["id"] = self._origin.id or 0
            # The amount total depends on the field line_ids and is calculated upon saving, we needed a way to get it even when the
            # invoices has not been saved yet.
            casted_values = SQL(', ').join(
                SQL("%s::%s", value, SQL.identifier(self._fields[field_name].column_type[0]))
                for field_name, value in values.items()
            )
            column_names = SQL(', ').join(SQL.identifier(field_name) for field_name in values)
            payment_table_and_alias = SQL("(VALUES (%s)) AS payment(%s)", casted_values, column_names)

        query = SQL(
            """
                SELECT payment.id AS payment_id,
                       ARRAY_AGG(DISTINCT duplicate_payment.id) AS duplicate_payment_ids
                  FROM %(payment_table_and_alias)s
                  JOIN account_payment AS duplicate_payment ON payment.id != duplicate_payment.id
                                                           AND payment.partner_id = duplicate_payment.partner_id
                                                           AND payment.company_id = duplicate_payment.company_id
                                                           AND payment.date = duplicate_payment.date
                                                           AND payment.payment_type = duplicate_payment.payment_type
                                                           AND payment.amount = duplicate_payment.amount
                                                           AND duplicate_payment.state IN %(matching_states)s
                 WHERE payment.id = ANY(%(payments)s)
              GROUP BY payment.id
            """,
            payment_table_and_alias=payment_table_and_alias,
            matching_states=tuple(matching_states),
            payments=payments.ids or [0],
        )

        return {
            payment_id: self.env['account.payment'].browse(duplicate_ids)
            for payment_id, duplicate_ids in self.env.execute_query(query)
        }

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------

    @api.onchange('partner_id')
    def _inverse_partner_id(self):
        """
            The goal of this inverse is that when changing the partner, the payment method line is recomputed, and it can
            happen that the journal that was set doesn't have that particular payment method line, so we have to change
            the journal otherwise the user will have an UserError.
        """
        for payment in self:
            partner = payment.partner_id
            payment_type = payment.payment_type if payment.payment_type in ('inbound', 'outbound') else None
            if not partner or not payment_type:
                continue

            field_name = f'property_{payment_type}_payment_method_line_id'
            default_payment_method_line = payment.partner_id.with_company(payment.company_id)[field_name]
            journal = default_payment_method_line.journal_id
            if journal:
                payment.journal_id = journal

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
            elif pay.payment_method_line_id.journal_id and pay.payment_method_line_id.journal_id != pay.journal_id:
                raise ValidationError(_("The selected payment method is not available for this payment, please select the payment method again."))

    @api.constrains('state', 'move_id')
    def _check_move_id(self):
        for payment in self:
            if (
                payment.state not in ('draft', 'canceled')
                and not payment.move_id
                and payment.outstanding_account_id
            ):
                raise ValidationError(_("A payment with an outstanding account cannot be confirmed without having a journal entry."))

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        # OVERRIDE
        write_off_line_vals_list = []
        force_balance_vals_list = []
        linecomplete_line_vals_list = []

        for vals in vals_list:

            # Hack to add a custom write-off line.
            write_off_line_vals_list.append(vals.pop('write_off_line_vals', None))

            # Hack to force a custom balance.
            force_balance_vals_list.append(vals.pop('force_balance', None))

            # Hack to add a custom line.
            linecomplete_line_vals_list.append(vals.pop('line_ids', None))

        payments = super().create(vals_list)

        # Outstanding account should be set on the payment in community edition to force the generation of journal entries on the payment
        # This is required because no reconciliation is possible in community, which would prevent the user to reconcile the bank statement with the invoice
        accounting_installed = self.env['account.move']._get_invoice_in_payment_state() == 'in_payment'

        for i, (pay, vals) in enumerate(zip(payments, vals_list)):
            if not accounting_installed and not pay.outstanding_account_id:
                outstanding_account = pay._get_outstanding_account(pay.payment_type)
                pay.outstanding_account_id = outstanding_account.id

            if (
                write_off_line_vals_list[i] is not None
                or force_balance_vals_list[i] is not None
                or linecomplete_line_vals_list[i] is not None
            ):
                pay._generate_journal_entry(
                    write_off_line_vals=write_off_line_vals_list[i],
                    force_balance=force_balance_vals_list[i],
                    line_ids=linecomplete_line_vals_list[i],
                )
                # propagate the related fields to the move as it is being created after the payment
                if move_vals := {
                    fname: value
                    for fname, value in vals.items()
                    if self._fields[fname].related and (self._fields[fname].related or '').split('.')[0] == 'move_id'
                }:
                    pay.move_id.write(move_vals)
        return payments

    def _get_outstanding_account(self, payment_type):
        account_ref = 'account_journal_payment_debit_account_id' if payment_type == 'inbound' else 'account_journal_payment_credit_account_id'
        chart_template = self.with_context(allowed_company_ids=self.company_id.root_id.ids).env['account.chart.template']
        outstanding_account = (
            chart_template.ref(account_ref, raise_if_not_found=False)
            or self.company_id.transfer_account_id
        )
        if not outstanding_account:
            raise UserError(_("No outstanding account could be found to make the payment"))
        return outstanding_account

    def write(self, vals):
        if vals.get('state') in ('in_process', 'paid') and not vals.get('move_id'):
            self.filtered(lambda p: not p.move_id)._generate_journal_entry()
            self.move_id.action_post()

        res = super().write(vals)
        if self.move_id:
            self._synchronize_to_moves(set(vals.keys()))
        return res

    def unlink(self):
        self.move_id.filtered(lambda m: m.state != 'draft').button_draft()
        self.move_id.unlink()

        linked_invoices = self.invoice_ids
        res = super().unlink()
        self.env.add_to_compute(linked_invoices._fields['payment_state'], linked_invoices)
        return res

    @api.depends('move_id.name')
    def _compute_display_name(self):
        for payment in self:
            payment.display_name = payment.name or _('Draft Payment')

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default)
        for payment, vals in zip(self, vals_list):
            vals.update({
                'journal_id': payment.journal_id.id,
                'payment_method_line_id': payment.payment_method_line_id.id,
                **(vals or {}),
            })
        return vals_list

    # -------------------------------------------------------------------------
    # SYNCHRONIZATION account.payment -> account.move
    # -------------------------------------------------------------------------

    def _synchronize_to_moves(self, changed_fields):
        '''
            Update the account.move regarding the modified account.payment.
            :param changed_fields: A list containing all modified fields on account.payment.
        '''
        if not any(field_name in changed_fields for field_name in self._get_trigger_fields_to_synchronize()):
            return

        for pay in self:
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
            pay.move_id \
                .with_context(skip_invoice_sync=True) \
                .write({
                'partner_id': pay.partner_id.id,
                'currency_id': pay.currency_id.id,
                'partner_bank_id': pay.partner_bank_id.id,
                'line_ids': line_ids_commands,
            })

    @api.model
    def _get_trigger_fields_to_synchronize(self):
        return (
            'date', 'amount', 'payment_type', 'partner_type', 'payment_reference',
            'currency_id', 'partner_id', 'destination_account_id', 'partner_bank_id', 'journal_id'
        )

    def _generate_journal_entry(self, write_off_line_vals=None, force_balance=None, line_ids=None):
        need_move = self.filtered(lambda p: not p.move_id and p.outstanding_account_id)
        assert len(self) == 1 or (not write_off_line_vals and not force_balance and not line_ids)

        move_vals = []
        for pay in need_move:
            move_vals.append({
                'move_type': 'entry',
                'ref': pay.memo,
                'date': pay.date,
                'journal_id': pay.journal_id.id,
                'company_id': pay.company_id.id,
                'partner_id': pay.partner_id.id,
                'currency_id': pay.currency_id.id,
                'partner_bank_id': pay.partner_bank_id.id,
                'line_ids': line_ids or [
                    Command.create(line_vals)
                    for line_vals in pay._prepare_move_line_default_vals(
                        write_off_line_vals=write_off_line_vals,
                        force_balance=force_balance,
                    )
                ],
                'origin_payment_id': pay.id,
            })
        moves = self.env['account.move'].create(move_vals)
        for pay, move in zip(need_move, moves):
            pay.write({'move_id': move.id, 'state': 'in_process'})

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
        self.write({'is_sent': True})

    def unmark_as_sent(self):
        self.write({'is_sent': False})

    def action_post(self):
        ''' draft -> posted '''
        # Do not allow posting if the account is required but not trusted
        for payment in self:
            if payment.require_partner_bank_account and not payment.partner_bank_id.allow_out_payment:
                raise UserError(_(
                    "To record payments with %(method_name)s, the recipient bank account must be manually validated. "
                    "You should go on the partner bank account of %(partner)s in order to validate it.",
                    method_name=self.payment_method_line_id.name,
                    partner=payment.partner_id.display_name,
                ))
        self.filtered(lambda pay: pay.outstanding_account_id.account_type == 'asset_cash').state = 'paid'
        # Avoid going back one state when clicking on the confirm action in the payment list view and having paid expenses selected
        # We need to set values to each payment to avoid recomputation later
        self.filtered(lambda pay: pay.state in {False, 'draft', 'in_process'}).state = 'in_process'

    def action_validate(self):
        self.state = 'paid'

    def action_reject(self):
        self.state = 'rejected'

    def action_cancel(self):
        self.state = 'canceled'
        draft_moves = self.move_id.filtered(lambda m: m.state == 'draft')
        draft_moves.unlink()
        (self.move_id - draft_moves).button_cancel()

    def button_request_cancel(self):
        return self.move_id.button_request_cancel()

    def action_draft(self):
        self.state = 'draft'
        self.move_id.button_draft()

    def button_open_invoices(self):
        ''' Redirect the user to the invoice(s) paid by this payment.
        :return:    An action on account.move.
        '''
        self.ensure_one()
        return (self.invoice_ids | self.reconciled_invoice_ids).with_context(
            create=False
        )._get_records_action(
            name=_("Paid Invoices"),
        )

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


# For optimization purpose, creating the reverse relation of m2o in _inherits saves
# a lot of SQL queries
class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ['account.move']

    payment_ids = fields.One2many('account.payment', 'move_id', string='Payments')
