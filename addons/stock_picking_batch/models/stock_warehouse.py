from odoo import models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    def _prepare_picking_type_create_vals(self):
        data = super()._prepare_picking_type_create_vals()
        updatable_types = {
            k: v for (k, v) in data.items() if v.get("code") in ("incoming", "outgoing")
        }
        _debug.logic(
            "warehouse_types_auto_batched",
            warehouses=self,
            types=sorted(updatable_types),
        )
        for picking_type in updatable_types.values():
            picking_type.update(
                {
                    "auto_batch": True,
                    "batch_group_by_partner": True,
                }
            )
        return data
