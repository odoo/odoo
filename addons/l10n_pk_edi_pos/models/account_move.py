from urllib.parse import urlencode

from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _l10n_pk_edi_pos_qr(self):
        self.ensure_one()
        # sudo: the invoice can be printed by users without any access to POS orders.
        return self.sudo().pos_order_ids.filtered('l10n_pk_edi_pos_qr')[:1].l10n_pk_edi_pos_qr

    def _l10n_pk_edi_pos_qr_code_src(self):
        self.ensure_one()
        encoded_params = urlencode(
            {
                'barcode_type': 'QR',
                'quiet': 0,
                'value': self._l10n_pk_edi_pos_qr(),
                'width': 200,
                'height': 200,
            }
        )
        return f"/report/barcode/?{encoded_params}"
