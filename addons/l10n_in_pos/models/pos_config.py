# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _get_closing_entry_by_product(self):
        if self.company_id.account_fiscal_country_id.code == 'IN':
            return True
        return super()._get_closing_entry_by_product()
