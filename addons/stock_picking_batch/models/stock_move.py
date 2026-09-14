from odoo import models
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"

    def _get_domain_picking_for_assignation(self):
        domain = super()._get_domain_picking_for_assignation()
        return Domain.AND(
            [domain, ["|", ("batch_id", "=", False), ("batch_id.is_wave", "=", False)]]
        )

    def _action_cancel(self):
        _debug.pipeline("batched_move_cancel", moves=self)
        res = super()._action_cancel()

        for picking in self.picking_id:
            if (
                picking.state == "cancel"
                and picking.batch_id
                and any(p.state != "cancel" for p in picking.batch_id.picking_ids)
            ):
                picking.batch_id = None
        return res

    def _post_process_picking(self, new=False):
        _debug.pipeline("batched_picking_post_process", moves=self, new=new)
        super()._post_process_picking(new=new)
        for picking in self.picking_id:
            picking._resolve_auto_batch()

    def write(self, vals):
        res = super().write(vals)
        if "state" in vals and vals["state"] in ("partially_available", "assigned"):
            for picking in self.picking_id:
                if picking.state != "assigned":
                    continue
                picking._resolve_auto_batch()

        return res

    def _action_assign(self, force_qty=False):
        super()._action_assign(force_qty=force_qty)
        self.move_line_ids._auto_wave()

    def action_show_details(self):
        action = super().action_show_details()
        if self.picking_id.batch_id:
            action["context"]["default_picking_id"] = self.picking_id.id
        return action
