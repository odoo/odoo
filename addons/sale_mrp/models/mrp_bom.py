from odoo import _, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class MrpBom(models.Model):
    _inherit = "mrp.bom"

    def _check_bom_is_free(self):
        product_ids = []
        for bom in self:
            if not bom.active or bom.type != "phantom":
                continue
            product_ids += (
                bom.product_id.ids or bom.product_tmpl_id.product_variant_ids.ids
            )
        if not product_ids:
            return
        owed = ("no", "to do", "partial")
        lines = (
            self.env["sale.order.line"]
            .sudo()
            .search(
                [
                    ("state", "=", "done"),
                    ("product_id", "in", product_ids),
                    ("move_ids.state", "!=", "cancel"),
                    "|",
                    ("invoice_state", "in", owed),
                    ("transfer_state", "in", owed),
                ]
            )
        )
        if lines:
            product_names = ", ".join(lines.product_id.mapped("display_name"))
            _debug.logic("bom_change_refused", boms=self, order_lines=lines)
            raise UserError(
                _(
                    "As long as there are some sale order lines that must be delivered/invoiced and are "
                    "related to these bills of materials, you can not remove them.\n"
                    "The error concerns these products: %s",
                    product_names,
                )
            )

    def write(self, vals):
        if not vals.get("active", True) or vals.get("type", "phantom") != "phantom":
            self._check_bom_is_free()
        return super().write(vals)

    def unlink(self):
        self._check_bom_is_free()
        return super().unlink()
