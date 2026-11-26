# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _is_taxable_supply_date_used(self):
        # EXTENDS 'account'
        return self.country_code == 'BG' or super()._is_taxable_supply_date_used()
