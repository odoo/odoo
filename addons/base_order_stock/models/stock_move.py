from odoo import api, models
from odoo.fields import Command
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"

    def _get_fields_linking_order_lines(self):
        return []

    @api.depends(
        lambda self: [
            path
            for link, _created in self._get_fields_linking_order_lines()
            for path in (link, f"{link}.product_uom_id")
        ],
    )
    def _compute_packaging_uom_id(self):
        super()._compute_packaging_uom_id()
        for move in self:
            for link, _created in move._get_fields_linking_order_lines():
                line = move[link]
                if line and move.product_uom_id._has_common_reference(
                    line.product_uom_id,
                ):
                    move.packaging_uom_id = line.product_uom_id
                    break

    def _update_merged_moves(self):
        _debug.pipeline("merged_moves_update", moves=self)
        super()._update_merged_moves()
        cleared = {
            created: [Command.clear()]
            for _link, created in self._get_fields_linking_order_lines()
        }
        if cleared:
            self.write(cleared)

    def _get_source_document(self):
        res = super()._get_source_document()
        for link, _created in self._get_fields_linking_order_lines():
            if order := self[link].order_id:
                return order
        return res

    def _prepare_merge_moves_distinct_fields(self):
        distinct_fields = super()._prepare_merge_moves_distinct_fields()
        for link, created in self._get_fields_linking_order_lines():
            distinct_fields += [link, created]
        return distinct_fields

    def _prepare_merge_negative_moves_excluded_distinct_fields(self):
        return super()._prepare_merge_negative_moves_excluded_distinct_fields() + [
            created for _link, created in self._get_fields_linking_order_lines()
        ]

    def _prepare_move_split_vals(self, uom_qty, force_uom_id=False):
        _debug.logic("move_split_vals", moves=self, uom_qty=uom_qty)
        vals = super()._prepare_move_split_vals(uom_qty, force_uom_id=force_uom_id)
        for link, created in self._get_fields_linking_order_lines():
            if self.procure_method == "make_to_order" and self[created]:
                vals[created] = [Command.set(self[created].ids)]
            vals[link] = self[link].id
        return vals
