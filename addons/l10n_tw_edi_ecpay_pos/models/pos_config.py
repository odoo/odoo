# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def get_limited_partners_loading(self):
        partner_ids = super().get_limited_partners_loading()
        if self.env.ref('l10n_tw_edi_ecpay_pos.ecpay_default_walk_in_customer', raise_if_not_found=False) and self.env.ref('l10n_tw_edi_ecpay_pos.ecpay_default_walk_in_customer').id not in partner_ids:
            partner_ids.append((self.env.ref('l10n_tw_edi_ecpay_pos.ecpay_default_walk_in_customer').id,))
        return partner_ids
