from odoo import api, models
from odoo.fields import Domain


class IrUiView(models.Model):
    _inherit = "ir.ui.view"

    @api.model
    def _get_domain_shipping_modules(self):
        # a view an imported module carries is a custom view
        return super()._get_domain_shipping_modules() & Domain("imported", "=", False)
