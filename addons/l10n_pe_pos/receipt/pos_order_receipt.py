# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class PosOrderReceipt(models.AbstractModel):
    _inherit = 'pos.order.receipt'

    def order_receipt_generate_data(self, basic_receipt=False):
        data = super().order_receipt_generate_data(basic_receipt)
        if self.company_id.account_fiscal_country_id.code == 'PE':
            data['extra_data']['partner_vat_label'] = self.partner_id.l10n_latam_identification_type_id.name
        return data
