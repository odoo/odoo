# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PosSession(models.Model):
    _inherit = "pos.session"

    def _load_pos_data(self, data):
        data = super()._load_pos_data(data)
        if self.env.company.country_id.code == 'TW':
            default_customer = self.env.ref('l10n_tw_edi_ecpay_pos.ecpay_default_walk_in_customer', raise_if_not_found=False)
            data['data'][0]['_default_tw_customer_id'] = default_customer.id if default_customer else None
        return data
