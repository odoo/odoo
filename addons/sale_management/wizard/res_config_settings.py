# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    def set_values(self):
        super().set_values()
        if mandatory_product_view := self.env.ref(
            "sale_management.sale_order_template_view_form_mandatory_product",
            raise_if_not_found=False,
        ):
            mandatory_product_view.active = self.sale_order_mandatory_product
