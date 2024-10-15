from odoo import models, api
from odoo.addons import account, point_of_sale


class ResCurrency(account.ResCurrency, point_of_sale.PosLoadMixin):

    @api.model
    def _load_pos_data_domain(self, data):
        return [('id', '=', data['pos.config']['data'][0]['currency_id'])]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'name', 'symbol', 'position', 'rounding', 'rate', 'decimal_places', 'iso_numeric']
