from odoo import models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _is_quantities_set(self):
        return self.company_id.l10n_in_is_gst_registered or super()._is_quantities_set()
