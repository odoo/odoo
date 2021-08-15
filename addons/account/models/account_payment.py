# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class AccountPaymentMethod(models.Model):
    _name = "account.payment.method"
    _description = "Payment Methods"
    _order = 'sequence'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True)  # For internal identification
    payment_type = fields.Selection([('inbound', 'Inbound'), ('outbound', 'Outbound')], required=True)
    sequence = fields.Integer(help='Used to order Methods in the form view', default=10)


class AccountPayment(models.Model):
    _name = "account.payment"
    _inherits = {'account.move': 'move_id'}
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Payments"
    _order = "date desc, name desc"
    _check_company_auto = True

    def _get_default_journal(self):
        ''' Retrieve the default journal for the account.payment.
        /!\ This method will not override the method in 'account.move' because the ORM
        doesn't allow overriding methods using _inherits. Then, this method will be called
        manually in 'create' and 'new'.
        :return: An account.journal record.
        '''
        return self.env['account.move']._search_default_journal(('bank', 'cash'))

    # == Business fields ==
    move_id = fields.Many2one(
        comodel_name='account.move',
        string='Journal Entry', required=True, readonly=True, ondelete='cascade',
        check_company=True)

    is_reconciled = fields.Boolean(string="Is Reconciled", store=True,
        compute='_compute_reconciliation_status',
        help="Technical field indicating if the payment is already reconciled.")
    is_matched = fields.Boolean(string="Is Matched With a Bank Statement", store=True,
        compute='_compute_reconciliation_status',
        help="Technical field indicating if the payment has been matched with a statement line.")
    partner_bank_id = fields.Many2one('res.partner.bank', string="Recipient Bank Account",
        readonly=False, store=True,
        compute='_compute_partner_bank_id',
        domain="[('partner_id', '=', partner_id)]",
        check_company=True)
    is_internal_transfer = fields.Boolean(string="Is Internal Transfer",
        readonly=False, store=True,
        compute="_compute_is_internal_transfer")
    qr_code = fields.Char(string="QR Code",
        compute="_compute_qr_code",
        help="QR-code report URL to use to generate the QR-code to scan with a banking app to perform this payment.")

    # == Payment methods fields ==
    payment_method_id = fields.Many2one('account.payment.method', string='Payment Method',
        readonly=False, store=True,
        compute='_compute_payment_method_id',
        domain="[('id', 'in', available_payment_method_ids)]",
        help="Manual: Get paid by cash, check or any other method outside of Odoo.\n"\
        "Electronic: Get paid automatically through a payment acquirer by requesting a transaction on a card saved by the customer when buying or subscribing online (payment token).\n"\
        "Check: Pay bill by check and print it from Odoo.\n"\
        "Batch Deposit: Encase several customer checks at once by generating a batch deposit to submit to your bank. When encoding the bank statement in Odoo, you are suggested to reconcile the transaction with the batch deposit.To enable batch deposit, module account_batch_payment must be installed.\n"\
        "SEPA Credit Transfer: Pay bill from a SEPA Credit Transfer file you submit to your bank. To enable sepa credit transfer, module account_sepa must be installed ")
    available_payment_method_ids = fields.Many2many('account.payment.method',
        compute='_compute_payment_method_fields')
    hide_payment_method = fields.Boolean(
        compute='_compute_payment_method_fields',
        help="Technical field used to hide the payment method if the selected journal has only one available which is 'manual'")

    # == Synchronized fields with the account.move.lines ==
    amount = fields.Monetary(currency_field='currency_id')
    payment_type = fields.Selection([
        ('outbound', 'Send Money'),
        ('inbound', 'Receive Money'),
    ], string='Payment Type', default='inbound', required=True)
    partner_type = fields.Selection([
        ('customer', 'Customer'),
        ('supplier', 'Vendor'),
    ], default='customer', tracking=True, required=True)
    payment_reference = fields.Char(string="Payment Reference", copy=False,
        help="Reference of the document used to issue this payment. Eg. check number, file name, etc.")
    currency_id = fields.Many2one('res.currency', string='Currency', store=True, readonly=False,
        compute='_compute_currency_id',
        help="The payment's currency.")
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string="Customer/Vendor",
        store=True, readonly=False, ondelete='restrict',
        compute='_compute_partner_id',
        domain="['|', ('parent_id','=', False), ('is_company','=', True)]",
        check_company=True)
    destination_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Destination Account',
        store=True, readonly=False,
        compute='_compute_destination_account_id',
        domain="[('user_type_id.type', 'in', ('receivable', 'payable')), ('company_id', '=', company_id)]",
        check_company=True)

    # == Stat buttons ==
    reconciled_invoice_ids = fields.Many2many('account.move', string="Reconciled Invoices",
        compute='_compute_stat_buttons_from_reconciliation',
        help="Invoices whose journal items have been reconciled with these payments.")
    reconciled_invoices_count = fields.Integer(string="# Reconciled Invoices",
        compute="_compute_stat_buttons_from_reconciliation")
    reconciled_bill_ids = fields.Many2many('account.move', string="Reconciled Bills",
        compute='_compute_stat_buttons_from_reconciliation',
        help="Invoices whose journal items have been reconciled with these payments.")
    reconciled_bills_count = fields.Integer(string="# Reconciled Bills",
        compute="_compute_stat_buttons_from_reconciliation")
    reconciled_statement_ids = fields.Many2many('account.bank.statement', string="Reconciled Statements",
        compute='_compute_stat_buttons_from_reconciliation',
        help="Statements matched to this payment")
    reconciled_statements_count = fields.Integer(string="# Reconciled Statements",
        compute="_compute_stat_buttons_from_reconciliation")

    # == Display purpose fields ==
    payment_method_code = fields.Char(
        related='payment_method_id.code',
        help="Technical field used to adapt the interface to the payment type selected.")
    show_partner_bank_account = fields.Boolean(
        compute='_compute_show_require_partner_bank',
        help="Technical field used to know whether the field `partner_bank_id` needs to be displayed or not in the payments form views")
    require_partner_bank_account = fields.Boolean(
        compute='_compute_show_require_partner_bank',
        help="Technical field used to know whether the field `partner_bank_id` needs to be required or not in the payments form views")
    country_code = fields.Char(related='company_id.country_id.code')

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

        for line in self.move_id.line_ids:
            if line.account_id in (
                    self.journal_id.default_account_id,
                    self.journal_id.payment_debit_account_id,
                    self.journal_id.payment_credit_account_id,
            ):
                liquidity_lines += line
            elif line.account_id.internal_type in ('receivable', 'payable') or line.partner_id == line.company_id.partner_id:
                counterpart_lines += line
            else:
                writeoff_lines += line

        return liquidity_lines, counterpart_lines, writeoff_lines

    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        ''' Prepare the dictionary to create the default account.move.lines for the current payment.
        :param write_off_line_vals: Optional dictionary to create a write-off account.move.line easily containing:
            * amount:       The amount to be added to the counterpart amount.
            * name:         The label to set on the line.
            * account_id:   The account on which create the write-off.
        :return: A list of python dictionary to be passed to the account.move.line's 'create' method.
        '''
        self.ensure_one()
        write_off_line_vals = write_off_line_vals or {}

        if not self.journal_id.payment_debit_account_id or not self.journal_id.payment_credit_account_id:
            raise UserError(_(
                "You can't create a new payment without an outstanding payments/receipts account set on the %s journal.",
                self.journal_id.display_name))

        # Compute amounts.
        write_off_amount_currency = write_off_line_vals.get('amount', 0.0)

        if self.payment_type == 'inbound':
            # Receive money.
            liquidity_amount_currency = self.amount
        elif self.payment_type == 'outbound':
            # Send money.
            liquidity_amount_currency = -self.amount
            write_off_amount_currency *= -1
        else:
            liquidity_amount_currency = write_off_amount_currency = 0.0

        write_off_balance = self.currency_id._convert(
            write_off_amount_currency,
            self.company_id.currency_id,
            self.company_id,
            self.date,
        )
        liquidity_balance = self.currency_id._convert(
            liquidity_amount_currency,
            self.company_id.currency_id,
            self.company_id,
            self.date,
        )
        counterpart_amount_currency = -liquidity_amount_currency - write_off_amount_currency
        counterpart_balance = -liquidity_balance - write_off_balance
        currency_id = self.currency_id.id

        if self.is_internal_transfer:
            if self.payment_type == 'inbound':
                liquidity_line_name = _('Transfer to %s', self.journal_id.name)
            else: # payment.payment_type == 'outbound':
                liquidity_line_name = _('Transfer from %s', self.journal_id.name)
        else:
            liquidity_line_name = self.payment_reference

        # Compute a default label to set on the journal items.

        payment_display_name = {
            'outbound-customer': _("Customer Reimbursement"),
            'inbound-customer': _("Customer Payment"),
            'outbound-supplier': _("Vendor Payment"),
            'inbound-supplier': _("Vendor Reimbursement"),
        }

        default_line_name = self.env['account.move.line']._get_default_line_name(
            _("Internal Transfer") if self.is_internal_transfer else payment_display_name['%s-%s' % (self.payment_type, self.partner_type)],
            self.amount,
            self.currency_id,
            self.date,
            partner=self.partner_id,
        )

        line_vals_list = [
            # Liquidity line.
            {
                'name': liquidity_line_name or default_line_name,
                'date_maturity': self.date,
                'amount_currency': liquidity_amount_currency,
                'currency_id': currency_id,
                'debit': liquidity_balance if liquidity_balance > 0.0 else 0.0,
                'credit': -liquidity_balance if liquidity_balance < 0.0 else 0.0,
                'partner_id': self.partner_id.id,
                'account_id': self.journal_id.payment_credit_account_id.id if liquidity_balance < 0.0 else self.journal_id.payment_debit_account_id.id,
            },
            # Receivable / Payable.
            {
                'name': self.payment_reference or default_line_name,
                'date_maturity': self.date,
                'amount_currency': counterpart_amount_currency,
                'currency_id': currency_id,
                'debit': counterpart_balance if counterpart_balance > 0.0 else 0.0,
                'credit': -counterpart_balance if counterpart_balance < 0.0 else 0.0,
                'partner_id': self.partner_id.id,
                'account_id': self.destination_account_id.id,
            },
        ]
        if not self.currency_id.is_zero(write_off_amount_currency):
            # Write-off line.
            line_vals_list.append({
                'name': write_off_line_vals.get('name') or default_line_name,
                'amount_currency': write_off_amount_currency,
                'currency_id': currency_id,
                'debit': write_off_balance if write_off_balance > 0.0 else 0.0,
                'credit': -write_off_balance if write_off_balance < 0.0 else 0.0,
                'partner_id': self.partner_id.id,
                'account_id': write_off_line_vals.get('account_id'),
            })
        return line_vals_list

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
            payment.show_partner_bank_account = payment.payment_method_code in self._get_method_codes_using_bank_account()
            payment.require_partner_bank_account = payment.state == 'draft' and payment.payment_method_code in self._get_method_codes_needing_bank_account()

    @api.depends('partner_id')
    def _compute_partner_bank_id(self):
        ''' The default partner_bank_id will be the first available on the partner. '''
        for pay in self:
            available_partner_bank_accounts = pay.partner_id.bank_ids.filtered(lambda x: x.company_id in (False, pay.company_id))
            if available_partner_bank_accounts:
                if pay.partner_bank_id not in available_partner_bank_accounts:
                    pay.partner_bank_id = available_partner_bank_accounts[0]._origin
            else:
                pay.partner_bank_id = False

    @api.depends('partner_id', 'destination_account_id', 'journal_id')
    def _compute_is_internal_transfer(self):
        for payment in self:
            is_partner_ok = payment.partner_id == payment.journal_id.company_id.partner_id
            is_account_ok = payment.destination_account_id and payment.destination_account_id == payment.journal_id.company_id.transfer_account_id
            payment.is_internal_transfer = is_partner_ok and is_account_ok

    @api.depends('payment_type', 'journal_id')
    def _compute_payment_method_id(self):
        ''' Compute the 'payment_method_id' field.
        This field is not computed in '_compute_payment_method_fields' because it's a stored editable one.
        '''
        for pay in self:
            if pay.payment_type == 'inbound':
                available_payment_methods = pay.journal_id.inbound_payment_method_ids
            else:
                available_payment_methods = pay.journal_id.outbound_payment_method_ids

            # Select the first available one by default.
            if pay.payment_method_id in available_payment_methods:
                pay.payment_method_id = pay.payment_method_id
            elif available_payment_methods:
                pay.payment_method_id = available_payment_methods[0]._origin
            else:
                pay.payment_method_id = False

    @api.depends('payment_type',
                 'journal_id.inbound_payment_method_ids',
                 'journal_id.outbound_payment_method_ids')
    def _compute_payment_method_fields(self):
        for pay in self:
            if pay.payment_type == 'inbound':
                pay.available_payment_method_ids = pay.journal_id.inbound_payment_method_ids
            else:
                pay.available_payment_method_ids = pay.journal_id.outbound_payment_method_ids

            pay.hide_payment_method = len(pay.available_payment_method_ids) == 1 and pay.available_payment_method_ids.code == 'manual'

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

    @api.depends('journal_id', 'partner_id', 'partner_type', 'is_internal_transfer')
    def _compute_destination_account_id(self):
        self.destination_account_id = False
        for pay in self:
            if pay.is_internal_transfer:
                pay.destination_account_id = pay.journal_id.company_id.transfer_account_id
            elif pay.partner_type == 'customer':
                # Receive money from invoice or send money to refund it.
                if pay.partner_id:
                    pay.destination_account_id = pay.partner_id.with_company(pay.company_id).property_account_receivable_id
                else:
                    pay.destination_account_id = self.env['account.account'].search([
                        ('company_id', '=', pay.company_id.id),
                        ('internal_type', '=', 'receivable'),
                        ('deprecated', '=', False),
                    ], limit=1)
            elif pay.partner_type == 'supplier':
                # Send money to pay a bill or receive money to refund it.
                if pay.partner_id:
                    pay.destination_account_id = pay.partner_id.with_company(pay.company_id).property_account_payable_id
                else:
                    pay.destination_account_id = self.env['account.account'].search([
                        ('company_id', '=', pay.company_id.id),
                        ('internal_type', '=', 'payable'),
                        ('deprecated', '=', False),
                    ], limit=1)

    @api.depends('partner_bank_id', 'amount', 'ref', 'currency_id', 'journal_id', 'move_id.state',
                 'payment_method_id', 'payment_type')
    def _compute_qr_code(self):
        for pay in self:
            if pay.state in ('draft', 'posted') \
                and pay.partner_bank_id \
                and pay.payment_method_id.code == 'manual' \
                and pay.payment_type == 'outbound' \
                and pay.currency_id:

                if pay.partner_bank_id:
                    qr_code = pay.partner_bank_id.build_qr_code_url(pay.amount, pay.ref, pay.ref, pay.currency_id, pay.partner_id)
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
            self.reconciled_bill_ids = False
            self.reconciled_bills_count = 0
            self.reconciled_statement_ids = False
            self.reconciled_statements_count = 0
            return

        self.env['account.move'].flush()
        self.env['account.move.line'].flush()
        self.env['account.partial.reconcile'].flush()

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
            WHERE account.internal_type IN ('receivable', 'payable')
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
                ARRAY_AGG(DISTINCT counterpart_line.statement_id) AS statement_ids
            FROM account_payment payment
            JOIN account_move move ON move.id = payment.move_id
            JOIN account_journal journal ON journal.id = move.journal_id
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
            WHERE (account.id = journal.payment_debit_account_id OR account.id = journal.payment_credit_account_id)
                AND payment.id IN %(payment_ids)s
                AND line.id != counterpart_line.id
                AND counterpart_line.statement_id IS NOT NULL
            GROUP BY payment.id
        ''', {
            'payment_ids': tuple(stored_payments.ids)
        })
        query_res = dict((payment_id, statement_ids) for payment_id, statement_ids in self._cr.fetchall())

        for pay in self:
            statement_ids = query_res.get(pay.id, [])
            pay.reconciled_statement_ids = [(6, 0, statement_ids)]
            pay.reconciled_statements_count = len(statement_ids)

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

    @api.constrains('payment_method_id')
    def _check_payment_method_id(self):
        ''' Ensure the 'payment_method_id' field is not null.
        Can't be done using the regular 'required=True' because the field is a computed editable stored one.
        '''
        for pay in self:
            if not pay.payment_method_id:
                raise ValidationError(_("Please define a payment method on your payment."))

    # -------------------------------------------------------------------------
    # LOW-LEVEL METHODS
    # -------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        # OVERRIDE
        write_off_line_vals_list = []

        for vals in vals_list:

            # Hack to add a custom write-off line.
            write_off_line_vals_list.append(vals.pop('write_off_line_vals', None))

            # Force the move_type to avoid inconsistency with residual 'default_move_type' inside the context.
            vals['move_type'] = 'entry'

            # Force the computation of 'journal_id' since this field is set on account.move but must have the
            # bank/cash type.
            if 'journal_id' not in vals:
                vals['journal_id'] = self._get_default_journal().id

            # Since 'currency_id' is a computed editable field, it will be computed later.
            # Prevent the account.move to call the _get_default_currency method that could raise
            # the 'Please define an accounting miscellaneous journal in your company' error.
            if 'currency_id' not in vals:
                journal = self.env['account.journal'].browse(vals['journal_id'])
                vals['currency_id'] = journal.currency_id.id or journal.company_id.currency_id.id

        payments = super().create(vals_list)

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
    def name_get(self):
        return [(payment.id, payment.move_id.name or _('Draft Payment')) for payment in self]

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

                if len(liquidity_lines) != 1 or len(counterpart_lines) != 1:
                    raise UserError(_(
                        "The journal entry %s reached an invalid state relative to its payment.\n"
                        "To be consistent, the journal entry must always contains:\n"
                        "- one journal item involving the outstanding payment/receipts account.\n"
                        "- one journal item involving a receivable/payable account.\n"
                        "- optional journal items, all sharing the same account.\n\n"
                    ) % move.display_name)

                if writeoff_lines and len(writeoff_lines.account_id) != 1:
                    raise UserError(_(
                        "The journal entry %s reached an invalid state relative to its payment.\n"
                        "To be consistent, all the write-off journal items must share the same account."
                    ) % move.display_name)

                if any(line.currency_id != all_lines[0].currency_id for line in all_lines):
                    raise UserError(_(
                        "The journal entry %s reached an invalid state relative to its payment.\n"
                        "To be consistent, the journal items must share the same currency."
                    ) % move.display_name)

                if any(line.partner_id != all_lines[0].partner_id for line in all_lines):
                    raise UserError(_(
                        "The journal entry %s reached an invalid state relative to its payment.\n"
                        "To be consistent, the journal items must share the same partner."
                    ) % move.display_name)

                if counterpart_lines.account_id.user_type_id.type == 'receivable':
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

    def _synchronize_to_moves(self, changed_fields):
        ''' Update the account.move regarding the modified account.payment.
        :param changed_fields: A list containing all modified fields on account.payment.
        '''
        if self._context.get('skip_account_move_synchronization'):
            return

        if not any(field_name in changed_fields for field_name in (
            'date', 'amount', 'payment_type', 'partner_type', 'payment_reference', 'is_internal_transfer',
            'currency_id', 'partner_id', 'destination_account_id', 'partner_bank_id',
        )):
            return

        for pay in self.with_context(skip_account_move_synchronization=True):
            liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()

            # Make sure to preserve the write-off amount.
            # This allows to create a new payment with custom 'line_ids'.

            if writeoff_lines:
                counterpart_amount = sum(counterpart_lines.mapped('amount_currency'))
                writeoff_amount = sum(writeoff_lines.mapped('amount_currency'))

                # To be consistent with the payment_difference made in account.payment.register,
                # 'writeoff_amount' needs to be signed regarding the 'amount' field before the write.
                # Since the write is already done at this point, we need to base the computation on accounting values.
                if (counterpart_amount > 0.0) == (writeoff_amount > 0.0):
                    sign = -1
                else:
                    sign = 1
                writeoff_amount = abs(writeoff_amount) * sign

                write_off_line_vals = {
                    'name': writeoff_lines[0].name,
                    'amount': writeoff_amount,
                    'account_id': writeoff_lines[0].account_id.id,
                }
            else:
                write_off_line_vals = {}

            line_vals_list = pay._prepare_move_line_default_vals(write_off_line_vals=write_off_line_vals)

            line_ids_commands = [
                (1, liquidity_lines.id, line_vals_list[0]),
                (1, counterpart_lines.id, line_vals_list[1]),
            ]

            for line in writeoff_lines:
                line_ids_commands.append((2, line.id))

            for extra_line_vals in line_vals_list[2:]:
                line_ids_commands.append((0, 0, extra_line_vals))

            # Update the existing journal items.
            # If dealing with multiple write-off lines, they are dropped and a new one is generated.

            pay.move_id.write({
                'partner_id': pay.partner_id.id,
                'currency_id': pay.currency_id.id,
                'partner_bank_id': pay.partner_bank_id.id,
                'line_ids': line_ids_commands,
            })

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------

    def mark_as_sent(self):
        self.write({'is_move_sent': True})

    def unmark_as_sent(self):
        self.write({'is_move_sent': False})

    def action_post(self):
        ''' draft -> posted '''
        self.move_id._post(soft=False)

    def action_cancel(self):
        ''' draft -> cancelled '''
        self.move_id.button_cancel()

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

    def button_open_statements(self):
        ''' Redirect the user to the statement line(s) reconciled to this payment.
        :return:    An action on account.move.
        '''
        self.ensure_one()

        action = {
            'name': _("Matched Statements"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.bank.statement',
            'context': {'create': False},
        }
        if len(self.reconciled_statement_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.reconciled_statement_ids.id,
            })
        else:
            action.update({
                'view_mode': 'list,form',
                'domain': [('id', 'in', self.reconciled_statement_ids.ids)],
            })
        return action
