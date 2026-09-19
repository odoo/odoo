from collections import defaultdict
from itertools import zip_longest

from odoo import Command, _, api, fields, models
from odoo.exceptions import MissingError, UserError, ValidationError
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL

_debug = DebugLog(__name__)

_SQL_RECONCILED_INVOICES_PER_PAYMENT = """
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
    WHERE account.account_type = ANY(%(account_types)s)
        AND payment.id = ANY(%(payment_ids)s)
        AND line.id != counterpart_line.id
        AND invoice.move_type = ANY(%(move_types)s)
    GROUP BY payment.id, invoice.move_type
"""

_SQL_RECONCILED_STATEMENT_LINES_PER_PAYMENT = """
    SELECT
        payment.id,
        ARRAY_AGG(DISTINCT counterpart_move.statement_line_id) AS statement_line_ids
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
    JOIN account_move counterpart_move ON counterpart_move.id = counterpart_line.move_id
    WHERE account.id = payment.outstanding_account_id
        AND payment.id = ANY(%(payment_ids)s)
        AND line.id != counterpart_line.id
        AND counterpart_move.statement_line_id IS NOT NULL
    GROUP BY payment.id
"""

_SEEK_FOR_LINES_DEPENDS = (
    "move_id.line_ids.account_id",
    "outstanding_account_id",
    "payment_channel_id.payment_account_id",
    "journal_id.default_account_id",
    "journal_id.inbound_payment_channel_ids.payment_account_id",
    "journal_id.outbound_payment_channel_ids.payment_account_id",
    "company_id.account_config_id.transfer_account_id",
)


