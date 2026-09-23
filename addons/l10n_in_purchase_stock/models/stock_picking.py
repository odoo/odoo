from odoo import models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _get_l10n_in_dropship_dest_partner(self):
        self.check_singleton()
        if line_id := self.purchase_id:
            return line_id.dest_address_id
        return False

    def _l10n_in_get_fiscal_position(self):
        self.check_singleton()
        if purchase_order := self.purchase_id:
            return purchase_order.fiscal_position_id
        return super()._l10n_in_get_fiscal_position()
