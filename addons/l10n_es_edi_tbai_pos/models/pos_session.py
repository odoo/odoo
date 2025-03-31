from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _load_pos_data(self, models_to_load):
        data = super()._load_pos_data(models_to_load)

        tbai_refund_reason_field = self.env['ir.model.fields']._get('account.move', 'l10n_es_tbai_refund_reason')
        data['data'][0]['_tbai_refund_reasons'] = [
            {'value': refund_reason.value, 'name': refund_reason.name}
            for refund_reason in tbai_refund_reason_field.selection_ids
            if refund_reason.value != 'R5'  # R5 is for simplified invoice
        ]

        return data
