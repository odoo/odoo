from odoo import models, api
from odoo.addons import account, point_of_sale


class DecimalPrecision(account.DecimalPrecision, point_of_sale.PosLoadMixin):

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'name', 'digits']
