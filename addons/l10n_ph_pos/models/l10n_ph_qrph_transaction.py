# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class L10n_PhQrphTransaction(models.Model):
    _inherit = 'l10n_ph.qrph.transaction'

    def _get_supported_models(self):
        # EXTENDS l10n_ph
        return super()._get_supported_models() + ['pos.order']

    def _get_record(self):
        # EXTENDS l10n_ph
        self.ensure_one()
        if self.model == 'pos.order':
            # The order is only stored once it is paid, so there is usually nothing to link yet.
            return self.env['pos.order'].search([('uuid', '=', self.model_id)], limit=1)
        return super()._get_record()
