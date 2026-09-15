from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog

TRANSFER_STATE = [
    ("no", "Nothing to transfer"),
    ("to do", "To transfer"),
    ("partial", "Partially transferred"),
    ("done", "Fully transferred"),
    ("over done", "Over transferred"),
]


_debug = DebugLog(__name__)


class MixinOrderStock(models.AbstractModel):
    _name = "mixin.order.stock"
    _inherit = ["mixin.order.state.rollup"]
    _description = "Order Stock Integration"

    transfer_state = fields.Selection(
        selection=TRANSFER_STATE,
        string="Transfer Status",
        compute="_compute_transfer_state",
        default="no",
        store=True,
    )
    force_fully_delivered = fields.Boolean(
        copy=False,
        help="Report this order as fully transferred regardless of its lines.",
    )

    date_effective = fields.Datetime(
        string="Effective Date",
        compute="_compute_date_effective",
        store=True,
        copy=False,
    )

    incoterm_id = fields.Many2one(
        comodel_name="account.incoterms",
        help="International Commercial Terms are a series of predefined commercial "
        "terms used in international transactions.",
    )
    incoterm_location = fields.Char()

    @api.depends(
        "state",
        "line_ids.transfer_state",
        "picking_ids",
        "picking_ids.state",
        "force_fully_delivered",
    )
    def _compute_transfer_state(self):
        _debug.perf.count("order_transfer_state_compute", orders=self)
        forced = self.filtered("force_fully_delivered")
        forced.transfer_state = "done"
        confirmed = (self - forced).filtered(lambda order: order.state == "done")
        (self - forced - confirmed).transfer_state = "no"
        if not confirmed:
            return

        states_per_order, _pending_ids = confirmed._rollup_line_states("transfer_state")
        for order in confirmed:
            states = states_per_order.get(order._origin.id, set())
            if not states:
                order.transfer_state = "no"
            elif len(states) == 1:
                order.transfer_state = next(iter(states))
            elif "over done" in states:
                order.transfer_state = "over done"
            elif "partial" in states:
                order.transfer_state = "partial"
            elif "done" in states:
                order.transfer_state = "partial" if "to do" in states else "done"
            elif "to do" in states:
                order.transfer_state = "to do"
            else:
                order.transfer_state = "no"

            if order.transfer_state == "to do" and any(
                picking.state == "done" for picking in order.picking_ids
            ):
                order.transfer_state = "partial"

    @api.depends(
        "picking_ids.date_done",
        "picking_ids.state",
        "picking_ids.location_dest_id.usage",
    )
    def _compute_date_effective(self):
        for order in self:
            pickings = order._get_effective_pickings(order.picking_ids)
            dates = [d for d in pickings.mapped("date_done") if d]
            order.date_effective = min(dates, default=False)

    def _get_effective_pickings(self, pickings):
        return pickings.filtered(
            lambda p: p.state == "done" and p.date_done,
        )

    def action_force_transfer_state(self):
        _debug.lifecycle("transfer_state_forced", orders=self)
        self.force_fully_delivered = True

    def action_unforce_transfer_state(self):
        _debug.lifecycle("transfer_state_unforced", orders=self)
        self.force_fully_delivered = False

    def _get_action_view_picking(self, pickings):
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "stock.action_picking_tree_all",
        )
        if len(pickings) == 1:
            form_view = [(self.env.ref("stock.view_stock_picking_form").id, "form")]
            action["views"] = form_view + [
                (state, view)
                for state, view in action.get("views", [])
                if view != "form"
            ]
            action["res_id"] = pickings.id
        else:
            action["domain"] = [("id", "in", pickings.ids)]
        action["context"] = self._prepare_picking_action_context(pickings)
        return action

    def _prepare_picking_action_context(self, pickings):
        return {}
