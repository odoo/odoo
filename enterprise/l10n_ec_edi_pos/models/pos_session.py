from odoo import api, models


class PosSession(models.Model):

    _inherit = 'pos.session'

    def _load_pos_data(self, data):
        data = super()._load_pos_data(data)
        if self.env.company.country_id.code == 'EC':
            final_consumer = self.env.ref('l10n_ec.ec_final_consumer', raise_if_not_found=False)
            data['data'][0]['_final_consumer_id'] = final_consumer.id if final_consumer else None
        return data

    @api.model
    def _load_pos_data_models(self, config_id):
        data = super()._load_pos_data_models(config_id)
        if self.env.company.country_id.code == 'EC':
            data += ['l10n_latam.identification.type', 'account.move']
        return data
