from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _load_pos_data(self, models_to_load):
        data = super()._load_pos_data(models_to_load)

        l10n_sa_reason_field = self.env['ir.model.fields']._get('account.move', 'l10n_sa_reason')
        data[0]['_zatca_refund_reasons'] = [
            {'value': refund_reason.value, 'name': refund_reason.name}
            for refund_reason in l10n_sa_reason_field.selection_ids
        ]

        return data
