from odoo import models, api


class ResCurrency(models.Model):
    _name = 'res.currency'
    _inherit = ['res.currency', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data):
<<<<<<< master
        return [('id', '=', data['pos.config'][0]['currency_id'])]
||||||| c6857d98be168160c067942e99b63b1634c3ffb7
        return [('id', '=', data['pos.config']['data'][0]['currency_id'])]
=======
        company_currency_id = self.env['res.company'].browse(data['pos.config']['data'][0]['company_id']).currency_id.id
        if company_currency_id != data['pos.config']['data'][0]['currency_id']:
            return [('id', 'in', [company_currency_id, data['pos.config']['data'][0]['currency_id']])]
        return [('id', '=', data['pos.config']['data'][0]['currency_id'])]
>>>>>>> be349795fe8696886a1c5bdf13153b2a65281e22

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'name', 'symbol', 'position', 'rounding', 'rate', 'decimal_places', 'iso_numeric']
