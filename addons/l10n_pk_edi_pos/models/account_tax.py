from odoo import api, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    @api.model
    def _load_pos_data_fields(self, config):
        result = super()._load_pos_data_fields(config)
        if config.l10n_pk_edi_pos_enabled:
            result += ['l10n_pk_is_further_tax']
        return result
