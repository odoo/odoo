from odoo import api, models


class AccountTaxGroup(models.Model):
    _name = 'account.tax.group'
    _inherit = ['account.tax.group', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data):
        return [('id', 'in', data['account.tax'].tax_group_id.ids)]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'name', 'pos_receipt_label']
