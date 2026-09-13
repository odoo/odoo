from odoo import api, fields, models
from odoo.exceptions import UserError

from ..models import approval_trace as trace


class ApprovalDecisionWizard(models.TransientModel):
    _name = "approval.decision.wizard"
    _description = "Approval Decision Wizard"

    approver_id = fields.Many2one(
        comodel_name="approval.approver",
        readonly=True,
        help="The approver record making this decision. Empty in batch mode, "
        "where request_ids carries the targets and each request resolves "
        "its own pending row for the current user.",
    )
    request_ids = fields.Many2many(
        comodel_name="approval.request",
        string="Requests",
        readonly=True,
        help="Batch mode: every request refused with the reason below.",
    )
    request_id = fields.Many2one(
        comodel_name="approval.request",
        string="Approval Request",
        compute="_compute_request_id",
        precompute=True,
        store=True,
        readonly=True,
        help="The approval request being decided. Auto-populated from ``approver_id``.",
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        related="approver_id.user_id",
        string="User",
        readonly=True,
    )
    decision_type = fields.Selection(
        selection=[
            ("refuse", "Refuse"),
            ("change", "Request Change"),
        ],
        string="Decision",
        readonly=True,
        required=True,
        help="Type of decision being made",
    )

    refusal_reason_id = fields.Many2one(
        comodel_name="approval.refusal.reason",
        help="Select the primary reason for ending this request",
    )
    refusal_reason_description = fields.Text(
        related="refusal_reason_id.description",
        readonly=True,
        help="Internal guidance shown to the approver to clarify when "
        "this reason applies. Rendered as a read-only info banner in "
        "the wizard; never persisted on the request or sent to the "
        "requester.",
    )
    change_field = fields.Selection(
        selection=[
            ("date", "Date"),
            ("reason", "Description"),
        ],
        string="Field to Modify",
        help="Field the requester must update before the approver can "
        "decide. Only date and description (reason) are eligible; "
        "amount, lines and other structural data cannot be changed "
        "in-flight.",
    )

    note = fields.Text(
        help="Free-text message to the requester. Required when "
        "requesting a change; optional when refusing."
    )
    request_name = fields.Char(
        related="request_id.name",
        string="Request",
        readonly=True,
    )
    request_owner_id = fields.Many2one(
        comodel_name="res.users",
        related="request_id.request_owner_id",
        string="Request Owner",
        readonly=True,
    )
    category_id = fields.Many2one(
        comodel_name="approval.category",
        related="request_id.category_id",
        string="Category",
        readonly=True,
    )

    @api.depends("approver_id")
    def _compute_request_id(self):
        for wiz in self:
            if wiz.approver_id:
                wiz.request_id = wiz.approver_id.request_id

    def _check_refusal_reason_applicable(self, request) -> None:
        self.check_singleton()
        reason = self.refusal_reason_id
        if reason.category_ids and request.category_id not in reason.category_ids:
            trace.REFUSAL.event(
                "reason_wrong_category",
                request=request.id,
                reason=reason.id,
                category=request.category_id.id,
            )
            raise UserError(
                self.env._(
                    "The reason '%(reason)s' is not available for the "
                    "'%(category)s' category.",
                    reason=reason.name,
                    category=request.category_id.name,
                ),
            )
        if reason.company_id and reason.company_id != request.company_id:
            trace.REFUSAL.event(
                "reason_wrong_company",
                request=request.id,
                reason=reason.id,
                company=request.company_id.id,
            )
            raise UserError(
                self.env._(
                    "The reason '%(reason)s' is restricted to another "
                    "company and cannot be used on this request.",
                    reason=reason.name,
                ),
            )

    def action_confirm_refuse(self):
        self.check_singleton()
        if not self.refusal_reason_id:
            trace.REFUSAL.event(
                "refusal_without_reason",
                request=self.request_id.id,
                approver=self.approver_id.id,
            )
            raise UserError(
                self.env._("Please select a reason for refusing this request.")
            )
        if self.request_ids:
            return self.request_ids._action_bulk_decision(
                "action_refuse",
                "refusal",
                "refused",
                before=self._stamp_refusal,
            )
        if not self.approver_id:
            trace.REFUSAL.event("refusal_without_a_row", wizard=self.id)
            raise UserError(self.env._("There is no approval to refuse."))
        trace.WIZARD.note(
            "refuse",
            request=self.request_id.id,
            approver=self.approver_id.id,
            reason=self.refusal_reason_id.id,
            noted=bool(self.note),
        )
        self._stamp_refusal(self.request_id, self.approver_id)
        self.approver_id.with_context(skip_wizard=True).action_refuse()
        return {"type": "ir.actions.act_window_close"}

    def _stamp_refusal(self, request, approver=None) -> None:
        self._check_refusal_reason_applicable(request)
        if approver is None:
            approver = request._get_current_pending_approver()
        approver.write(
            {
                "refusal_reason_id": self.refusal_reason_id.id,
                "note": self.note or False,
            }
        )
        request_vals = {}
        if not request.refusal_reason_id:
            request_vals["refusal_reason_id"] = self.refusal_reason_id.id
        if not request.refusal_note:
            request_vals["refusal_note"] = self.note or False
        if request_vals:
            request.sudo().write(request_vals)

    def action_confirm_change(self):
        self.check_singleton()
        if not self.change_field:
            trace.REFUSAL.event(
                "change_request_without_field", request=self.request_id.id
            )
            raise UserError(
                self.env._(
                    "Select which field the requester must update "
                    "(date or description).",
                ),
            )
        if not self.note:
            trace.REFUSAL.event(
                "change_request_without_note",
                request=self.request_id.id,
                field=self.change_field,
            )
            raise UserError(
                self.env._(
                    "Explain what the requester should change.",
                ),
            )

        trace.WIZARD.note(
            "request_change",
            request=self.request_id.id,
            approver=self.approver_id.id,
            field=self.change_field,
        )
        self.request_id.with_context(
            skip_wizard=True,
            requested_change_field=self.change_field,
            requested_change_note=self.note,
        ).action_request_change(approver=self.approver_id)
        return {"type": "ir.actions.act_window_close"}

    def action_cancel(self):
        return {"type": "ir.actions.act_window_close"}
