from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PaymentRefundWizard(models.TransientModel):
    _name = "payment.refund.wizard"
    _description = "Payment Refund Wizard"

    payment_id = fields.Many2one(
        comodel_name="account.payment",
        default=lambda self: self.env.context.get("active_id"),
        readonly=True,
    )
    transaction_id = fields.Many2one(
        related="payment_id.transaction_id",
        string="Payment Transaction",
    )
    payment_amount = fields.Monetary(
        related="payment_id.amount",
        string="Payment Amount",
    )
    refunded_amount = fields.Monetary(compute="_compute_refunded_amount")
    amount_available_for_refund = fields.Monetary(
        related="payment_id.amount_available_for_refund",
        string="Maximum Refund Allowed",
    )
    amount_to_refund = fields.Monetary(
        string="Refund Amount",
        compute="_compute_amount_to_refund",
        store=True,
        readonly=False,
    )
    currency_id = fields.Many2one(
        related="transaction_id.currency_id",
        string="Currency",
    )
    support_refund = fields.Selection(
        selection=[
            ("none", "Unsupported"),
            ("full_only", "Full Only"),
            ("partial", "Partial"),
        ],
        string="Refund",
        compute="_compute_support_refund",
    )
    has_pending_refund = fields.Boolean(
        string="Has a pending refund",
        compute="_compute_has_pending_refund",
    )

    @api.constrains("amount_to_refund")
    def _check_amount_to_refund_within_boundaries(self):
        for wizard in self:
            if not 0 < wizard.amount_to_refund <= wizard.amount_available_for_refund:
                raise ValidationError(
                    _(
                        "The amount to be refunded must be positive and cannot be superior to %s.",
                        wizard.amount_available_for_refund,
                    )
                )

    @api.depends("amount_available_for_refund")
    def _compute_refunded_amount(self):
        for wizard in self:
            wizard.refunded_amount = (
                wizard.payment_amount - wizard.amount_available_for_refund
            )

    @api.depends("amount_available_for_refund")
    def _compute_amount_to_refund(self):
        """Set the default amount to refund to the amount available for refund."""
        for wizard in self:
            wizard.amount_to_refund = wizard.amount_available_for_refund

    @api.depends("transaction_id.provider_id", "transaction_id.payment_method_id")
    def _compute_support_refund(self):
        for wizard in self:
            tx_sudo = (
                wizard.transaction_id.sudo()
            )  # needed for users without access to the provider
            p_support_refund = tx_sudo.provider_id.support_refund
            pm_sudo = tx_sudo.payment_method_id
            pm_support_refund = (
                pm_sudo.primary_payment_method_id or pm_sudo
            ).support_refund
            if p_support_refund == "none" or pm_support_refund == "none":
                wizard.support_refund = "none"
            elif p_support_refund == "full_only" or pm_support_refund == "full_only":
                wizard.support_refund = "full_only"
            else:  # Both support partial refunds.
                wizard.support_refund = "partial"

    @api.depends("payment_id")  # To always trigger the compute
    def _compute_has_pending_refund(self):
        for wizard in self:
            pending_refunds_count = self.env["payment.transaction"].search_count(  # noqa: E8507 - a transient wizard: one record
                [
                    ("source_transaction_id", "=", wizard.payment_id.transaction_id.id),
                    ("operation", "=", "refund"),
                    ("state", "in", ["draft", "pending", "authorized"]),
                ]
            )
            wizard.has_pending_refund = pending_refunds_count > 0

    def action_refund(self):
        self.check_singleton()
        return self.transaction_id.action_refund(amount_to_refund=self.amount_to_refund)
