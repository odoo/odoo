from odoo import models


class PosOrderReceipt(models.AbstractModel):
    _inherit = 'pos.order.receipt'

    def order_receipt_generate_data(self, basic_receipt=False):
        data = super().order_receipt_generate_data(basic_receipt)
        if self.company_id.country_id.code != 'PK':
            return data

        if data['order'].get('l10n_pk_edi_pos_qr'):
            data['extra_data']['l10n_pk_edi_pos_qr'] = self._order_receipt_generate_qr_code(data['order']['l10n_pk_edi_pos_qr'])
        return data
