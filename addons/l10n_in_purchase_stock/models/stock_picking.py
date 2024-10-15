# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons import purchase_stock, l10n_in_stock


class StockPicking(l10n_in_stock.StockPicking, purchase_stock.StockPicking):

    def _get_l10n_in_dropship_dest_partner(self):
        self.ensure_one()
        if line_id := self.purchase_id:
            return line_id.dest_address_id
        return False

    def _l10n_in_get_fiscal_position(self):
        self.ensure_one()
        if purchase_order := self.purchase_id:
            purchase_order.fiscal_position_id
        return super()._l10n_in_get_fiscal_position()
