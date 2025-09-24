from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _post_read_pos_data(self, data):
        tbai_refund_reason_field = self.env['ir.model.fields']._get('account.move', 'l10n_es_tbai_refund_reason')
        data[0]['_tbai_refund_reasons'] = [
            {'value': refund_reason.value, 'name': refund_reason.name}
            for refund_reason in tbai_refund_reason_field.selection_ids
            if refund_reason.value != 'R5'  # R5 is for simplified invoice
        ]

        return super()._post_read_pos_data(data)
