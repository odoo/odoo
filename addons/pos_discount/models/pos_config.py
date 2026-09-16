from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PosConfig(models.Model):
    _inherit = "pos.config"

    iface_discount = fields.Boolean(
        string="Order Discounts",
        help="Allow the cashier to give discounts on the whole order.",
    )
    discount_pc = fields.Float(
        string="Discount Percentage",
        default=10.0,
        help="The default discount percentage when clicking on the Discount button",
    )
    discount_product_id = fields.Many2one(
        comodel_name="product.product",
        domain=[("sale_ok", "=", True)],
        help="The product used to apply the discount on the ticket.",
    )

    @api.model
    def _update_discount_product_on_module_install(self):
        configs = self.env["pos.config"].search([])
        open_configs = (
            self.env["pos.session"]
            .search(["|", ("state", "!=", "closed"), ("rescue", "=", True)])
            .mapped("config_id")
        )
        # Do not modify configs where an opened session exists.
        product = self.env.ref(
            "pos_discount.product_product_consumable", raise_if_not_found=False
        )
        for conf in configs - open_configs:
            conf.discount_product_id = (
                product
                if conf.module_pos_discount
                and product
                and (not product.company_id or product.company_id == conf.company_id)
                else False
            )

    def open_ui(self):
        for config in self:
            if (
                not self.current_session_id
                and config.module_pos_discount
                and not config.discount_product_id
            ):
                raise UserError(
                    _(
                        "A discount product is needed to use the Global Discount feature. Go to Point of Sale > Configuration > Settings to set it."
                    )
                )
        return super().open_ui()

    def _get_special_products(self):
        res = super()._get_special_products()
        default_discount_product = (
            self.env.ref(
                "pos_discount.product_product_consumable", raise_if_not_found=False
            )
            or self.env["product.product"]
        )
        return (
            res
            | self.env["pos.config"].search([]).mapped("discount_product_id")
            | default_discount_product
        )
