<<<<<<< HEAD
||||||| MERGE BASE
=======
from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _post_read_pos_data(self, data):
        verifactu_refund_reason_field = self.env['ir.model.fields']._get('pos.order', 'l10n_es_edi_verifactu_refund_reason')
        data[0]['_verifactu_refund_reasons'] = [
            {'value': refund_reason.value, 'name': refund_reason.name}
            for refund_reason in verifactu_refund_reason_field.selection_ids
        ]

        return super()._post_read_pos_data(data)

>>>>>>> FORWARD PORTED
