# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    @api.model
    def _load_pos_data_fields(self, config):
        fields = super()._load_pos_data_fields(config)
        # Adding the field in the data so that it is available in batch_for_taxes_computation
        fields.append('is_withholding_tax_on_payment')
        return fields
