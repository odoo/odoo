from odoo import fields, models
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    # FIELDS
    maintenance_order_id = fields.Many2one(
        comodel_name="maintenance.order",
        index="btree_not_null",
        ondelete="set null",
        check_company=True,
        help="The maintenance this transfer takes the equipment to, or back from.",
    )

    # CONSTRAINT METHODS
    def _check_returned_equipment(self):
        for picking in self.filtered(
            lambda picking: picking.maintenance_order_id and picking.return_id
        ):
            sent = picking.return_id.move_line_ids.lot_id
            extra = picking.move_line_ids.lot_id - sent
            if not sent or not extra:
                continue
            raise ValidationError(
                self.env._(
                    "%(extra)s did not go out on %(transfer)s, so it cannot come back on its return. Expected equipment: %(expected)s",
                    extra=", ".join(extra.mapped("name")),
                    transfer=picking.return_id.display_name,
                    expected=", ".join(sent.mapped("name")),
                )
            )

    # ACTION METHODS
    def action_view_maintenance_order(self):
        self.check_singleton()
        return {
            "type": "ir.actions.act_window",
            "res_model": "maintenance.order",
            "res_id": self.maintenance_order_id.id,
            "view_mode": "form",
            "target": "current",
        }

    # STOCK METHODS
    def _action_done(self):
        self._check_returned_equipment()
        result = super()._action_done()
        maintenance = self.filtered("maintenance_order_id")
        coming_back = maintenance.filtered(
            lambda picking: picking._is_maintenance_return()
        )
        _debug.logic(
            "maintenance_transfers_done",
            pickings=maintenance,
            returns=coming_back,
        )
        for picking in coming_back:
            # sudo: closing the order is a consequence of the equipment coming back,
            # not an edit by whoever receives it, who may have no maintenance rights.
            picking.maintenance_order_id.sudo()._mark_returned(picking)
        (maintenance - coming_back).maintenance_order_id.sudo()._mark_sent()
        return result

    # HELPER METHODS
    def _is_maintenance_return(self):
        self.check_singleton()
        depth, picking = 0, self.return_id
        while picking:
            depth, picking = depth + 1, picking.return_id
        return depth % 2 == 1
