from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _l10n_es_edi_verifactu_get_record_values(self, cancellation=False):
        self.ensure_one()
        vals = super()._l10n_es_edi_verifactu_get_record_values(cancellation=cancellation)
        # Case: We invoiced the refund but not the original order
        refunded_order = None if self.reversed_entry_id else self.pos_order_ids.refunded_order_ids
        if refunded_order:
            vals['refunded_document'] = refunded_order.l10n_es_edi_verifactu_document_ids._get_last('submission')
        return vals
