from odoo import models


class PosOrderReceipt(models.AbstractModel):
    _inherit = 'pos.order.receipt'

    def order_receipt_generate_data(self, basic_receipt=False):
        data = super().order_receipt_generate_data(basic_receipt)
        if self.company_id.country_id.code == 'BH':
            data['conditions']['code_bh'] = True
            data['conditions']['l10n_bh_partner_has_vat'] = bool(self.partner_id.commercial_partner_id.vat)
        return data
