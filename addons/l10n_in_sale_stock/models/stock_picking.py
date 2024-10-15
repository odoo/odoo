# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons import sale_stock, l10n_in_stock


class StockPicking(l10n_in_stock.StockPicking, sale_stock.StockPicking):


    def _l10n_in_get_invoice_partner(self):
        self.ensure_one()
        if line_id := self.sale_id:
            return line_id.partner_invoice_id
        return False

    def _l10n_in_get_fiscal_position(self):
        self.ensure_one()
        if sale_order := self.sale_id:
            return sale_order.fiscal_position_id
        return super()._l10n_in_get_fiscal_position()
