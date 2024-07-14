from odoo import models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _get_invoice_lines(self):
        # EXTENDS 'sale'
        invoice_lines = super()._get_invoice_lines()

        # The request cancel has been made but you don't want to account twice the sale values.
        # Instead, account only the first invoice until the cancellation is completed.
        excluded_invoices = set(
            invoice_lines.move_id\
                .filtered(lambda x: x.l10n_mx_edi_cfdi_state == 'sent')\
                .l10n_mx_edi_cfdi_cancel_id
        )
        return invoice_lines.filtered(lambda x: x.move_id not in excluded_invoices)
