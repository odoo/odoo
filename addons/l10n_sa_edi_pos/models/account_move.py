from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _compute_qr_code_str(self):
        for order in self:
            if any(o._is_settle_or_deposit_order() for o in order.pos_order_ids):
                order.l10n_sa_qr_code_str = False
            else:
                super(AccountMove, order)._compute_qr_code_str()

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
