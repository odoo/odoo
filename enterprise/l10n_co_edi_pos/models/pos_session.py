from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _load_pos_data(self, data):
        # EXTENDS point_of_sale
        data = super()._load_pos_data(data)
        if self.env.company.account_fiscal_country_id.code == 'CO':
            final_consumer = self.env.ref('l10n_co_edi.consumidor_final_customer', raise_if_not_found=False)
            data['data'][0]['_l10n_co_final_consumer_id'] = final_consumer.id if final_consumer else None
        return data
