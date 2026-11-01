from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PettyCashTransaction(models.Model):
    _name = "petty.cash.transaction"
    _description = "Petty Cash Transaction"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    fund_id = fields.Many2one(
        "petty.cash.fund",
        string="Petty Cash Fund",
        required=True,
        tracking=True,
    )
    name = fields.Char(
        string="Description",
        required=True,
        tracking=True,
    )
    amount = fields.Monetary(
        string="Amount",
        currency_field="currency_id",
        required=True,
        tracking=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        related="fund_id.currency_id",
        store=True,
    )
    transaction_type = fields.Selection(
        [
            ("expense", "Expense"),
            ("replenishment", "Replenishment"),
        ],
        string="Type",
        required=True,
        default="expense",
        tracking=True,
    )
    expense_account_id = fields.Many2one(
        "account.account",
        string="Expense Account",
        domain="[('account_type', '=', 'expense')]",
    )
    date = fields.Date(
        string="Date",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("posted", "Posted"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="draft",
        tracking=True,
        copy=False,
    )
    move_id = fields.Many2one(
        "account.move",
        string="Journal Entry",
        readonly=True,
        copy=False,
    )
    journal_id = fields.Many2one(
        "account.journal",
        string="Journal",
    )
    note = fields.Text(string="Notes")

    # ------------------------------------------------------------------
    # Supporting document type - payment certificate in lieu of receipt
    # (ใบรับรองแทนใบเสร็จรับเงิน)
    # ------------------------------------------------------------------
    # Petty cash disbursements usually go to payees that cannot issue a
    # receipt. A payment certificate documents the payment; it carries no
    # input VAT, so the whole amount is booked as an expense.
    od19_document_type = fields.Selection(
        [
            ("tax_invoice", "ใบกำกับภาษี / Tax Invoice"),
            ("receipt", "ใบเสร็จรับเงิน / Receipt"),
            ("payment_certificate",
             "ใบรับรองแทนใบเสร็จรับเงิน / Payment Certificate"),
        ],
        string="ประเภทเอกสาร / Document Type",
        default="tax_invoice",
        required=True,
        tracking=True,
        help=(
            'Thai supporting-document type. Choose "ใบรับรองแทนใบเสร็จรับเงิน" '
            'when the payee cannot issue a receipt: there is no input VAT to '
            'claim and the whole amount is booked as an expense.'
        ),
    )
    od19_certificate_number = fields.Char(
        string="เลขที่ใบรับรอง / Certificate No",
        copy=False,
        help="Running number printed on the payment certificate.",
    )
    od19_payee_name = fields.Char(
        string="ผู้รับเงิน / Payee",
        help="Person who received the petty cash, printed on the certificate.",
    )
    od19_vat_creditable = fields.Boolean(
        string="ภาษีซื้อหักได้ / Input VAT Creditable",
        compute="_compute_od19_vat_creditable",
        store=True,
        help="Unticked for a payment certificate: the payee does not charge "
             "VAT, so no input tax can be claimed against output VAT.",
    )

    @api.depends("od19_document_type")
    def _compute_od19_vat_creditable(self):
        for transaction in self:
            transaction.od19_vat_creditable = (
                transaction.od19_document_type != "payment_certificate"
            )

    @api.constrains("amount")
    def _check_amount(self):
        for transaction in self:
            if transaction.amount <= 0:
                raise ValidationError(
                    _("Amount must be greater than zero.")
                )

    @api.constrains("transaction_type", "expense_account_id")
    def _check_expense_account(self):
        for transaction in self:
            if transaction.transaction_type == "expense" and not transaction.expense_account_id:
                raise ValidationError(
                    _("Expense account is required for expense transactions.")
                )

    def action_post(self):
        for transaction in self:
            if transaction.state != "draft":
                continue
            if transaction.transaction_type == "expense":
                if transaction.fund_id.balance < transaction.amount:
                    raise ValidationError(
                        _("Insufficient petty cash balance.")
                    )
            if not transaction.journal_id:
                raise ValidationError(
                    _("Please select a journal.")
                )
            move_vals = transaction._prepare_move_vals()
            move = self.env["account.move"].create(move_vals)
            move.action_post()
            transaction.move_id = move
            transaction.state = "posted"

    def action_reconcile(self):
        """ตัดบัญชีเงินสดย่อยกับรายการคู่ที่เกี่ยวข้อง (reconcile)."""
        for transaction in self:
            if transaction.state != "posted" or not transaction.move_id:
                continue
            transaction.move_id._od19_reconcile_account_lines(
                transaction.fund_id.account_id.id
            )
        return True

    def action_cancel(self):
        for transaction in self:
            if transaction.state != "posted":
                continue
            if transaction.move_id:
                transaction.move_id.with_context(
                    od19_skip_reason=True
                ).button_cancel()
            transaction.state = "cancelled"

    def action_draft(self):
        for transaction in self:
            if transaction.state != "cancelled":
                continue
            if transaction.move_id:
                transaction.move_id.button_draft()
                transaction.move_id.unlink()
            transaction.state = "draft"

    def _prepare_move_vals(self):
        self.ensure_one()
        if self.transaction_type == "expense":
            debit_account = self.expense_account_id
            credit_account = self.fund_id.account_id
        else:
            debit_account = self.fund_id.account_id
            credit_account = self.journal_id.default_account_id

        return {
            "date": self.date,
            "journal_id": self.journal_id.id,
            "ref": self.name,
            "line_ids": [
                (
                    0,
                    0,
                    {
                        "account_id": debit_account.id,
                        "debit": self.amount,
                        "credit": 0.0,
                        "name": self.name,
                    },
                ),
                (
                    0,
                    0,
                    {
                        "account_id": credit_account.id,
                        "debit": 0.0,
                        "credit": self.amount,
                        "name": self.name,
                    },
                ),
            ],
        }
