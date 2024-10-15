from odoo import models
from odoo.addons import point_of_sale


class PosConfig(point_of_sale.PosConfig):

    def get_limited_partners_loading(self):
        partner_ids = super().get_limited_partners_loading()
        if (self.env.ref('l10n_ar.par_cfa').id,) not in partner_ids:
            partner_ids.append((self.env.ref('l10n_ar.par_cfa').id,))
        return partner_ids
