from odoo import models, api
from odoo.addons import account, point_of_sale


class AccountFiscalPosition(account.AccountFiscalPosition, point_of_sale.PosLoadMixin):

    @api.model
    def _load_pos_data_domain(self, data):
        return [('id', 'in', data['pos.config']['data'][0]['fiscal_position_ids'])]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'name', 'display_name', 'tax_map']
