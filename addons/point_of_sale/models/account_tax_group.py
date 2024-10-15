from odoo import api, models
from odoo.addons import account, point_of_sale


class AccountTaxGroup(account.AccountTaxGroup, point_of_sale.PosLoadMixin):

    @api.model
    def _load_pos_data_domain(self, data):
        tax_group_ids = [tax_data['tax_group_id'] for tax_data in data['account.tax']['data']]
        return [('id', 'in', tax_group_ids)]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'pos_receipt_label']
