from odoo import models


class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    def _load_pos_self_data(self, data):
        return self._load_pos_data(data)
