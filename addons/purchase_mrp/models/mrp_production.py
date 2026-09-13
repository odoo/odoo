from odoo import Command, _, api, fields, models


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    purchase_order_count = fields.Integer(
        string="Count of generated PO",
        compute="_compute_purchase_order_count",
        groups="purchase.group_purchase_user",
    )

    @api.depends(
        "move_raw_ids.created_purchase_line_ids.order_id",
        "move_raw_ids.purchase_line_id.order_id",
        "move_raw_ids.move_orig_ids.created_purchase_line_ids.order_id",
        "move_raw_ids.move_orig_ids.purchase_line_id.order_id",
    )
    def _compute_purchase_order_count(self):
        for production in self:
            production.purchase_order_count = len(production._get_purchase_orders())

    def action_view_purchase_orders(self):
        self.check_singleton()
        purchase_order_ids = self._get_purchase_orders().ids
        action = {
            "res_model": "purchase.order",
            "type": "ir.actions.act_window",
        }
        if len(purchase_order_ids) == 1:
            action.update(
                {
                    "view_mode": "form",
                    "res_id": purchase_order_ids[0],
                }
            )
        else:
            action.update(
                {
                    "name": _("Purchase Order generated from %s", self.name),
                    "domain": [("id", "in", purchase_order_ids)],
                    "view_mode": "list,form",
                }
            )
        return action

    def _get_document_iterate_key(self, move_raw_id):
        iterate_key = super()._get_document_iterate_key(move_raw_id)
        if not iterate_key and move_raw_id.created_purchase_line_ids:
            iterate_key = "created_purchase_line_ids"
        return iterate_key

    def _get_purchase_orders(self):
        self.check_singleton()
        moves = self.move_raw_ids | self.move_raw_ids.move_orig_ids
        purchase_lines = moves.mapped("created_purchase_line_ids") | moves.mapped(
            "purchase_line_id"
        )
        return purchase_lines.mapped("order_id")

    def _prepare_merge_orig_links(self):
        origs = super()._prepare_merge_orig_links()
        for move in self.move_raw_ids:
            if not move.created_purchase_line_ids:
                continue
            origs[move.bom_line_id.id].setdefault(
                "created_purchase_line_ids", set()
            ).update(move.created_purchase_line_ids.ids)
        for vals in origs.values():
            if vals.get("created_purchase_line_ids"):
                vals["created_purchase_line_ids"] = [
                    Command.set(vals["created_purchase_line_ids"])
                ]
        return origs
