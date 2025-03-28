# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _set_shop_warning_stock(self, desired_qty, new_qty):
        self.ensure_one()
        self.shop_warning = _(
            'You ask for %(desired_qty)s %(product_name)s but only %(new_qty)s is available',
            desired_qty=desired_qty, product_name=self.product_id.name, new_qty=new_qty
        )
        return self.shop_warning

    def _get_max_line_qty(self):
        max_quantity = self._get_max_available_qty()
        return self.product_uom_qty + max_quantity if (max_quantity is not None) else None

    def _get_max_available_qty(self):
        """ The max quantity of a combo product is the max quantity of its selected combo item with
        the lowest max quantity. If none of the combo items has a max quantity, then the combo
        product also has no max quantity.
        """
        website = self.order_id.website_id
        max_quantities = [
            max_quantity for product in self._get_lines_with_price().product_id
            if (max_quantity := product._get_max_quantity(website)) is not None
        ]
        return min(max_quantities, default=None)
