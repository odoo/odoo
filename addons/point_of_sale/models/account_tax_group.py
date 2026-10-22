from odoo import api, models


class AccountTaxGroup(models.Model):
    _name = 'account.tax.group'
    _inherit = ['account.tax.group', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data, config):
        # On an incremental load, data['account.tax'] only holds the taxes
        # modified since the last sync, not all the loaded ones.
        tax_domain = self.env['account.tax']._load_pos_data_domain(data, config)
        return [('id', 'in', self.env['account.tax'].search(tax_domain).tax_group_id.ids)]

    @api.model
    def _load_pos_data_fields(self, config):
        return ['id', 'name', 'pos_receipt_label']
