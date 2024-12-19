from odoo import models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def get_limited_partners_loading(self, offset=0):
        partner_ids = super().get_limited_partners_loading(offset)
        if (self.env.ref('l10n_pe_pos.partner_pe_cf').id,) not in partner_ids:
            partner_ids.append((self.env.ref('l10n_pe_pos.partner_pe_cf').id,))
        return partner_ids