class AccountPayment(models.Model):
    _name = "account.payment"
    _inherit = [
        "mixin.mail.thread.main.attachment",
        "mixin.mail.activity",
        "mixin.payment.qr.code",
    ]
    _description = "Payments"
    _order = "date desc, name desc"
    _check_company_auto = True

    name = fields.Char(
        string="Number",
        compute="_compute_name",
        store=True,
    )
    date = fields.Date(
        default=fields.Date.context_today,
        required=True,
        tracking=True,
    )
    move_id = fields.Many2one(
        comodel_name="account.move",
        string="Journal Entry",
        index=True,
        copy=False,
        check_company=True,
    )
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        compute="_compute_journal_id",
        precompute=True,
        store=True,
        index=False,
        readonly=False,
        required=True,
        check_company=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        compute="_compute_company_id",
        precompute=True,
        store=True,
        index=False,
        readonly=False,
        required=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("in_process", "In Process"),
            ("paid", "Paid"),
            ("canceled", "Canceled"),
            ("rejected", "Rejected"),
        ],
        compute="_compute_state",
        default="draft",
        store=True,
        copy=False,
        readonly=False,
        required=True,
        tracking=True,
    )
    is_invoice_reconciled = fields.Boolean(
        string="Is Reconciled",
        compute="_compute_reconciliation_status",
        store=True,
    )
    is_bank_matched = fields.Boolean(
        string="Is Matched With a Bank Statement",
        compute="_compute_reconciliation_status",
        store=True,
    )
    is_sent = fields.Boolean(
        copy=False,
        readonly=True,
    )
    available_partner_bank_ids = fields.Many2many(
        comodel_name="res.partner.bank",
        compute="_compute_available_partner_bank_ids",
    )
    partner_bank_id = fields.Many2one(
        comodel_name="res.partner.bank",
        string="Recipient Bank Account",
        compute="_compute_partner_bank_id",
        store=True,
        readonly=False,
        domain="[('id', 'in', available_partner_bank_ids)]",
        ondelete="restrict",
        check_company=True,
        tracking=True,
    )
    qr_code = fields.Html(
        string="QR Code URL",
        compute="_compute_qr_code",
    )
    paired_internal_transfer_payment_id = fields.Many2one(
        comodel_name="account.payment",
        index="btree_not_null",
        copy=False,
        help="When an internal transfer is posted, a paired payment is created. "
        "They are cross referenced through this field",
    )

    payment_channel_id = fields.Many2one(
        comodel_name="account.payment.channel",
        string="Payment Method",
        compute="_compute_payment_channel_id",
        store=True,
        copy=False,
        readonly=False,
        domain="[('id', 'in', available_payment_channel_ids)]",
        help="Manual: Pay or Get paid by any method outside of Odoo.\n"
        "Payment Providers: Each payment provider has its own Payment Method. Request a transaction on/to a card thanks to a payment token saved by the partner when buying or subscribing online.\n"
        "Check: Pay bills by check and print it from Odoo.\n"
        "Batch Deposit: Collect several customer checks at once generating and submitting a batch deposit to your bank. Module account_batch_payment is necessary.\n"
        "SEPA Credit Transfer: Pay in the SEPA zone by submitting a SEPA Credit Transfer file to your bank. Module account_iso20022 is necessary.\n"
        "SEPA Direct Debit: Get paid in the SEPA zone thanks to a mandate your partner will have granted to you. Module account_iso20022 is necessary.\n"
        "U.S. ISO20022: Pay in the US by submitting an ISO20022 file to your bank. Module account_iso20022 is necessary.\n",
    )
    available_payment_channel_ids = fields.Many2many(
        comodel_name="account.payment.channel",
        compute="_compute_available_payment_channel_ids",
    )
    payment_method_id = fields.Many2one(
        related="payment_channel_id.payment_method_id",
        string="Method",
        tracking=True,
    )
    available_journal_ids = fields.Many2many(
        comodel_name="account.journal",
        compute="_compute_available_journal_ids",
    )

    amount = fields.Monetary(currency_field="currency_id")
    payment_type = fields.Selection(
        selection=[
            ("outbound", "Send"),
            ("inbound", "Receive"),
        ],
        default="inbound",
        required=True,
        tracking=True,
    )
    partner_type = fields.Selection(
        selection=[
            ("customer", "Customer"),
            ("supplier", "Vendor"),
        ],
        default="customer",
        required=True,
        tracking=True,
    )
    memo = fields.Char(
        inverse="_inverse_memo",
        tracking=True,
    )
    payment_reference = fields.Char(
        copy=False,
        tracking=True,
        help="Reference of the document used to issue this payment. Eg. check number, file name, etc.",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        compute="_compute_currency_id",
        precompute=True,
        store=True,
        readonly=False,
        help="The payment's currency.",
    )
    company_currency_id = fields.Many2one(
        related="company_id.currency_id",
        string="Company Currency",
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Customer/Vendor",
        domain="['|', ('parent_id','=', False), ('is_company','=', True)]",
        ondelete="restrict",
        check_company=True,
        tracking=True,
    )
    outstanding_account_id = fields.Many2one(
        comodel_name="account.account",
        compute="_compute_outstanding_account_id",
        store=True,
        index="btree_not_null",
        check_company=True,
    )
    destination_account_id = fields.Many2one(
        comodel_name="account.account",
        compute="_compute_destination_account_id",
        store=True,
        readonly=False,
        domain="[('account_type', 'in', ('asset_receivable', 'liability_payable'))]",
        check_company=True,
    )

    invoice_ids = fields.Many2many(
        comodel_name="account.move",
        relation="account_move__account_payment",
        column1="payment_id",
        column2="invoice_id",
        string="Invoices",
        copy=False,
    )
    reconciled_invoice_ids = fields.Many2many(
        comodel_name="account.move",
        string="Reconciled Invoices",
        compute="_compute_stat_buttons_from_reconciliation",
        search="_search_reconciled_invoice_ids",
        help="Invoices whose journal items have been reconciled with these payments.",
    )
    reconciled_invoices_count = fields.Count(
        count_of="reconciled_invoice_ids",
        string="# Reconciled Invoices",
    )

    reconciled_invoices_type = fields.Selection(
        selection=[("credit_note", "Credit Note"), ("invoice", "Invoice")],
        compute="_compute_stat_buttons_from_reconciliation",
    )
    reconciled_bill_ids = fields.Many2many(
        comodel_name="account.move",
        string="Reconciled Bills",
        compute="_compute_stat_buttons_from_reconciliation",
        search="_search_reconciled_bill_ids",
        help="Bills whose journal items have been reconciled with these payments.",
    )
    reconciled_bills_count = fields.Count(
        count_of="reconciled_bill_ids",
        string="# Reconciled Bills",
    )
    reconciled_statement_line_ids = fields.Many2many(
        comodel_name="account.bank.statement.line",
        string="Reconciled Statement Lines",
        compute="_compute_stat_buttons_from_reconciliation",
        help="Statements lines matched to this payment",
    )
    reconciled_statement_lines_count = fields.Count(
        count_of="reconciled_statement_line_ids",
        string="# Reconciled Statement Lines",
    )

    payment_method_code = fields.Char(related="payment_channel_id.code")
    payment_receipt_title = fields.Char(compute="_compute_payment_receipt_title")

    need_cancel_request = fields.Boolean(related="move_id.need_cancel_request")
    show_partner_bank_account = fields.Boolean(
        compute="_compute_show_require_partner_bank"
    )
    require_partner_bank_account = fields.Boolean(
        compute="_compute_show_require_partner_bank"
    )
    country_code = fields.Char(
        related="company_id.account_config_id.account_fiscal_country_id.code"
    )
    amount_signed = fields.Monetary(
        currency_field="currency_id",
        compute="_compute_amount_signed",
        tracking=True,
        help="Negative value of amount field if payment_type is outbound",
    )
    amount_company_currency_signed = fields.Monetary(
        currency_field="company_currency_id",
        compute="_compute_amount_company_currency_signed",
        store=True,
    )
    duplicate_payment_ids = fields.Many2many(
        comodel_name="account.payment",
        compute="_compute_duplicate_payment_ids",
    )
    attachment_ids = fields.One2many(
        comodel_name="ir.attachment",
        inverse_name="res_id",
        string="Attachments",
    )

    _check_amount_not_negative = models.Constraint(
        "CHECK(amount >= 0.0)",
        "The payment amount cannot be negative.",
    )
    _journal_id_company_id_idx = models.Index("(journal_id, company_id)")
    _unmatched_idx = models.Index(
        "(journal_id, company_id) WHERE is_bank_matched IS NOT TRUE"
    )

    @api.model
    def _get_valid_payment_account_types(self):
        return ["asset_receivable", "liability_payable"]

    def _seek_for_lines(self):
        self.check_singleton()

        empty = self.env["account.move.line"]
        liquidity_ids, counterpart_ids, other_ids = [], [], []
        valid_account_types = self._get_valid_payment_account_types()
        liquidity_accounts = self._get_valid_liquidity_accounts()
        for line in self.move_id.line_ids:
            if line.account_id in liquidity_accounts:
                liquidity_ids.append(line.id)
            elif (
                line.account_id.account_type in valid_account_types
                or line.account_id
                == line.company_id.account_config_id.transfer_account_id
            ):
                counterpart_ids.append(line.id)
            else:
                other_ids.append(line.id)

        liquidity = empty.browse(liquidity_ids)
        counterpart = empty.browse(counterpart_ids)
        other = empty.browse(other_ids)

        if len(other) == 1:
            if not liquidity:
                _debug.logic("lone_other_line_as_liquidity", payment=self)
                liquidity, other = other, empty
            elif not counterpart:
                _debug.logic("lone_other_line_as_counterpart", payment=self)
                counterpart, other = other, empty

        return [liquidity, counterpart, other]

    def _get_valid_liquidity_accounts(self):
        self.check_singleton()
        return (
            self.journal_id.default_account_id
            | self.payment_channel_id.payment_account_id
            | self.journal_id.inbound_payment_channel_ids.payment_account_id
            | self.journal_id.outbound_payment_channel_ids.payment_account_id
            | self.outstanding_account_id
        )

    def _valid_payment_states(self):
        if self.env["account.move"]._has_full_accounting():
            return ["in_process"]
        return ["in_process", "paid"]

    def _get_aml_default_display_name_list(self):
        self.check_singleton()
        label = (
            self.payment_channel_id.name
            if self.payment_channel_id
            else _("No Payment Method")
        )

        if self.memo:
            return [
                ("label", label),
                ("sep", ": "),
                ("memo", self.memo),
            ]
        return [
            ("label", label),
        ]

    @_debug.perf.timed
    def _prepare_move_withholding_lines(self, default_values):
        self.check_singleton()
        return []

    @_debug.perf.timed
    def _prepare_move_liquidity_lines(self, default_values):
        self.check_singleton()
        return [
            {
                "name": default_values["name"],
                "date_maturity": self.date,
                "partner_id": self.partner_id.id,
                "account_id": self.outstanding_account_id.id,
                "currency_id": self.currency_id.id,
                "balance": default_values["balance"],
                "amount_currency": default_values["amount_currency"],
            }
        ]

    @_debug.perf.timed
    def _prepare_move_counterpart_lines(self, default_values):
        self.check_singleton()
        return [
            {
                "name": default_values["name"],
                "date_maturity": self.date,
                "partner_id": self.partner_id.id,
                "account_id": self.destination_account_id.id,
                "currency_id": self.currency_id.id,
                "balance": default_values["balance"],
                "amount_currency": default_values["amount_currency"],
            }
        ]

    @_debug.perf.timed
    def _prepare_move_lines_per_type(
        self, write_off_line_vals=None, force_balance=None
    ):
        self.check_singleton()

        if force_balance is not None and write_off_line_vals:
            raise ValueError(
                "force_balance sets the liquidity balance outright and cannot be "
                "combined with write_off_line_vals, which derive it."
            )

        if not self.outstanding_account_id:
            raise UserError(
                _(
                    "You can't create a new payment without an outstanding payments/receipts account set either on the company or the %(payment_method)s payment method in the %(journal)s journal.",
                    payment_method=self.payment_channel_id.name,
                    journal=self.journal_id.display_name,
                )
            )

        line_name = "".join(
            x[1] for x in self._get_aml_default_display_name_list() if x[1]
        )

        write_off_lines = write_off_line_vals or []
        write_off_amount_currency = sum(x["amount_currency"] for x in write_off_lines)
        write_off_balance = sum(x["balance"] for x in write_off_lines)

        sign = -1 if self.payment_type == "outbound" else 1
        liquidity_amount_currency = sign * self.amount

        withholding_lines = self._prepare_move_withholding_lines(
            {"name": line_name, "amount_currency": liquidity_amount_currency}
        )
        withholding_amount_currency = sum(
            x["amount_currency"] for x in withholding_lines
        )
        withholding_balance = sum(x["balance"] for x in withholding_lines)

        if force_balance is not None:
            liquidity_balance = sign * abs(force_balance)
        else:
            liquidity_balance = self.currency_id._convert(
                liquidity_amount_currency,
                self.company_id.currency_id,
                self.company_id,
                self.date,
            )
        liquidity_amount_currency -= withholding_amount_currency
        liquidity_balance -= withholding_balance

        liquidity_lines = self._prepare_move_liquidity_lines(
            {
                "name": line_name,
                "balance": liquidity_balance,
                "amount_currency": liquidity_amount_currency,
            }
        )

        counterpart_amount_currency = (
            -liquidity_amount_currency
            - write_off_amount_currency
            - withholding_amount_currency
        )
        counterpart_balance = (
            -liquidity_balance - write_off_balance - withholding_balance
        )
        counterpart_lines = self._prepare_move_counterpart_lines(
            {
                "name": line_name,
                "balance": counterpart_balance,
                "amount_currency": counterpart_amount_currency,
            }
        )

        _debug.pipeline(
            "payment_lines_prepared",
            payment=self,
            forced_balance=force_balance is not None,
            liquidity=len(liquidity_lines),
            counterpart=len(counterpart_lines),
            write_off=len(write_off_lines),
            withholding=len(withholding_lines),
            liquidity_balance=liquidity_balance,
            counterpart_balance=counterpart_balance,
        )
        return {
            "liquidity_lines": liquidity_lines,
            "counterpart_lines": counterpart_lines,
            "write_off_lines": write_off_lines,
            "withholding_lines": withholding_lines,
        }

    @_debug.perf.timed
    def _prepare_move_line_default_vals(
        self, write_off_line_vals=None, force_balance=None
    ):
        self.check_singleton()

        line_vals_per_type = self._prepare_move_lines_per_type(
            write_off_line_vals=write_off_line_vals, force_balance=force_balance
        )
        line_vals = []
        for sub_line_vals in line_vals_per_type.values():
            line_vals += sub_line_vals
        return line_vals

    @api.depends("move_id.name", "state", "company_id", "date")
    def _compute_name(self):
        for payment in self:
            if not payment.id or payment.state not in ("in_process", "paid"):
                continue
            if payment.name and (
                not payment.move_id or payment.name == payment.move_id.name
            ):
                continue
            payment.name = payment.move_id.name or self.env["ir.sequence"].with_company(
                payment.company_id
            ).next_by_code("account.payment", sequence_date=payment.date)

    @api.depends("company_id", "partner_id", "payment_type")
    @_debug.perf.timed
    def _compute_journal_id(self):
        default_journal_by_company = {}
        for payment in self:
            partner = payment.partner_id
            payment_type = (
                payment.payment_type
                if payment.payment_type in ("inbound", "outbound")
                else None
            )
            if not payment._origin and partner and payment_type:
                field_name = f"property_{payment_type}_payment_channel_id"
                default_payment_channel = payment.partner_id.with_company(
                    payment.company_id
                )[field_name]
                journal = default_payment_channel.journal_id
                if journal:
                    payment.journal_id = journal
                    continue

            company = payment.company_id or self.env.company
            if not payment.journal_id or company != payment.journal_id.company_id:
                if company not in default_journal_by_company:
                    default_journal_by_company[company] = self._get_default_journal(
                        company
                    )
                payment.journal_id = default_journal_by_company[company]
        _debug.logic(
            "journal_defaults_resolved",
            payment=self,
            companies_defaulted=len(default_journal_by_company),
        )

    def _get_default_journal(self, company):
        return self.env["account.journal"].search(
            [
                *self.env["account.journal"]._check_company_domain(company),
                ("type", "in", ["bank", "cash", "credit"]),
            ],
            limit=1,
        )

    @api.depends("journal_id")
    def _compute_company_id(self):
        for payment in self:
            if payment.journal_id.company_id not in payment.company_id.parent_ids:
                payment.company_id = (
                    payment.journal_id.company_id or self.env.company
                )._get_accessible_branches()[:1]

    @api.depends(
        "reconciled_invoice_ids.payment_state",
        "reconciled_bill_ids.payment_state",
        "move_id.line_ids.amount_residual",
        "move_id.line_ids.account_id.reconcile",
        *_SEEK_FOR_LINES_DEPENDS,
    )
    @_debug.perf.timed
    def _compute_state(self):
        for payment in self:
            if not payment.state:
                payment.state = "draft"
            if (move := payment.move_id) and payment.state in ("paid", "in_process"):
                liquidity, _counterpart, _writeoff = payment._seek_for_lines()
                payment.state = (
                    "paid"
                    if move.company_currency_id.is_zero(
                        sum(liquidity.mapped("amount_residual"))
                    )
                    or not any(liquidity.account_id.mapped("reconcile"))
                    else "in_process"
                )
            if (
                payment.state == "in_process"
                and (
                    moves := (
                        payment.reconciled_invoice_ids | payment.reconciled_bill_ids
                    )
                )
                and all(invoice.payment_state == "paid" for invoice in moves)
            ):
                _debug.logic("all_reconciled_invoices_paid_paid", payment=payment)
                payment.state = "paid"
            _debug.logic(
                "_compute_state",
                payment=payment,
                state=payment.state,
                move=payment.move_id,
            )

    @api.depends(
        "move_id.line_ids.amount_residual",
        "move_id.line_ids.amount_residual_currency",
        "state",
        "amount",
        "currency_id",
        "company_id.currency_id",
        *_SEEK_FOR_LINES_DEPENDS,
    )
    @_debug.perf.timed
    def _compute_reconciliation_status(self):
        for pay in self:
            liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()

            if not pay.outstanding_account_id:
                pay.is_invoice_reconciled = False
                pay.is_bank_matched = pay.state == "paid"
            elif not pay.currency_id or not pay.id or not pay.move_id:
                pay.is_invoice_reconciled = False
                pay.is_bank_matched = False
            elif pay.currency_id.is_zero(pay.amount):
                pay.is_invoice_reconciled = True
                pay.is_bank_matched = True
            else:
                residual_field = (
                    "amount_residual"
                    if pay.currency_id == pay.company_id.currency_id
                    else "amount_residual_currency"
                )
                if (
                    pay.journal_id.default_account_id
                    and pay.journal_id.default_account_id in liquidity_lines.account_id
                ):
                    pay.is_bank_matched = True
                else:
                    pay.is_bank_matched = pay.currency_id.is_zero(
                        sum(liquidity_lines.mapped(residual_field))
                    )

                reconcile_lines = (counterpart_lines + writeoff_lines).filtered(
                    lambda line: line.account_id.reconcile
                )
                pay.is_invoice_reconciled = pay.currency_id.is_zero(
                    sum(reconcile_lines.mapped(residual_field))
                )
        if _debug.logic.enabled:
            _debug.logic(
                "reconciliation_status_computed",
                payment=self,
                invoice_reconciled=len(self.filtered("is_invoice_reconciled")),
                bank_matched=len(self.filtered("is_bank_matched")),
            )

    @api.model
    def _get_method_codes_using_bank_account(self):
        return ["manual"]

    @api.model
    def _get_method_codes_needing_bank_account(self):
        return []

    @_debug.perf.timed
    def action_view_business_doc(self):
        _debug.lifecycle("action_view_business_doc", records=self)
        return {
            "name": _("Payment"),
            "type": "ir.actions.act_window",
            "views": [(False, "form")],
            "res_model": "account.payment",
            "res_id": self.id,
        }

    @api.depends("payment_method_code", "journal_id.type", "state")
    def _compute_show_require_partner_bank(self):
        for payment in self:
            if payment.journal_id.type == "cash":
                payment.show_partner_bank_account = False
            else:
                payment.show_partner_bank_account = (
                    payment.payment_method_code
                    in self._get_method_codes_using_bank_account()
                )
            payment.require_partner_bank_account = (
                payment.state == "draft"
                and payment.payment_method_code
                in self._get_method_codes_needing_bank_account()
            )

    @api.depends(
        "move_id.line_ids.balance",
        "amount",
        "payment_type",
        "currency_id",
        "date",
        "company_id",
        "company_currency_id",
        *_SEEK_FOR_LINES_DEPENDS,
    )
    def _compute_amount_company_currency_signed(self):
        for payment in self:
            if payment.move_id:
                liquidity_lines = payment._seek_for_lines()[0]
                payment.amount_company_currency_signed = sum(
                    liquidity_lines.mapped("balance")
                )
            else:
                payment.amount_company_currency_signed = payment.currency_id._convert(
                    from_amount=payment.amount_signed,
                    to_currency=payment.company_currency_id,
                    company=payment.company_id,
                    date=payment.date,
                )

    @api.depends("amount", "payment_type")
    def _compute_amount_signed(self):
        for payment in self:
            if payment.payment_type == "outbound":
                payment.amount_signed = -payment.amount
            else:
                payment.amount_signed = payment.amount

    @api.depends(
        "partner_id", "company_id", "payment_type", "journal_id.bank_account_id"
    )
    def _compute_available_partner_bank_ids(self):
        for pay in self:
            if pay.payment_type == "inbound":
                pay.available_partner_bank_ids = pay.journal_id.bank_account_id
            else:
                pay.available_partner_bank_ids = pay.partner_id.bank_ids.filtered(
                    lambda x, pay=pay: x.company_id.id in (False, pay.company_id.id)
                )._origin

    @api.depends("available_partner_bank_ids", "journal_id")
    def _compute_partner_bank_id(self):
        for pay in self:
            if pay.partner_bank_id not in pay.available_partner_bank_ids:
                pay.partner_bank_id = pay.available_partner_bank_ids[:1]._origin

    @api.depends("available_payment_channel_ids", "partner_id", "company_id")
    @_debug.perf.timed
    def _compute_payment_channel_id(self):
        for pay in self:
            available = pay.available_payment_channel_ids
            available_ids = set(available.ids)
            partner = pay.partner_id.with_company(pay.company_id)
            preferred = self.env["account.payment.channel"]
            if pay.payment_type in ("inbound", "outbound"):
                preferred = partner[f"property_{pay.payment_type}_payment_channel_id"]
            if preferred.id in available_ids:
                pay.payment_channel_id = preferred
            elif pay.payment_channel_id.id in available_ids:
                continue
            elif available:
                pay.payment_channel_id = available[0]._origin
            else:
                pay.payment_channel_id = False
        if _debug.logic.enabled:
            _debug.logic(
                "payment_channels_resolved",
                payment=self,
                channels=self.mapped("payment_channel_id"),
            )

    @api.depends("payment_type", "journal_id", "currency_id")
    def _compute_available_payment_channel_ids(self):
        for pay in self:
            channels = pay.journal_id._get_available_payment_channels(pay.payment_type)
            if to_exclude := pay._get_payment_method_codes_to_exclude():
                channels = channels.filtered(
                    lambda x, to_exclude=to_exclude: x.code not in to_exclude
                )
            pay.available_payment_channel_ids = channels

    def _get_available_journals(self, company):
        return self.env["account.journal"].search(
            [
                "|",
                ("company_id", "parent_of", company.id),
                ("company_id", "child_of", company.id),
                ("type", "in", ("bank", "cash", "credit")),
            ]
        )

    @api.depends("payment_type", "company_id")
    def _compute_available_journal_ids(self):
        journals_per_company = {}
        for pay in self:
            company = pay.company_id or self.env.company
            if company not in journals_per_company:
                journals_per_company[company] = self._get_available_journals(company)
            method_lines = (
                "inbound_payment_channel_ids"
                if pay.payment_type == "inbound"
                else "outbound_payment_channel_ids"
            )
            pay.available_journal_ids = journals_per_company[company].filtered(
                method_lines
            )

    def _get_payment_method_codes_to_exclude(self):
        self.check_singleton()
        return []

    @api.depends("journal_id.currency_id", "company_id.currency_id")
    def _compute_currency_id(self):
        for pay in self:
            pay.currency_id = pay.journal_id.currency_id or pay.company_id.currency_id

    def _outstanding_account_is_mandatory(self):
        return (
            bool(self.env.context.get("force_payment_move"))
            or not self.env["account.move"]._has_full_accounting()
        )

    @api.depends("payment_channel_id", "payment_type", "company_id")
    def _compute_outstanding_account_id(self):
        mandatory = self._outstanding_account_is_mandatory()
        fallback = {}
        for pay in self:
            account = pay.payment_channel_id.payment_account_id
            if not account and mandatory:
                key = (pay.company_id, pay.payment_type)
                if key not in fallback:
                    fallback[key] = pay._get_outstanding_account(pay.payment_type)
                account = fallback[key]
            if not account and pay.move_id:
                _debug.logic("outstanding_account_kept_no_channel", payment=pay)
                continue
            _debug.logic(
                "outstanding",
                payment=pay,
                account=account,
                channel=pay.payment_channel_id,
                mandatory=mandatory,
            )
            pay.outstanding_account_id = account

    @api.depends("journal_id", "partner_id", "partner_type")
    @_debug.perf.timed
    def _compute_destination_account_id(self):
        self.destination_account_id = False
        fallback_account = {}

        def _fallback(company, account_type):
            key = (company, account_type)
            if key not in fallback_account:
                fallback_account[key] = (
                    self.env["account.account"]
                    .with_company(company)
                    .search(
                        [
                            *self.env["account.account"]._check_company_domain(company),
                            ("account_type", "=", account_type),
                        ],
                        limit=1,
                    )
                )
            return fallback_account[key]

        account_by_partner_type = {
            "customer": ("property_account_receivable_id", "asset_receivable"),
            "supplier": ("property_account_payable_id", "liability_payable"),
        }
        for pay in self:
            if pay.partner_type not in account_by_partner_type:
                continue
            property_name, account_type = account_by_partner_type[pay.partner_type]
            pay.destination_account_id = (
                pay.partner_id.with_company(pay.company_id)[property_name]
                if pay.partner_id
                else _fallback(pay.company_id, account_type)
            )
            _debug.logic(
                "destination_account",
                payment=pay,
                account=pay.destination_account_id,
                source=property_name if pay.partner_id else f"fallback {account_type}",
            )

    @api.depends(
        "partner_bank_id",
        "amount",
        "memo",
        "currency_id",
        "journal_id",
        "move_id.state",
        "payment_channel_id",
        "payment_type",
        "state",
    )
    def _compute_qr_code(self):
        for pay in self:
            pay.qr_code = (
                pay._render_payment_qr_code(pay.amount, pay.memo)
                if pay.state in ("draft", "in_process")
                else False
            )

    def _get_reconciled_invoices_per_payment(self, stored_payments):
        return self.env.execute_query(
            SQL(
                _SQL_RECONCILED_INVOICES_PER_PAYMENT,
                payment_ids=stored_payments.ids,
                account_types=self._get_valid_payment_account_types(),
                move_types=list(
                    self.env["account.move"].get_sale_types(True)
                    + self.env["account.move"].get_purchase_types(True)
                ),
            )
        )

    def _get_reconciled_statement_lines_per_payment(self, stored_payments):
        return dict(
            self.env.execute_query(
                SQL(
                    _SQL_RECONCILED_STATEMENT_LINES_PER_PAYMENT,
                    payment_ids=stored_payments.ids,
                )
            )
        )

    @api.depends(
        "move_id.line_ids.matched_debit_ids",
        "move_id.line_ids.matched_credit_ids",
        "invoice_ids",
    )
    @_debug.perf.timed
    def _compute_stat_buttons_from_reconciliation(self):
        stored_payments = self.filtered("id")
        _debug.logic(
            "stat_buttons_scope",
            payment=self,
            stored=len(stored_payments),
            skipped=not stored_payments,
        )
        if not stored_payments:
            self.reconciled_invoice_ids = False
            self.reconciled_invoices_type = False
            self.reconciled_bill_ids = False
            self.reconciled_statement_line_ids = False
            return

        self.env["account.payment"].flush_model(
            fnames=["move_id", "outstanding_account_id"]
        )
        self.env["account.move"].flush_model(fnames=["move_type", "statement_line_id"])
        self.env["account.move.line"].flush_model(
            fnames=["move_id", "account_id", "statement_line_id"]
        )
        self.env["account.partial.reconcile"].flush_model(
            fnames=["debit_move_id", "credit_move_id"]
        )

        invoices_per_payment = self._get_reconciled_invoices_per_payment(
            stored_payments
        )
        _debug.perf.count("reconciled_invoices_fetched", rows=len(invoices_per_payment))

        query_res = self._get_reconciled_statement_lines_per_payment(stored_payments)
        _debug.perf.count("reconciled_statement_lines_fetched", rows=len(query_res))
        sale_types = self.env["account.move"].get_sale_types(True)

        invoices_by_payment = defaultdict(list)
        bills_by_payment = defaultdict(list)
        for payment_id, invoice_ids, move_type in invoices_per_payment:
            target = (
                invoices_by_payment if move_type in sale_types else bills_by_payment
            )
            target[payment_id].extend(invoice_ids)

        _debug.pipeline(
            "reconciled_documents_grouped",
            payment=stored_payments,
            with_invoices=len(invoices_by_payment),
            with_bills=len(bills_by_payment),
            with_statement_lines=len(query_res),
        )
        for pay in self:
            invoices = pay.invoice_ids.filtered(lambda m: m.is_sale_document(True))
            bills = pay.invoice_ids.filtered(lambda m: m.is_purchase_document(True))
            invoices |= self.env["account.move"].browse(
                invoices_by_payment.get(pay.id, ())
            )
            bills |= self.env["account.move"].browse(bills_by_payment.get(pay.id, ()))

            pay.reconciled_invoice_ids = invoices
            pay.reconciled_bill_ids = bills
            pay.reconciled_statement_line_ids = [Command.set(query_res.get(pay.id, []))]
            pay.reconciled_invoices_type = (
                "credit_note"
                if set(invoices.mapped("move_type")) == {"out_refund"}
                else "invoice"
            )

    def _compute_payment_receipt_title(self):
        self.payment_receipt_title = _("Payment Receipt")

    @api.depends(
        "partner_id",
        "amount",
        "date",
        "payment_type",
        "company_id",
        "currency_id",
        "state",
    )
    def _compute_duplicate_payment_ids(self):
        payment_to_duplicate_move = self._get_duplicate_reference()
        _debug.perf.count(
            "duplicate_payments_fetched", rows=len(payment_to_duplicate_move)
        )
        for payment in self:
            payment.duplicate_payment_ids = payment_to_duplicate_move.get(
                payment._origin.id, self.env["account.payment"]
            )

    @_debug.perf.timed
    def _search_reconciled_move_ids(self, operator, value, move_filter=None):
        if operator not in ("in", "="):
            return NotImplemented

        def payment_ids(moves):
            if move_filter is not None:
                moves = moves.filtered(move_filter)
            return moves.reconciled_payment_ids.ids

        moves = self.env["account.move"].browse(value)
        try:
            ids = payment_ids(moves)
        except MissingError:
            ids = payment_ids(moves.exists())
        return [("id", "in", ids)]

    @_debug.perf.timed
    def _search_reconciled_invoice_ids(self, operator, value):
        return self._search_reconciled_move_ids(
            operator, value, lambda move: move.is_sale_document(True)
        )

    @_debug.perf.timed
    def _search_reconciled_bill_ids(self, operator, value):
        return self._search_reconciled_move_ids(
            operator, value, lambda move: move.is_purchase_document(True)
        )

    @_debug.perf.timed
    def _get_duplicate_reference(self, matching_states=("draft", "in_process")):
        payments = self.filtered(
            lambda p: p.partner_id and p.amount and p.state != "in_process"
        )
        _debug.pipeline(
            "duplicate_candidates_filtered",
            payment=self,
            candidates=len(payments),
            unsaved=not self.ids,
            matching_states=matching_states,
        )
        if not payments:
            return {}

        matched_fields = (
            "company_id",
            "partner_id",
            "date",
            "amount",
            "payment_type",
            "currency_id",
        )
        self.flush_model((*matched_fields, "state"))

        payment_table_and_alias = SQL("account_payment AS payment")
        if not self.ids:
            self.check_singleton()
            values = {
                field_name: self._fields[field_name].convert_to_write(
                    self[field_name], self
                )
                or None
                for field_name in matched_fields
            }
            values["id"] = self._origin.id or 0
            casted_values = SQL(", ").join(
                SQL(
                    "%s::%s",
                    value,
                    SQL.identifier(self._fields[field_name].column_type[0]),
                )
                for field_name, value in values.items()
            )
            column_names = SQL(", ").join(
                SQL.identifier(field_name) for field_name in values
            )
            payment_table_and_alias = SQL(
                "(VALUES (%s)) AS payment(%s)", casted_values, column_names
            )

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
                                                           AND payment.currency_id = duplicate_payment.currency_id
                                                           AND duplicate_payment.state IN %(matching_states)s
                 WHERE payment.id = ANY(%(payments)s)
              GROUP BY payment.id
            """,
            payment_table_and_alias=payment_table_and_alias,
            matching_states=tuple(matching_states),
            payments=payments.ids or [0],
        )

        return {
            payment_id: self.env["account.payment"].browse(duplicate_ids)
            for payment_id, duplicate_ids in self.env.execute_query(query)
        }

    def _inverse_memo(self):
        for payment in self:
            payment.move_id.ref = payment.memo

    @api.constrains("payment_channel_id")
    @_debug.perf.timed
    def _check_payment_channel_id(self):
        for pay in self:
            if not pay.payment_channel_id:
                raise ValidationError(
                    _("Please define a payment method line on your payment.")
                )
            if (
                pay.payment_channel_id.journal_id
                and pay.payment_channel_id.journal_id != pay.journal_id
            ):
                raise ValidationError(
                    _(
                        "The selected payment method is not available for this payment, please select the payment method again."
                    )
                )

    @api.constrains("state", "move_id")
    @_debug.perf.timed
    def _check_move_id(self):
        for payment in self:
            if (
                payment.state not in ("draft", "canceled")
                and not payment.move_id
                and (
                    payment.outstanding_account_id
                    or payment._outstanding_account_is_mandatory()
                )
            ):
                raise ValidationError(
                    _(
                        "A payment with an outstanding account cannot be confirmed without having a journal entry."
                    )
                )

    @api.model_create_multi
    @_debug.perf.timed
    def create(self, vals_list):
        if _debug.lifecycle.enabled:
            _debug.lifecycle(
                "create",
                model=self._name,
                count=len(vals_list),
                fields=sorted({key for vals in vals_list for key in vals}),
            )
        entry_vals_list = [
            (
                vals.pop("write_off_line_vals", None),
                vals.pop("force_balance", None),
                vals.pop("line_ids", None),
            )
            for vals in vals_list
        ]

        payments = super().create(vals_list)

        for pay, vals, (write_off_line_vals, force_balance, line_ids) in zip(
            payments, vals_list, entry_vals_list, strict=True
        ):
            if (
                write_off_line_vals is None
                and force_balance is None
                and line_ids is None
            ):
                continue
            _debug.pipeline(
                "create_journal_entry_explicit_vals",
                payment=pay,
                write_off=write_off_line_vals is not None,
                force_balance=force_balance is not None,
                line_ids=line_ids is not None,
            )
            pay._create_journal_entry(
                write_off_line_vals=write_off_line_vals,
                force_balance=force_balance,
                line_ids=line_ids,
            )
            if move_vals := pay._move_vals_from_related(vals):
                pay.move_id.write(move_vals)
        return payments

    def _move_vals_from_related(self, vals):
        return {
            fname: value
            for fname, value in vals.items()
            if (self._fields[fname].related or "").split(".")[0] == "move_id"
        }

    def _get_outstanding_account(self, payment_type):
        account_ref = (
            "account_journal_payment_debit_account_id"
            if payment_type == "inbound"
            else "account_journal_payment_credit_account_id"
        )
        chart_template = self.with_context(
            allowed_company_ids=self.company_id.root_id.ids
        ).env["account.chart.template"]
        outstanding_account = (
            chart_template.ref(account_ref, raise_if_not_found=False)
            or self.company_id.account_config_id.transfer_account_id
        )
        if not outstanding_account:
            raise UserError(
                _("No outstanding account could be found to make the payment")
            )
        return outstanding_account

    @_debug.perf.timed
    def write(self, vals):
        _debug.lifecycle("write", records=self, fields=sorted(vals))
        if _debug.lifecycle.enabled and "state" in vals:
            _debug.lifecycle(
                "state_change",
                payment=self,
                state=set(self.mapped("state")),
                state_to=vals["state"],
            )
        if vals.get("state") in ("in_process", "paid") and not vals.get("move_id"):
            self.filtered(lambda p: not p.move_id)._create_journal_entry()
            draft_moves = self.move_id.filtered(lambda m: m.state == "draft")
            _debug.pipeline("posting_moves", payment=self, draft_moves=draft_moves)
            draft_moves.action_post()

        res = super().write(vals)
        if self.move_id:
            self._sync_to_moves(set(vals.keys()))
        return res

    @_debug.perf.timed
    def unlink(self):
        _debug.lifecycle("unlink", unlink=self)
        moves = self.move_id
        res = super().unlink()
        moves.filtered(lambda m: m.state != "draft").action_draft()
        moves.unlink()
        return res

    @api.depends("name")
    def _compute_display_name(self):
        for payment in self:
            payment.display_name = payment.name or _("Draft Payment")

    @_debug.perf.timed
    def copy_data(self, default=None):
        _debug.lifecycle("copy_data", records=self)
        vals_list = super().copy_data(dict(default or {}))
        for payment, vals in zip(self, vals_list, strict=True):
            vals.setdefault("payment_channel_id", payment.payment_channel_id.id)
        return vals_list

    def _message_mail_after_hook(self, mails):
        for payment, mail in zip(self, mails, strict=False):
            if not payment.message_main_attachment_id and (
                attachments_to_link := mail.attachment_ids.filtered(
                    lambda a: a.res_model == "mail.message"
                )
            ):
                attachments_to_link.write(
                    {"res_model": self._name, "res_id": payment.id}
                )
        return super()._message_mail_after_hook(mails)

    @api.model
    @_debug.perf.timed
    def _prepare_line_commands(self, lines, line_vals):
        commands = []
        for line, vals in zip_longest(lines, line_vals):
            if line is not None and vals is not None:
                commands.append(Command.update(line.id, vals))
            elif vals is not None:
                commands.append(Command.create(vals))
            else:
                commands.append(Command.delete(line.id))
        return commands

    @_debug.perf.timed
    def _sync_to_moves(self, changed_fields):
        if not any(
            field_name in changed_fields
            for field_name in self._get_trigger_fields_to_synchronize()
        ):
            return

        for pay in self:
            if pay.move_id.state == "posted":
                _debug.logic("_sync_to_moves_move_posted_not_synced", payment=pay)
                continue
            liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()
            if _debug.pipeline.enabled:
                _debug.pipeline(
                    "_sync_to_moves",
                    payment=pay,
                    fields=sorted(changed_fields),
                    liquidity=liquidity_lines,
                    counterpart=counterpart_lines,
                    writeoff=writeoff_lines,
                )

            if "amount" in changed_fields and len(liquidity_lines) > 1:
                raise UserError(
                    _(
                        "You cannot change the amount of a payment with multiple liquidity lines."
                    )
                )

            write_off_line_vals = []
            if liquidity_lines and counterpart_lines and writeoff_lines:
                write_off_line_vals.append(
                    {
                        "name": writeoff_lines[0].name,
                        "account_id": writeoff_lines[0].account_id.id,
                        "partner_id": writeoff_lines[0].partner_id.id,
                        "currency_id": writeoff_lines[0].currency_id.id,
                        "amount_currency": sum(
                            writeoff_lines.mapped("amount_currency")
                        ),
                        "balance": sum(writeoff_lines.mapped("balance")),
                    }
                )
            line_vals_per_type = pay._prepare_move_lines_per_type(
                write_off_line_vals=write_off_line_vals
            )
            line_ids_commands = [
                *self._prepare_line_commands(
                    liquidity_lines, line_vals_per_type.get("liquidity_lines", [])
                ),
                *self._prepare_line_commands(
                    counterpart_lines, line_vals_per_type.get("counterpart_lines", [])
                ),
                *(Command.delete(line.id) for line in writeoff_lines),
                *(
                    Command.create(extra_line_vals)
                    for extra_line_vals in line_vals_per_type.get("write_off_lines", [])
                    + line_vals_per_type.get("withholding_lines", [])
                ),
            ]
            to_write = {
                "date": pay.date,
                "partner_id": pay.partner_id.id,
                "currency_id": pay.currency_id.id,
                "partner_bank_id": pay.partner_bank_id.id,
                "line_ids": line_ids_commands,
            }
            if "journal_id" in changed_fields:
                to_write.update(
                    {
                        "name": "/",
                        "journal_id": pay.journal_id.id,
                    }
                )
            pay.move_id.with_context(skip_invoice_sync=True).write(to_write)

    @api.model
    def _get_trigger_fields_to_synchronize(self):
        return (
            "date",
            "amount",
            "payment_type",
            "partner_type",
            "memo",
            "payment_channel_id",
            "currency_id",
            "partner_id",
            "destination_account_id",
            "partner_bank_id",
            "journal_id",
        )

    @_debug.perf.timed
    def _create_journal_entry(
        self, write_off_line_vals=None, force_balance=None, line_ids=None
    ):
        if len(self) > 1 and (write_off_line_vals or force_balance or line_ids):
            raise ValueError(
                "write_off_line_vals, force_balance and line_ids describe one "
                "entry and cannot be applied to a recordset."
            )
        need_move = self.filtered(lambda p: not p.move_id and p.outstanding_account_id)

        move_vals = [
            pay._generate_move_vals(write_off_line_vals, force_balance, line_ids)
            for pay in need_move
        ]
        moves = self.env["account.move"].with_context(is_payment=True).create(move_vals)
        _debug.pipeline(
            "_create_journal_entry",
            payment=need_move,
            moves=moves,
            skipped=self - need_move,
        )
        for pay, move in zip(need_move, moves, strict=True):
            pay.write({"move_id": move.id, "state": "in_process"})

    @_debug.perf.timed
    def _generate_move_vals(
        self, write_off_line_vals=None, force_balance=None, line_ids=None
    ):
        self.check_singleton()
        return {
            "move_type": "entry",
            "ref": self.memo,
            "date": self.date,
            "journal_id": self.journal_id.id,
            "company_id": self.company_id.id,
            "partner_id": self.partner_id.id,
            "currency_id": self.currency_id.id,
            "partner_bank_id": self.partner_bank_id.id,
            "line_ids": line_ids
            or [
                Command.create(line_vals)
                for line_vals in self._prepare_move_line_default_vals(
                    write_off_line_vals=write_off_line_vals,
                    force_balance=force_balance,
                )
            ],
        }

    def _prepare_payment_receipt_report_values(self):
        self.check_singleton()
        return {
            "display_invoices": True,
            "display_payment_method": True,
        }

    def mark_as_sent(self):
        self.write({"is_sent": True})

    def unmark_as_sent(self):
        self.write({"is_sent": False})

    @_debug.perf.timed
    def action_post(self):
        _debug.lifecycle("action_post", records=self)
        for payment in self:
            if (
                payment.require_partner_bank_account
                and not payment.partner_bank_id.allow_out_payment
                and payment.payment_type == "outbound"
            ):
                raise UserError(
                    _(
                        "To record payments with %(method_name)s, the recipient bank account must be manually validated. "
                        "You should go on the partner bank account of %(partner)s in order to validate it.",
                        method_name=payment.payment_channel_id.name,
                        partner=payment.partner_id.display_name,
                    )
                )
        cash_payments = self.filtered(
            lambda pay: pay.outstanding_account_id.account_type == "asset_cash"
        )
        _debug.logic(
            "action_post_cash_payments_straight_paid", cash_payments=cash_payments
        )
        cash_payments.state = "paid"
        self.filtered(
            lambda pay: pay.state in {False, "draft", "in_process"}
        ).state = "in_process"

    @_debug.perf.timed
    def action_validate(self):
        _debug.lifecycle("action_validate", records=self)
        self.state = "paid"

    @_debug.perf.timed
    def action_reject(self):
        _debug.lifecycle("action_reject", records=self)
        self.state = "rejected"

    @_debug.perf.timed
    def action_cancel(self):
        _debug.lifecycle("action_cancel", records=self)
        moves = self.move_id
        draft_moves = moves.filtered(lambda m: m.state == "draft")
        self.state = "canceled"
        (moves - draft_moves).action_cancel()
        draft_moves.unlink()

    @_debug.perf.timed
    def button_request_cancel(self):
        _debug.lifecycle("button_request_cancel", records=self)
        return self.move_id.button_request_cancel()

    @_debug.perf.timed
    def action_draft(self):
        _debug.lifecycle("action_draft", records=self)
        self.state = "draft"
        self.move_id.action_draft()

    @_debug.perf.timed
    def button_open_invoices(self):
        _debug.lifecycle("button_open_invoices", records=self)
        self.check_singleton()
        return self.reconciled_invoice_ids.with_context(
            create=False
        )._get_records_action(
            name=_("Paid Invoices"),
        )

    @_debug.perf.timed
    def button_open_bills(self):
        _debug.lifecycle("button_open_bills", records=self)
        self.check_singleton()
        return self.reconciled_bill_ids.with_context(create=False)._get_records_action(
            name=_("Paid Bills"),
        )

    @_debug.perf.timed
    def button_open_statement_lines(self):
        _debug.lifecycle("button_open_statement_lines", records=self)
        self.check_singleton()
        return self.reconciled_statement_line_ids.with_context(
            create=False
        )._get_records_action(
            name=_("Matched Transactions"),
        )

    @_debug.perf.timed
    def button_open_journal_entry(self):
        _debug.lifecycle("button_open_journal_entry", records=self)
        self.check_singleton()
        return self.move_id.with_context(create=False)._get_records_action(
            name=_("Journal Entry"),
        )


class AccountMove(models.Model):
    _inherit = "account.move"

    payment_ids = fields.One2many(
        comodel_name="account.payment",
        inverse_name="move_id",
        string="Payments",
    )
