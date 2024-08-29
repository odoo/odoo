from odoo import models
from odoo.addons import account


class AccountFiscalPosition(models.Model, account.AccountFiscalPosition):

    def _load_pos_self_data(self, data):
        return self._load_pos_data(data)
