# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class L10n_PhQrphTransaction(models.Model):
    _inherit = 'l10n_ph.qrph.transaction'

    def _l10n_ph_qrph_settle(self):
        # EXTENDS l10n_ph
        self.ensure_one()
        if self.model == 'pos.order':
            order = self._get_record()
            # An order taken at the counter is paid by the cashier confirming the code was scanned,
            # and is only stored once that happened: there is nothing for Maya to settle there.
            if order and order.config_id.self_ordering_mode == 'kiosk':
                order._l10n_ph_qrph_settle_kiosk_payment()
            return
        return super()._l10n_ph_qrph_settle()
