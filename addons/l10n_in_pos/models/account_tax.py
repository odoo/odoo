from odoo import api, models
from odoo.addons import point_of_sale, l10n_in


class AccountTax(l10n_in.AccountTax, point_of_sale.AccountTax):

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields = super()._load_pos_data_fields(config_id)
        fields += ['l10n_in_tax_type']
        return fields
