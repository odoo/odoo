# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.tools import float_round


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _l10n_jp_printed_unit_prices(self):
        """The unit prices the report prints, rounded the way it prints them.

        A negative discount is a surcharge, and the report prints the surcharged
        price rather than the one on the line, so that is the value that decides
        whether the column can drop its decimals.
        """
        self.ensure_one()
        precision = self.env['decimal.precision'].precision_get('Product Price')
        return [
            float_round((1 - line.discount / 100.0) * line.price_unit, precision_digits=precision)
            if line.discount < 0 else line.price_unit
            for line in self.order_line
        ]
