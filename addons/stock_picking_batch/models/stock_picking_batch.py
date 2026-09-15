from odoo import _, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class StockPickingBatch(models.Model):
    _inherit = "stock.picking.batch"

    def action_print(self):
        _debug.lifecycle("batch_print", batches=self)
        self.check_singleton()
        return self.env.ref(
            "stock_picking_batch.action_report_picking_batch"
        ).report_action(self)

    def action_merge(self):
        _debug.pipeline("batch_merge_enter", batches=self)
        if not self:
            return None
        if len(self) < 2:
            raise UserError(
                self.env._("Please select at least two batch/wave transfers to merge.")
            )
        if len(self.picking_type_id) > 1:
            raise UserError(
                _(
                    "Batch/Wave transfers with different operation types cannot be merged."
                )
            )
        if len(set(self.mapped("is_wave"))) > 1:
            raise UserError(
                _(
                    "Batch transfers cannot be merged with wave transfers and vice versa."
                )
            )
        if len(set(self.mapped("state"))) > 1:
            raise UserError(
                _("Batch/Wave transfers with different states cannot be merged.")
            )
        if self[:1].state in ["done", "cancel"]:
            raise UserError(
                _("You cannot merge done or cancelled batch/wave transfers.")
            )

        target_batch = self[:1]
        other_batches = self[1:]
        planned_batches = self.filtered("date_planned").sorted("date_planned")
        earliest_batch = planned_batches[:1] or target_batch
        merged_batch_vals = earliest_batch._prepare_merged_batch_vals()
        target_batch.picking_ids |= other_batches.picking_ids
        target_batch.write(merged_batch_vals)
        other_batches.unlink()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _(
                    "Batch/Wave transfers have been merged into the following transfer"
                ),
                "message": "%s",
                "links": [
                    {
                        "label": target_batch.name,
                        "url": f"/odoo/action-stock_picking_batch.{'action_picking_tree_wave' if target_batch.is_wave else 'stock_picking_batch_action'}/{target_batch.id}",
                    }
                ],
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def action_batch_detailed_operations(self):
        _debug.lifecycle("batch_detailed_operations", batches=self)
        self.check_singleton()
        view_id = self.env.ref("stock_picking_batch.view_stock_move_line_list").id
        return {
            "name": _("Detailed Operations"),
            "view_mode": "list",
            "type": "ir.actions.act_window",
            "res_model": "stock.move.line",
            "views": [(view_id, "list")],
            "domain": [("id", "in", self.picking_ids.move_line_ids.ids)],
            "context": {
                "default_company_id": self.company_id.id,
                "default_picking_id": self.picking_ids[:1].id,
                "picking_ids": self.picking_ids.ids,
                "show_lots_text": self.show_lots_text,
                "picking_code": self.picking_type_code,
                "create": self.state not in ("done", "cancel"),
            },
        }

    def _track_subtype(self, init_values):
        if "state" in init_values:
            return self.env.ref("stock.mt_batch_state")
        return super()._track_subtype(init_values)
