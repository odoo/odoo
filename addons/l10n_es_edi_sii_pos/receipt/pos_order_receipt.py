from odoo import models


class PosOrderReceipt(models.AbstractModel):
    _inherit = 'pos.order.receipt'

    def order_receipt_generate_data(self, basic_receipt=False):
        data = super().order_receipt_generate_data(basic_receipt)
        if self.l10n_es_sii_required:
            data['extra_data']['sii_ticket_name'] = self._l10n_es_sii_get_ticket_name()
            data['conditions']['has_account_move'] = self.is_singly_invoiced
        return data