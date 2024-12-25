from odoo import models, _
from odoo.exceptions import UserError


class AccountPaymentRegister(models.TransientModel):
    _name = 'account.payment.register'
    _inherit = 'account.payment.register'

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------

    def _create_payment_vals_from_wizard(self, batch_result):
        # OVERRIDE
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)

        # Apply early payment discount and create credit notes if applicable
        self._handle_early_payment_discount(batch_result, payment_vals)
        return payment_vals

    def _create_payment_vals_from_batch(self, batch_result):
        # OVERRIDE
        payment_vals = super()._create_payment_vals_from_batch(batch_result)

        # Apply early payment discount and create credit notes if applicable
        self._handle_early_payment_discount(batch_result, payment_vals)
        return payment_vals

    def _handle_early_payment_discount(self, batch_result, payment_vals):
        """
        Handles the creation of credit notes for early payment discounts.
        """

        if self.hide_writeoff_section:
            if self.group_payment:
                # Extract all invoices from batch_result lines
                invoices = self.env['account.move'].browse({line.move_id.id for line in batch_result['lines']})

                # Check if any invoice have early_pay_credit_note set to True then all invoices have `early_pay_credit_note` set to True
                if any(invoice.invoice_payment_term_id.early_pay_credit_note for invoice in invoices):
                    if not all(invoice.invoice_payment_term_id.early_pay_credit_note for invoice in invoices):
                        raise UserError(_(
                            "Creating credit note must be consistently enabled or disabled for payment terms of all selected invoices."
                        ))

            for line in batch_result['lines']:
                invoice = line.move_id
                if invoice._is_eligible_for_early_payment_discount(self.company_id.currency_id, self.payment_date):
                    open_amount_currency = (line.amount_residual - line.discount_balance) \
                                        * (-1 if self.payment_type == 'outbound' else 1)
                    open_balance = self.currency_id._convert(
                        open_amount_currency, self.company_id.currency_id, self.company_id, self.payment_date
                    )

                    invoice._create_credit_note_for_early_payment_discount(
                        invoice=invoice,
                        open_balance=open_balance,
                        payment_vals=payment_vals,
                    )

    def _create_payments(self):
        # OVERRIDE
        payments = super()._create_payments()
        for payment in payments:
            for invoice in payment.invoice_ids.reversal_move_ids:
                message_content_reverse = _('Entry of discounted amount: %s', invoice._get_html_link())
                payment.message_post(body=message_content_reverse)
        return payments
