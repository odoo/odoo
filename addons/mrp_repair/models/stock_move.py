# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _get_dest_account(self, accounts_data):
        if self.repair_line_type == 'add' and self.repair_id.under_warranty:
            return accounts_data['expense'].id
        elif self.repair_line_type:
            return accounts_data['stock_output'].id
        return super()._get_dest_account(accounts_data)
