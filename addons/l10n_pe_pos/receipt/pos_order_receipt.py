# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class PosOrderReceipt(models.AbstractModel):
    _inherit = 'pos.order.receipt'

    def order_receipt_generate_data(self, basic_receipt=False):
        data = super().order_receipt_generate_data(basic_receipt)
        if self.company_id.account_fiscal_country_id.code == 'PE' and self.partner_id:
            identifier_vals = self.partner_id._get_preferred_legal_entity_identifier_vals()
            if value := identifier_vals.get('value'):
                data['partner']['vat'] = value
                if label := identifier_vals.get('label'):
                    data['extra_data']['partner_vat_label'] = str(label)
        return data
