from odoo import api, fields, models


class LoyaltyProgram(models.Model):
    _name = "loyalty.program"
    _inherit = ["loyalty.program", "mixin.website.multi"]

    ecommerce_ok = fields.Boolean(
        string="Available on Website",
        default=True,
    )
    show_non_published_product_warning = fields.Boolean(
        compute="_compute_show_non_published_product_warning"
    )

    @api.depends("program_type", "trigger_product_ids.website_published")
    def _compute_show_non_published_product_warning(self):
        for program in self:
            program.show_non_published_product_warning = (
                program.program_type == "ewallet"
                and any(
                    not product.website_published
                    for product in program.trigger_product_ids
                )
            )

    def action_program_share(self):
        self.check_singleton()
        return self.env["coupon.share"].create_share_action(program=self)
