from odoo import models


class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    def _load_pos_self_data_search_read(self, data, config_id):
        return self._load_pos_data_search_read(data, config_id)
