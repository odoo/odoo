from odoo import api, models
from odoo.addons import point_of_sale, account_tax_python


class AccountTax(account_tax_python.AccountTax, point_of_sale.AccountTax):

    @api.model
    def _load_pos_data_fields(self, config_id):
        return super()._load_pos_data_fields(config_id) + ['formula_decoded_info']
