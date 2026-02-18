# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _load_pos_data(self, models_to_load):
        data = super()._load_pos_data(models_to_load)

        if self.company_id.country_id.code != 'VN':
            return data

        walk_in_customer_id = self.env.ref('l10n_vn_edi_viettel_pos.partner_walk_in_customer', raise_if_not_found=False).id
        data['data'][0]['_default_customer_id'] = walk_in_customer_id
        return data
