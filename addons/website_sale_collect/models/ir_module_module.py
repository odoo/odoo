# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrModuleModule(models.Model):
    _inherit = "ir.module.module"

    def _get_provided_delivery_type(self):
        """Override of `delivery` to return the in-store delivery type."""
        self.ensure_one()
        if self.name == "website_sale_collect":
            return "in_store"
        return super()._get_provided_delivery_type()
