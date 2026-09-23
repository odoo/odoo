from odoo import SUPERUSER_ID, Command, api, fields, models
from odoo.api import DomainType
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.tools import SQL, Query

from . import approval_trace as trace

VERDICTS = [
    ("approved", "Approved"),
    ("refused", "Refused"),
    ("withdrawn", "Withdrawn"),
    ("granted", "Granted without a decision"),
    ("revoked", "Revoked"),
    ("cancelled", "Cancelled"),
    ("reset", "Reset to draft"),
]


class ApprovalDecisionLog(models.Model):
    """What was decided about a request, by whom, as whom, and under what elevation.

    The approver rows and the request carry the current decision and are
    rewritten by withdrawal, reset and revocation; this model is what they used
    to be. Rows are created only by the engine's funnels and never change.
    """

    _name = "approval.decision.log"
    _description = "Approval Decision"
    _order = "date desc, id desc"
    _rec_name = "verdict"

    request_id = fields.Many2one(
        comodel_name="approval.request",
        index=True,
        readonly=True,
        required=True,
        ondelete="restrict",
    )
    company_id = fields.Many2one(
        related="request_id.company_id",
    )
    approver_id = fields.Many2one(
        comodel_name="approval.approver",
        readonly=True,
        ondelete="set null",
    )
    step_ids = fields.Many2many(
        comodel_name="approval.category.step",
        relation="approval_decision_log_step_rel",
        readonly=True,
    )
    verdict = fields.Selection(
        selection=VERDICTS,
        readonly=True,
        required=True,
    )
    state_after = fields.Char(readonly=True)
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Acted By",
        readonly=True,
        required=True,
        ondelete="restrict",
    )
    principal_id = fields.Many2one(
        comodel_name="res.users",
        string="On Behalf Of",
        readonly=True,
        ondelete="restrict",
        help="The approver whose row a delegate decided.",
    )
    elevation = fields.Selection(
        selection=[
            ("none", "Own rights"),
            ("superuser", "Superuser"),
            ("self_elevated", "Elevated by sudo()"),
        ],
        readonly=True,
        required=True,
    )
    refusal_reason_id = fields.Many2one(
        comodel_name="approval.refusal.reason",
        readonly=True,
        ondelete="set null",
    )
    note = fields.Text(readonly=True)
    date = fields.Datetime(
        default=fields.Datetime.now,
        readonly=True,
        required=True,
    )

    # A decision is readable exactly where its request is. An ir.rule cannot say
    # that: rule domains are evaluated as superuser, so `request_id any []` would
    # skip the request's own rules and expose every decision.
    @api.model
    def _search(
        self,
        domain: DomainType,
        offset: int = 0,
        limit: int | None = None,
        order: str | None = None,
        *,
        bypass_access: bool = False,
        **kwargs,
    ) -> Query:
        if not (self.env.su or bypass_access):
            domain = Domain(domain) & Domain(
                "request_id", "in", self.env["approval.request"]._search([])
            )
        return super()._search(
            domain, offset, limit, order, bypass_access=bypass_access, **kwargs
        )

    def _check_access(self, operation: str) -> tuple | None:
        result = super()._check_access(operation)
        if operation != "read" or not self or self.env.su:
            return result
        remaining = self - result[0] if result else self
        requests = remaining.sudo().request_id.with_env(self.env)
        hidden = requests - requests._filtered_access("read")
        if not hidden:
            return result
        forbidden = remaining.filtered(lambda log: log.sudo().request_id in hidden)
        denied = hidden._check_access("read")[1]
        if result:
            return result[0] + forbidden, result[1]
        return forbidden, denied

    def write(self, vals):
        if not self:
            return True
        trace.REFUSAL.event("decision_log_rewritten", rows=self.ids)
        raise UserError(self.env._("A recorded approval decision cannot be changed."))

    @api.ondelete(at_uninstall=False)
    def _unlink_never(self):
        trace.REFUSAL.event("decision_log_deleted", rows=self.ids)
        raise UserError(self.env._("A recorded approval decision cannot be deleted."))


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    decision_log_ids = fields.One2many(
        comodel_name="approval.decision.log",
        inverse_name="request_id",
        string="Decision History",
        compute="_compute_decision_log_ids",
        compute_sudo=True,
    )

    def _compute_decision_log_ids(self):
        # Read through the request: whoever may read the request may read what
        # was decided about it, without the log needing rules of its own.
        logs = self.env["approval.decision.log"].search(
            [("request_id", "in", self.ids)]
        )
        by_request = logs.grouped("request_id")
        for request in self:
            request.decision_log_ids = by_request.get(request, logs.browse())

    def _decision_elevation(self) -> str:
        if not self.env.su:
            return "none"
        return "superuser" if self.env.uid == SUPERUSER_ID else "self_elevated"

    def _append_decision_log(
        self,
        verdict,
        rows=None,
        actor=None,
        steps_by_row=None,
        reason=None,
        note=None,
        date=None,
    ) -> None:
        """Record one fact per row it concerns, or one for the request itself.

        Called by every funnel that changes what is decided, BEFORE a funnel that
        erases the rows' decision fields runs, and after one that sets them.
        """
        self.check_singleton()
        acting = actor or self.env.user
        elevation = self._decision_elevation()
        vals_list = []
        for row in rows or [None]:
            principal = row.user_id if row is not None else False
            steps = (steps_by_row or {}).get(row.id) if row is not None else None
            vals_list.append(
                {
                    "request_id": self.id,
                    "approver_id": row.id if row is not None else False,
                    "step_ids": [Command.set(steps.ids)] if steps else False,
                    "verdict": verdict,
                    "user_id": acting.id,
                    "principal_id": principal.id
                    if principal and principal != acting
                    else False,
                    "elevation": elevation,
                    "refusal_reason_id": (
                        reason.id
                        if reason
                        else (row.refusal_reason_id.id if row is not None else False)
                    )
                    or False,
                    "note": note or (row.note if row is not None else False) or False,
                    **({"date": date} if date else {}),
                }
            )
        logs = self.env["approval.decision.log"].sudo().create(vals_list)
        state_after = self.state
        self.env.cr.execute(
            SQL(
                "UPDATE approval_decision_log SET state_after = %s WHERE id = ANY(%s)",
                state_after,
                logs.ids,
            )
        )
        logs.invalidate_recordset(["state_after"])
        trace.DECISION.note(
            "logged",
            request=self.id,
            verdict=verdict,
            actor=acting.id,
            elevation=elevation,
            rows=len(vals_list),
        )
