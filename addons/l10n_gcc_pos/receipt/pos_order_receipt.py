# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class PosOrderReceipt(models.AbstractModel):
    _inherit = 'pos.order.receipt'
    _description = 'Point of Sale Order Receipt Generator'

    def order_receipt_generate_data(self, basic_receipt=False):
        data = super().order_receipt_generate_data(basic_receipt)
        data['conditions']['gcc_country'] = self.company_id.country_id.code in ["SA", "AE", "BH", "OM", "QA", "KW"]
        data['conditions']['l10n_gcc_dual_language_receipt'] = self.config_id.l10n_gcc_dual_language_receipt
        data['conditions']['l10n_gcc_is_settlement'] = len(self.lines) == 0 or any(
            paymentline.payment_method_id.type == "pay_later" and paymentline.amount < 0
            for paymentline in self.payment_ids
        )
        return data
