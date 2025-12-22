from odoo import models


class QRISTransaction(models.Model):
    _inherit = "l10n_id.qris.transaction"

    def _get_supported_models(self):
        return super()._get_supported_models() + ['pos.order']

    def _get_record(self):
        # Override
        # add it for pos.order
        if self.model == 'pos.order':
            return self.env[self.model].search([('uuid', '=', self.model_id)])
        return super()._get_record()
