from odoo import models

from odoo.tools.misc import mod10r

l10n_ch_ISR_NUMBER_LENGTH = 27
l10n_ch_ISR_ID_NUM_LENGTH = 6

class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _compute_sale_order_reference(self, order):
        self.ensure_one()
        if self.company_id.bank_ids.l10n_ch_qr_iban and self.sale_order_ids.name:
            id_number = self.company_id.bank_ids.l10n_ch_postal or ''
            if id_number:
                id_number = id_number.zfill(l10n_ch_ISR_ID_NUM_LENGTH)
            # Gets an unique number based on the sale order name. A letter will get converted to its base10 value
            invoice_ref = "".join([[str(ord(a)), a][a.isdigit()] for a in self.sale_order_ids.name])
            full_len = len(id_number) + len(invoice_ref)
            ref_payload_len = l10n_ch_ISR_NUMBER_LENGTH - 1
            extra = full_len - ref_payload_len
            if extra > 0:
                invoice_ref = invoice_ref[extra:]
            internal_ref = invoice_ref.zfill(ref_payload_len - len(id_number))
            return mod10r(id_number + internal_ref)
        else:
            return super()._compute_sale_order_reference(order)
