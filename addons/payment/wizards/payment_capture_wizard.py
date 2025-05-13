# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import format_amount


class PaymentCaptureWizard(models.TransientModel):
    _name = 'payment.capture.wizard'
    _description = "Payment Capture Wizard"

    transaction_ids = fields.Many2many(  # All the source txs related to the capture request
        comodel_name='payment.transaction',
        default=lambda self: self.env.context.get('active_ids'),
        readonly=True,
    )
    authorized_amount = fields.Monetary(
        string="Authorized Amount", compute='_compute_authorized_amount'
    )
    captured_amount = fields.Monetary(string="Already Captured", compute='_compute_captured_amount')
    voided_amount = fields.Monetary(string="Already Voided", compute='_compute_voided_amount')
    available_amount = fields.Monetary(
        string="Maximum Capture Allowed", compute='_compute_available_amount'
    )
    amount_to_capture = fields.Monetary(
        compute='_compute_amount_to_capture', store=True, readonly=False
    )
    is_amount_to_capture_valid = fields.Boolean(compute='_compute_is_amount_to_capture_valid')
    void_remaining_amount = fields.Boolean()
    currency_id = fields.Many2one(related='transaction_ids.currency_id')
    support_partial_capture = fields.Boolean(
        help="Whether each of the transactions' provider supports the partial capture.",
        compute='_compute_support_partial_capture',
        compute_sudo=True,
    )
    has_draft_children = fields.Boolean(compute='_compute_has_draft_children')
    has_remaining_amount = fields.Boolean(compute='_compute_has_remaining_amount')

    # === COMPUTE METHODS === #

    @api.depends('transaction_ids')
    def _compute_authorized_amount(self):
        for wizard in self:
            wizard.authorized_amount = sum(wizard.transaction_ids.mapped('amount'))

    @api.depends('transaction_ids')
    def _compute_captured_amount(self):
        for wizard in self:
            full_capture_txs = wizard.transaction_ids.filtered(
                lambda tx: tx.state == 'done' and not tx.child_transaction_ids
            )  # Transactions that have been fully captured in a single capture operation.
            partial_capture_child_txs = wizard.transaction_ids.child_transaction_ids.filtered(
                lambda tx: tx.state == 'done'
            )  # Transactions that represent a partial capture of their source transaction.
            wizard.captured_amount = sum(
                (full_capture_txs | partial_capture_child_txs).mapped('amount')
            )

    @api.depends('transaction_ids')
    def _compute_voided_amount(self):
        for wizard in self:
            void_child_txs = wizard.transaction_ids.child_transaction_ids.filtered(
                lambda tx: tx.state == 'cancel'
            )
            wizard.voided_amount = sum(void_child_txs.mapped('amount'))

    @api.depends('authorized_amount', 'captured_amount', 'voided_amount')
    def _compute_available_amount(self):
        for wizard in self:
            wizard.available_amount = wizard.authorized_amount \
                                      - wizard.captured_amount \
                                      - wizard.voided_amount

    @api.depends('available_amount')
    def _compute_amount_to_capture(self):
        """ Set the default amount to capture to the amount available for capture. """
        for wizard in self:
            wizard.amount_to_capture = wizard.available_amount

    @api.depends('amount_to_capture', 'available_amount')
    def _compute_is_amount_to_capture_valid(self):
        for wizard in self:
            is_valid = 0 < wizard.amount_to_capture <= wizard.available_amount
            wizard.is_amount_to_capture_valid = is_valid

    @api.depends('transaction_ids')
    def _compute_support_partial_capture(self):
        for wizard in self:
            wizard.support_partial_capture = all(
                tx.provider_id.support_manual_capture == 'partial'
                and tx.primary_payment_method_id.support_manual_capture == 'partial'
                for tx in wizard.transaction_ids
            )

    @api.depends('transaction_ids')
    def _compute_has_draft_children(self):
        for wizard in self:
            wizard.has_draft_children = bool(wizard.transaction_ids.child_transaction_ids.filtered(
                lambda tx: tx.state == 'draft'
            ))

    @api.depends('available_amount', 'amount_to_capture')
    def _compute_has_remaining_amount(self):
        for wizard in self:
            wizard.has_remaining_amount = wizard.amount_to_capture < wizard.available_amount
            if not wizard.has_remaining_amount:
                wizard.void_remaining_amount = False

    # === CONSTRAINT METHODS === #

    @api.constrains('amount_to_capture')
    def _check_amount_to_capture_within_boundaries(self):
        for wizard in self:
            if not wizard.is_amount_to_capture_valid:
                formatted_amount = format_amount(
                    self.env, wizard.available_amount, wizard.currency_id
                )
                raise ValidationError(_(
                    "The amount to capture must be positive and cannot be superior to %s.",
                    formatted_amount
                ))
            if not wizard.support_partial_capture \
               and wizard.amount_to_capture != wizard.available_amount:
                raise ValidationError(_(
                    "Some of the transactions you intend to capture can only be captured in full. "
                    "Handle the transactions individually to capture a partial amount."
                ))

    # === ACTION METHODS === #

    def action_capture(self):
        self.ensure_one()

        remaining_amount_to_capture = self.amount_to_capture
        processed_txs_sudo = self.env['payment.transaction'].sudo()
        for source_tx in self.transaction_ids.filtered(lambda tx: tx.state == 'authorized'):
            partial_capture_child_txs = self.transaction_ids.child_transaction_ids.filtered(
                lambda tx: tx.source_transaction_id == source_tx and tx.state == 'done'
            )  # We can void all the remaining amount only at once => don't check cancel state.
            source_tx_remaining_amount = source_tx.currency_id.round(
                source_tx.amount - sum(partial_capture_child_txs.mapped('amount'))
            )
            if remaining_amount_to_capture:
                amount_to_capture = min(source_tx_remaining_amount, remaining_amount_to_capture)
                # In sudo mode because we need to be able to read on provider fields.
                processed_txs_sudo |= source_tx.sudo()._capture(
                    amount_to_capture=amount_to_capture
                )
                remaining_amount_to_capture -= amount_to_capture
                source_tx_remaining_amount -= amount_to_capture

            if source_tx_remaining_amount and self.void_remaining_amount:
                # The source tx isn't fully captured and the user wants to void the remaining.
                # In sudo mode because we need to be able to read on provider fields.
                processed_txs_sudo |= source_tx.sudo()._void(
                    amount_to_void=source_tx_remaining_amount
                )
            elif not remaining_amount_to_capture and not self.void_remaining_amount:
                # The amount to capture has been completely captured.
                break  # Skip the remaining transactions.
        return processed_txs_sudo._build_action_feedback_notification()
