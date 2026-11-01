# Copyright 2026 OD19
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models, _
from odoo.exceptions import UserError


WHT_RATE_SELECTION = [
    ("1", "1%"),
    ("1.5", "1.5%"),
    ("2", "2%"),
    ("3", "3%"),
    ("5", "5%"),
]


class AccountPayment(models.Model):
    _inherit = "account.payment"

    # ------------------------------------------------------------------
    # Feature 2: Payer / Payee (also available on payments)
    # ------------------------------------------------------------------
    od19_payer_id = fields.Many2one(
        comodel_name="res.partner",
        string="ผู้จ่ายเงิน / Payer",
        help="Partner who actually pays.",
    )
    od19_payee_id = fields.Many2one(
        comodel_name="res.partner",
        string="ผู้รับเงิน / Payee",
        help="Partner who actually receives the payment.",
    )

    # ------------------------------------------------------------------
    # Feature 6: WHT base computed from selected invoices
    # ------------------------------------------------------------------
    od19_wht_invoice_base_amount = fields.Monetary(
        string="WHT Base Amount",
        currency_field="currency_id",
        compute="_compute_od19_wht_invoice_base_amount",
        store=True,
        help="Sum of the untaxed amounts of the invoices reconciled "
        "with this payment.",
    )
    od19_wht_rate = fields.Selection(
        selection=WHT_RATE_SELECTION,
        string="WHT Rate",
        default="1",
        help="Withholding tax rate applied to the base amount.",
    )
    od19_wht_type_id = fields.Many2one(
        comodel_name="account.withholding.tax",
        string="WHT Type",
        help="Withholding tax type (OCA l10n_th_account_tax).",
    )
    od19_wht_invoice_amount = fields.Monetary(
        string="WHT Amount",
        currency_field="currency_id",
        compute="_compute_od19_wht_invoice_amount",
        store=True,
        help="Withholding tax amount = base amount x rate.",
    )

    @api.depends(
        "reconciled_invoice_ids",
        "reconciled_bill_ids",
        "reconciled_invoice_ids.amount_untaxed",
        "reconciled_bill_ids.amount_untaxed",
    )
    def _compute_od19_wht_invoice_base_amount(self):
        for payment in self:
            invoices = payment.reconciled_invoice_ids | payment.reconciled_bill_ids
            if not invoices:
                # Fallback: lines tagged with WHT on the payment move.
                wht_lines = payment.move_id.line_ids.filtered("wht_tax_id")
                base = 0.0
                for line in wht_lines:
                    base += abs(line.balance)
                payment.od19_wht_invoice_base_amount = base
            else:
                payment.od19_wht_invoice_base_amount = sum(
                    invoices.mapped("amount_untaxed")
                )

    @api.depends("od19_wht_invoice_base_amount", "od19_wht_rate")
    def _compute_od19_wht_invoice_amount(self):
        for payment in self:
            try:
                rate = float(payment.od19_wht_rate or 0.0)
            except (TypeError, ValueError):
                rate = 0.0
            payment.od19_wht_invoice_amount = (
                payment.od19_wht_invoice_base_amount * rate / 100.0
            )

    # ------------------------------------------------------------------
    # Bill-first rule (AP / ฝั่งทำจ่าย): require ตั้งหนี้ before payment
    # ------------------------------------------------------------------
    def _od19_requires_vendor_bill(self):
        """AP bill-first rule applies to outbound payments (จ่ายชำระเจ้าหนี้)."""
        self.ensure_one()
        return (
            self.payment_type == "outbound"
            and self.company_id.od19_require_vendor_bill_for_payment
        )

    def _od19_is_expense_reimbursement(self):
        """Expense reimbursements paid to employees are out of the AP rule."""
        self.ensure_one()
        if "od19_is_expense_payment" not in self._fields:
            return False
        return bool(self.od19_is_expense_payment)

    def _od19_has_linked_vendor_bill(self):
        """True when the payment settles at least one Vendor Bill (ตั้งหนี้)."""
        self.ensure_one()
        bills = self.invoice_ids.filtered(
            lambda move: move.is_purchase_document(include_receipts=True)
        )
        if bills or self.reconciled_bill_ids:
            return True
        # Payments staged by the "Prepare payment" option of the Register
        # Payment wizard (``od19_accounting_payment_voucher_reports``) keep
        # their source document lines until they are posted, so the vendor bill
        # link is not materialised yet at posting time.
        if "od19_pending_reconcile_line_ids" in self._fields:
            staged_bills = self.od19_pending_reconcile_line_ids.move_id.filtered(
                lambda move: move.is_purchase_document(include_receipts=True)
            )
            if staged_bills:
                return True
        return False

    def _od19_check_vendor_bill_required(self):
        """Block outbound payments that are not linked to a Vendor Bill.

        ``od19_skip_vendor_bill_check`` is set by the "Register Payment" wizard,
        which always starts from an existing invoice/bill.
        """
        if self.env.context.get("od19_skip_vendor_bill_check"):
            return
        for payment in self:
            if not payment._od19_requires_vendor_bill():
                continue
            if payment._od19_is_expense_reimbursement():
                continue
            if payment._od19_has_linked_vendor_bill():
                continue
            raise UserError(
                _(
                    "ไม่สามารถยืนยันการจ่ายชำระได้ เนื่องจากไม่พบการตั้งหนี้ "
                    "(Vendor Bill)\n\n"
                    "การจ่ายชำระฝั่งเจ้าหนี้ต้องอ้างอิงใบแจ้งหนี้ของผู้ขายที่ "
                    "post แล้วเท่านั้น กรุณาใช้ปุ่ม \"ชำระเงิน\" (Register "
                    "Payment) จากใบแจ้งหนี้ผู้ขาย\n\n"
                    "Payment %(name)s (คู่ค้า: %(partner)s) ไม่ได้ผูกกับ "
                    "Vendor Bill",
                    name=payment.name or payment.display_name,
                    partner=payment.partner_id.display_name or "-",
                )
            )

    def action_post(self):
        self._od19_check_vendor_bill_required()
        return super().action_post()
