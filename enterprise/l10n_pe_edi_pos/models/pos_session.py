from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _load_pos_data(self, models_to_load):
        # EXTENDS 'point_of_sale'
        data = super()._load_pos_data(models_to_load)
        l10n_pe_edi_refund_reason = self.env['ir.model.fields']._get('account.move', 'l10n_pe_edi_refund_reason')
        data['data'][0]['_l10n_pe_edi_refund_reason'] = [
            {'value': s.value, 'name': s.name}
            for s in l10n_pe_edi_refund_reason.selection_ids
        ]
        return data
