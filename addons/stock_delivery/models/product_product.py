from odoo import _, models
from odoo.exceptions import RedirectWarning


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _get_product_nspid(self):
        product_nspid = self.env["ir.module.module"].search(
            [("name", "=", "product_nspid")], limit=1
        )
        if product_nspid.state == "installed":
            return self.manufacturing_pid or self.default_code

        raise RedirectWarning(
            message=_(
                "The module '%s' is required to retrieve the product Manufacturing PID.",
                "product_nspid",
            ),
            action={
                "name": _("Install %s", product_nspid.shortdesc),
                "type": "ir.actions.act_window",
                "res_model": "ir.module.module",
                "res_id": product_nspid.id,
                "view_mode": "form",
                "views": [(False, "form")],
                "target": "current",
            },
            button_text=_("Go to Module Installation"),
        )
