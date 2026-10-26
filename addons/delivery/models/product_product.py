from odoo import _, models
from odoo.exceptions import RedirectWarning


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _get_product_mpid(self):
        product_mpid = self.env["ir.module.module"].search(
            [("name", "=", "product_mpid"), ("state", "=", "installed")], limit=1
        )
        if product_mpid:
            return self.manufacturing_pid

        raise RedirectWarning(
            message=_(
                "The module '%s' is required to retrieve the product Manufacturing PID.",
                "product_mpid",
            ),
            action={
                "name": _("Install %s") % product_mpid.shortdesc,
                "type": "ir.actions.act_window",
                "res_model": "ir.module.module",
                "res_id": product_mpid.id,
                "view_mode": "form",
                "views": [(False, "form")],
                "target": "current",
            },
            button_text=_("Go to Module Installation"),
        )
