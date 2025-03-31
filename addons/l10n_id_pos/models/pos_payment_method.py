# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import UserError
from odoo import _, models


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    def l10n_id_verify_qris_status(self, trx_uuid):
        """ Verify qris payment status from the provided transaction UUID

        For all qris_invoice_details linked to the transaction, check the payment status
        """
        if self.payment_method_type != 'qr_code' or self.qr_code_method != 'id_qr':
            return True
        trx = self.env['l10n_id.qris.transaction']._get_latest_transaction('pos.order', trx_uuid)
        if not trx:
            raise UserError(_("No QRIS transaction record is found based on this order"))

        result = trx._l10n_id_get_qris_qr_statuses()
        return result['paid']
