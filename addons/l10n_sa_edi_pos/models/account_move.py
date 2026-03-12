from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def l10n_sa_pos_ensure_invoice_pdf(self):
        """Generate the invoice PDF on demand for SA POS.

        ZATCA clearance/reporting is already processed at checkout time.
        This generates only the PDF (no ZATCA re-submission, no email) so
        that "Reprint Invoice" serves the real signed invoice rather than a
        proforma.
        """
        self.ensure_one()
        if not self.invoice_pdf_report_id:
            # sending_methods={} skips email; ZATCA is already 'sent' so
            # _is_sa_edi_applicable returns False and it is not re-submitted.
            self.env['account.move.send']._generate_and_send_invoices(
                self, sending_methods={}
            )

    def _l10n_sa_check_refund_reason(self):
        return super()._l10n_sa_check_refund_reason() or (self.pos_order_ids and self.pos_order_ids[0].refunded_orders_count > 0 and self.ref)
