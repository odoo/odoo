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

        if self.group_payment:
            # Extract all invoices from batch_result lines
            invoices = self.env['account.move'].browse({line.move_id.id for line in batch_result['lines']})

            # Check if any invoice have early_pay_credit_note set to True then all invoices have early_pay_credit_note set to True
            if any(invoice.invoice_payment_term_id.early_pay_credit_note for invoice in invoices):
                if not all(invoice.invoice_payment_term_id.early_pay_credit_note for invoice in invoices):
                    raise UserError(_(
                        "Creating credit note must be consistently enabled or disabled for payment terms of all selected invoices."
                    ))

        # If early payment discount is applied, create credit note directly
        if self.payment_difference_handling == 'reconcile' and self.early_payment_discount_mode:
            open_amount_currency = self.payment_difference * (-1 if self.payment_type == 'outbound' else 1)
            open_balance = self.currency_id._convert(
                open_amount_currency, self.company_id.currency_id, self.company_id, self.payment_date
            )
            self.env['account.move']._create_credit_note_for_early_payment_discount(
                batch_result=batch_result,
                group_payment=self.group_payment,
                open_balance=open_balance,
                payment_vals=payment_vals,
            )

        return payment_vals

    def _create_payment_vals_from_batch(self, batch_result):
        # OVERRIDE
        payment_vals = super()._create_payment_vals_from_batch(batch_result)

        # If early payment discount is applied, create credit note directly
        if self._get_total_amounts_to_pay([batch_result])['epd_applied']:
            open_amount_currency = (batch_result['lines'].amount_residual - batch_result['lines'].discount_balance) * (-1 if batch_result['payment_values']['payment_type'] == 'outbound' else 1)
            open_balance = self.currency_id._convert(open_amount_currency, batch_result['lines'].company_currency_id, self.company_id, self.payment_date)
            self.env['account.move']._create_credit_note_for_early_payment_discount(
                batch_result=batch_result,
                group_payment=self.group_payment,
                open_balance=open_balance,
                payment_vals=payment_vals,
            )

        return payment_vals
