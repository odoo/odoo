from odoo import models, fields

class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    def get_qr_content(self, amount, free_communication, structured_communication, currency, debtor_partner):
        self.ensure_one()
        if self.qr_code_method == "id_qr":
            qr_id = self.env['l10n_id_pos.qr.code.payment'].with_context(pos_payment_method_id=self.id)._get_or_create(amount, free_communication, structured_communication, currency, debtor_partner)
            return {
                "qr_image": qr_id.qr_img,
                "qr_code_id": qr_id.id,
            }
        else:
            return super().get_qr_content(amount, free_communication, structured_communication, currency, debtor_partner)
