from odoo import models


class PosOrderReceipt(models.AbstractModel):
    _inherit = 'pos.order.receipt'

    def order_receipt_generate_data(self, basic_receipt=False):
        data = super().order_receipt_generate_data(basic_receipt)
        if self.company_id.account_fiscal_country_id.code == 'EG' and (qr_url := data['order'].get('l10n_eg_edi_pos_qr')):
            data['extra_data']['l10n_eg_edi_pos_qr'] = self._order_receipt_generate_qr_code(qr_url)
        return data
