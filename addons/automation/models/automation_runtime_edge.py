import logging

from odoo import fields, models
from odoo.tools.date_utils import get_timedelta
from odoo.tools.safe_eval import safe_eval

from .workflow_edge import CONDITION_SELECTION, EDGE_DELAY_UNITS, SETTLED_STATES

_logger = logging.getLogger(__name__)


class AutomationRuntimeEdge(models.Model):
    _name = "automation.runtime.edge"
    _description = "Automation Runtime Edge"
    _order = "runtime_id, id"

    runtime_id = fields.Many2one(
        comodel_name="automation.runtime",
        index=True,
        required=True,
        ondelete="cascade",
    )
    source_line_id = fields.Many2one(
        comodel_name="automation.runtime.line",
        string="Source Step",
        index=True,
        required=True,
        ondelete="cascade",
    )
    target_line_id = fields.Many2one(
        comodel_name="automation.runtime.line",
        string="Target Step",
        index=True,
        required=True,
        ondelete="cascade",
    )
    condition = fields.Selection(
        selection=CONDITION_SELECTION,
        default="on_success",
        readonly=True,
        required=True,
    )
    condition_expr = fields.Char(readonly=True)
    event_code = fields.Char(readonly=True)
    delay = fields.Integer(readonly=True)
    delay_unit = fields.Selection(
        selection=EDGE_DELAY_UNITS,
        readonly=True,
    )
    date_event = fields.Datetime(
        string="Event Received",
        copy=False,
        readonly=True,
    )
    revoked = fields.Boolean(
        copy=False,
        readonly=True,
        help="An exclusive event on the source closed this edge",
    )

    def _verdict(self, now):
        self.check_singleton()
        source = self.source_line_id
        if self.revoked:
            return False, None
        if self.condition == "no_event":
            if self.date_event:
                return False, None
            anchor = source.date_settled
        elif self.condition == "event":
            if not self.date_event:
                return None, None
            anchor = self.date_event
        elif self._is_satisfied():
            anchor = source.date_settled
        else:
            return False, None
        if not self.delay:
            return True, None
        return True, (anchor or now) + get_timedelta(self.delay, self.delay_unit)

    def _is_satisfied(self):
        self.check_singleton()
        state = self.source_line_id.state
        if state not in SETTLED_STATES:
            return False
        if self.condition == "event":
            return bool(self.date_event) and not self.revoked
        if self.condition == "no_event":
            return not self.date_event and not self.revoked
        if self.condition == "on_success":
            return state == "done"
        if self.condition == "on_error":
            return state == "error"
        if self.condition == "always":
            return True
        return self._is_expression_truthy()

    def _is_expression_truthy(self):
        self.check_singleton()
        runtime = self.runtime_id
        context = {
            "runtime": runtime,
            "runtime_line": self.source_line_id,
            "record": runtime._get_target_record(),
            "state": self.source_line_id.state,
        }
        try:
            return bool(safe_eval(self.condition_expr or "False", context))
        except Exception:
            _logger.warning(
                "Edge %s -> %s: condition %r could not be evaluated; "
                "the target stays blocked.",
                self.source_line_id.name,
                self.target_line_id.name,
                self.condition_expr,
                exc_info=True,
            )
            return False
