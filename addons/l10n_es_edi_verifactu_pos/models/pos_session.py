from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _load_pos_data(self, models_to_load):
        data = super()._load_pos_data(models_to_load)

        verifactu_refund_reason_field = self.env['ir.model.fields']._get('pos.order', 'l10n_es_edi_verifactu_refund_reason')
        data['data'][0]['_verifactu_refund_reasons'] = [
            {'value': refund_reason.value, 'name': refund_reason.name}
            for refund_reason in verifactu_refund_reason_field.selection_ids
        ]

        return data
