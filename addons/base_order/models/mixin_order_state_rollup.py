from odoo import models
from odoo.libs.debug_log import DebugLog

STATE_NOTHING = "no"
STATE_TODO = "to do"
STATE_PARTIAL = "partial"
STATE_DONE = "done"
STATE_OVER_DONE = "over done"

_debug = DebugLog(__name__)


class MixinOrderStateRollup(models.AbstractModel):
    _name = "mixin.order.state.rollup"
    _description = "Order Line State Rollup"

    def _get_domain_rollup_lines(self):
        return [
            ("is_downpayment", "=", False),
            ("display_type", "=", False),
        ]

    def _get_domain_rollup_pending_lines(self, state_field):
        return []

    def _rollup_line_states(self, state_field, nothing_may_be_pending=False):
        lines_domain = self._get_domain_rollup_lines()
        lines = self.env[self._get_line_model()]

        states_per_order = {}
        for order, state in lines._read_group(
            lines_domain + [("order_id", "in", self._origin.ids)],
            ["order_id", state_field],
        ):
            states_per_order.setdefault(order.id, set()).add(state)

        ambiguous_ids = [
            order._origin.id
            for order in self
            if nothing_may_be_pending
            and STATE_NOTHING in states_per_order.get(order._origin.id, set())
        ]
        pending_ids = set()
        if ambiguous_ids:
            pending_ids = {
                order.id
                for (order,) in lines._read_group(
                    lines_domain
                    + self._get_domain_rollup_pending_lines(state_field)
                    + [
                        ("order_id", "in", ambiguous_ids),
                        (state_field, "=", STATE_NOTHING),
                        ("product_qty", "!=", 0),
                    ],
                    ["order_id"],
                )
            }
        _debug.perf.count(
            "line_states_rolled_up",
            model=self._name,
            field=state_field,
            orders=len(states_per_order),
            ambiguous=len(ambiguous_ids),
            pending=len(pending_ids),
        )
        return states_per_order, pending_ids
