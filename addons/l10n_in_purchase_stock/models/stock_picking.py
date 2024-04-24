# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _get_l10n_in_dropship_dest_partner(self):
        self.ensure_one()
        return self.purchase_id.dest_address_id

    def _l10n_in_get_fiscal_position(self):
        self.ensure_one()
        if res := super()._l10n_in_get_fiscal_position():
            return res
        return self.purchase_id.fiscal_position_id
