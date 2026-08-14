from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def l10n_sa_pos_ensure_invoice_pdf(self):
        """Generate the invoice PDF on demand for SA POS.

        The PDF is not generated at checkout, see pos.order._generate_pos_order_invoice().
        This generates it, without sending the email, so that "Reprint Invoice" serves the
        real invoice rather than a proforma.
        """
        self.ensure_one()
        if not self.invoice_pdf_report_id:
            template = self.env.ref(self._get_mail_template())
            self.with_context(skip_invoice_sync=True)._generate_pdf_and_send_invoice(
                template, checkbox_send_mail=False,
            )

    def _l10n_sa_check_refund_reason(self):
        return super()._l10n_sa_check_refund_reason() or (self.pos_order_ids and self.pos_order_ids[0].refunded_orders_count > 0 and self.ref)
