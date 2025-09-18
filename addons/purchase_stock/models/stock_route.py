from odoo import models



class StockRoute(models.Model):
    _inherit = "stock.route"

    # ------------------------------------------------------------
    # VALIDATION METHODS
    # ------------------------------------------------------------

    def _is_valid_resupply_route_for_product(self, product):
        if any(rule.action == "buy" for rule in self.rule_ids):
            return bool(product.seller_ids)

        return super()._is_valid_resupply_route_for_product(product)
