from odoo import api, fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    team_id = fields.Many2one(
        comodel_name="team.team",
        string="Sales Team",
        index="btree_not_null",
        domain=[("use_sale", "=", True)],
        ondelete="set null",
        help="This Point of sale's sales will be related to this Sales Team.",
    )
    down_payment_product_id = fields.Many2one(
        comodel_name="product.product",
        help="This product will be used as down payment on a sale order.",
    )

    def _get_special_products(self):
        res = super()._get_special_products()
        return res | self.env["pos.config"].search([]).mapped("down_payment_product_id")

    @api.model
    def _update_downpayment_product(self):
        pos_config = self.env.ref(
            "point_of_sale.pos_config_main", raise_if_not_found=False
        )
        downpayment_product = self.env.ref(
            "pos_sale.default_downpayment_product", raise_if_not_found=False
        )
        if pos_config and downpayment_product:
            pos_config.write({"down_payment_product_id": downpayment_product.id})

    @api.model
    def load_onboarding_furniture_scenario(self, with_demo_data=True):
        res = super().load_onboarding_furniture_scenario(with_demo_data)
        self._update_downpayment_product()
        return res
