from odoo import models, api


class PosConfig(models.Model):
    _inherit = 'pos.config'

    @api.model
    def _load_pos_data_read(self, records, config):
        data = super()._load_pos_data_read(records, config)

        if data and self.env.company.country_id.code == 'ES':
            tbai_refund_reason_field = self.env['ir.model.fields']._get('account.move', 'l10n_es_tbai_refund_reason')
            data[0]['_tbai_refund_reasons'] = [
                {'value': refund_reason.value, 'name': refund_reason.name}
                for refund_reason in tbai_refund_reason_field.selection_ids
                if refund_reason.value != 'R5'  # R5 is for simplified invoice
            ]

        return data
