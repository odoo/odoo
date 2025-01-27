from odoo import api, models


class AccountTaxGroup(models.Model):
    _name = 'account.tax.group'
    _inherit = ['account.tax.group', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data):
        tax_group_ids = [tax_data['tax_group_id'] for tax_data in data['account.tax']['data']]
        return [('id', 'in', tax_group_ids)]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'name', 'pos_receipt_label']
