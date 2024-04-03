from odoo import models


class PickupLocationMixin(models.AbstractModel):
    _inherit = 'pickup.location.mixin'

    def _is_in_stock(self, wh_id):
        """ Check whether all storable products of the cart are in stock in the given warehouse.

        :param int wh_id: The warehouse in which to check the stock, as a `stock.warehouse` id.
        :return: Whether all storable products are in stock.
        :rtype: bool
        """
        return not self._get_unavailable_lines(wh_id)
