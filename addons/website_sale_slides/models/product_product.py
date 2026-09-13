from odoo import _, fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    channel_ids = fields.One2many(
        comodel_name="slide.channel",
        inverse_name="product_id",
        string="Courses",
    )

    def _is_add_to_cart_allowed(self):
        self.check_singleton()
        res = super()._is_add_to_cart_allowed()
        return res or bool(
            self.env["slide.channel"]
            .sudo()
            .search_count(
                [
                    ("product_id", "=", self.id),
                    ("website_published", "=", True),
                ],
                limit=1,
            )
        )

    def get_product_multiline_description_sale(self):
        payment_channels = self.channel_ids.filtered(
            lambda course: course.enroll == "payment"
        )

        if not payment_channels:
            return super().get_product_multiline_description_sale()

        new_line = "" if len(payment_channels) == 1 else "\n"
        return _(
            "Access to: %(new_line)s%(channel_list)s",
            new_line=new_line,
            channel_list="\n".join(payment_channels.mapped("name")),
        )
