from odoo import models
from odoo.exceptions import UserError


class StockLot(models.Model):
    _inherit = "stock.lot"

    def _check_lots_allowed(self, product_ids):
        active_mo_id = self.env.context.get("active_mo_id")
        if active_mo_id:
            active_mo = self.env["mrp.production"].browse(active_mo_id)
            component_product_ids = set(active_mo.move_raw_ids.product_id.ids)
            if (
                not active_mo.picking_type_id.use_create_components_lots
                and set(product_ids) & component_product_ids
            ):
                raise UserError(
                    self.env._(
                        'You are not allowed to create or edit a lot or serial number for the components with the operation type "Manufacturing". To change this, go on the operation type and tick the box "Create New Lots/Serial Numbers for Components".'
                    )
                )
        return super()._check_lots_allowed(product_ids)
