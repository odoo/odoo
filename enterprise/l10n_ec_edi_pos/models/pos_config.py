from odoo import models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def get_limited_partners_loading(self):
        partner_ids = super().get_limited_partners_loading()
        if (self.env.ref('l10n_ec.ec_final_consumer').id,) not in partner_ids:
            partner_ids.append((self.env.ref('l10n_ec.ec_final_consumer').id,))
        return partner_ids
