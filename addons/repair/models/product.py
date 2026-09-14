from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class ProductProduct(models.Model):
    _inherit = "product.product"

    product_catalog_product_is_in_repair = fields.Boolean(
        compute="_compute_product_catalog_product_is_in_repair",
        search="_search_product_catalog_product_is_in_repair",
    )

    def _compute_product_catalog_product_is_in_repair(self):
        # Just to enable the _search method
        self.product_catalog_product_is_in_repair = False

    def _search_product_catalog_product_is_in_repair(self, operator, value):
        if operator != "in":
            return NotImplemented
        product_ids = (
            self.env["repair.order"]
            .search(
                [
                    ("id", "in", [self.env.context.get("order_id", "")]),
                ]
            )
            .move_ids.product_id.ids
        )
        return [("id", "in", product_ids)]

    def _update_uom(self, to_uom_id):
        _debug.lifecycle("repair_product_uom_update", products=self, to_uom=to_uom_id)
        self._restamp_uom("repair.order", to_uom_id)
        return super()._update_uom(to_uom_id)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    service_tracking = fields.Selection(
        selection_add=[("repair", "Repair Order")],
        ondelete={"repair": "set default"},
    )

    @api.model
    def _get_saleable_tracking_types(self):
        return super()._get_saleable_tracking_types() + ["repair"]
