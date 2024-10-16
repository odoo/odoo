from odoo import models
from odoo.addons import pos_restaurant


class AccountFiscalPosition(pos_restaurant.AccountFiscalPosition):

    def _load_pos_self_data(self, data):
        return self._load_pos_data(data)
