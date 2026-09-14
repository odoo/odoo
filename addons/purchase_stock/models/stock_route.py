from odoo import models


class StockRoute(models.Model):
    _inherit = "stock.route"

    def _has_buy_rule(self):
        # whether a route buys is a fact about the route, not about which of
        # its rules the user's companies let them read: a shared route carries
        # every company's buy rule, and a sudo read may already have cached them
        return any(rule.action == "buy" for rule in self.sudo().rule_ids)

    def _is_valid_resupply_route_for_product(self, product):
        if self._has_buy_rule():
            return bool(product.seller_ids)

        return super()._is_valid_resupply_route_for_product(product)
