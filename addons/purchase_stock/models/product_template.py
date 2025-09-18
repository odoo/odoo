from odoo import api, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    # ------------------------------------------------------------
    # ONCHANGE METHODS
    # ------------------------------------------------------------

    @api.onchange("route_ids", "purchase_ok")
    def _onchange_buy_route(self):
        if self.purchase_ok:
            return
        buy_routes = (
            self.env["stock.rule"]
            .search(
                [
                    ("action", "=", "buy"),
                    ("picking_type_id.code", "=", "incoming"),
                    ("active", "=", True),
                ],
            )
            .route_id
        )
        if any(route in self.route_ids._origin for route in buy_routes):
            return {
                "warning": {
                    "title": self.env._("Warning!"),
                    "message": self.env._(
                        'This product has the "Buy" route checked but is not purchasable.',
                    ),
                },
            }
