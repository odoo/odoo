from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError

from ..models import approval_trace as trace
from ..models.approval_utils import is_approval_manager


class ApprovalDelegateWizard(models.TransientModel):
    _name = "approval.delegate.wizard"
    _description = "Approval Delegation Wizard"

    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Approver",
        default=lambda self: self.env.user,
        readonly=True,
        required=True,
        help="User whose approvals will be delegated",
    )
    delegate_id = fields.Many2one(
        comodel_name="res.users",
        string="Delegate To",
        required=True,
        domain="[('id', '!=', user_id), ('share', '=', False),"
        " ('company_ids', 'in', allowed_company_ids)]",
        help="User who will approve on behalf of the approver",
    )
    allowed_company_ids = fields.Many2many(
        comodel_name="res.company",
        string="Allowed Companies",
        default=lambda self: self.env.companies,
        help="Companies the delegate must belong to — the wizard's own copy "
        "of the active company set, so the delegate_id domain can reference "
        "it. Approver rows carry check_company=True on delegate_id, so a "
        "delegate outside the request's company is rejected at write time "
        "anyway; without this leaf the rejection surfaced as a raw "
        "check_company error from inside approvers.write() instead of "
        "simply not being offered in the dropdown.",
    )
    start_date = fields.Date(
        default=fields.Date.today,
        required=True,
        help="First day of delegation period",
    )
    end_date = fields.Date(
        required=True,
        help="Last day of delegation period",
    )
    apply_to = fields.Selection(
        selection=[
            ("pending", "Pending Approvals Only"),
            ("all_future", "Pending and Waiting Approvals"),
        ],
        default="pending",
        required=True,
        help="Which approvals to delegate",
    )

    pending_count = fields.Integer(
        string="Pending Approvals",
        compute="_compute_preview",
        help="Number of pending approvals that will be delegated",
    )
    waiting_count = fields.Integer(
        string="Waiting Approvals",
        compute="_compute_preview",
        help="Number of waiting approvals that will be delegated",
    )

    @api.constrains("start_date", "end_date")
    def _check_dates(self):
        today = fields.Date.context_today(self)
        for wizard in self:
            if wizard.end_date < wizard.start_date:
                trace.REFUSAL.event(
                    "delegation_window_inverted",
                    start=wizard.start_date,
                    end=wizard.end_date,
                )
                raise ValidationError(self.env._("End date must be after start date."))
            if wizard.end_date < today:
                trace.REFUSAL.event(
                    "delegation_window_past", end=wizard.end_date, today=today
                )
                raise ValidationError(
                    self.env._(
                        "The delegation period has already ended. Choose an "
                        "end date of today or later.",
                    ),
                )

    @api.constrains("user_id", "delegate_id")
    def _check_users(self):
        for wizard in self:
            if wizard.user_id == wizard.delegate_id:
                trace.REFUSAL.event("delegate_is_principal", user=wizard.user_id.id)
                raise ValidationError(
                    self.env._("You cannot delegate approvals to yourself.")
                )

    def _delegatable_states(self) -> list[str]:
        self.check_singleton()
        return ["pending"] if self.apply_to == "pending" else ["pending", "waiting"]

    def _get_domain_approver(self, states=None):
        self.check_singleton()
        return [
            ("user_id", "=", self.user_id.id),
            ("state", "in", states or self._delegatable_states()),
            ("request_id.state", "=", "pending"),
        ]

    @api.depends_context("uid")
    @api.depends("user_id")
    def _compute_preview(self):
        approver = self.env["approval.approver"]
        is_manager = is_approval_manager(self.env)
        previewable = self.filtered(
            lambda wizard: (
                wizard.user_id and (wizard.user_id == self.env.user or is_manager)
            ),
        )
        counts: dict[tuple[int, str], int] = {}
        if previewable:
            counts = {
                (user.id, state): count
                for user, state, count in approver._read_group(
                    [
                        ("user_id", "in", previewable.user_id.ids),
                        ("state", "in", ["pending", "waiting"]),
                        ("request_id.state", "=", "pending"),
                    ],
                    ["user_id", "state"],
                    ["__count"],
                )
            }
        for wizard in self:
            if wizard not in previewable:
                wizard.pending_count = 0
                wizard.waiting_count = 0
                continue

            wizard.pending_count = counts.get((wizard.user_id.id, "pending"), 0)
            wizard.waiting_count = counts.get((wizard.user_id.id, "waiting"), 0)

    def action_confirm(self):
        self.check_singleton()

        is_manager = is_approval_manager(self.env)
        if self.user_id != self.env.user and not is_manager:
            trace.REFUSAL.event(
                "delegate_for_other_user",
                uid=self.env.uid,
                principal=self.user_id.id,
            )
            raise AccessError(
                self.env._(
                    "You can only delegate your own approvals.\n\nAttempted to delegate approvals for: %(user)s",
                    user=self.user_id.name,
                ),
            )

        approvers = self.env["approval.approver"].search(self._get_domain_approver())

        if approvers:
            self.env.cr.execute(
                """
                SELECT id FROM approval_approver
                WHERE id = ANY(%s)
                FOR UPDATE
                """,
                [list(approvers.ids)],
            )
            approvers.invalidate_recordset(["state", "delegate_id"])
            approvers = approvers.filtered(
                lambda a: a.state in self._delegatable_states(),
            )

        skipped = approvers.filtered(
            lambda a: (
                self.delegate_id == a.request_id.request_owner_id
                or self.delegate_id in (a.request_id.approver_ids - a).mapped("user_id")
            ),
        )
        approvers -= skipped

        if not approvers:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": self.env._("No Approvals"),
                    "message": self.env._("No approvals found to delegate."),
                    "type": "warning",
                },
            }

        trace.DELEGATION.note(
            "delegate",
            principal=self.user_id.id,
            delegate=self.delegate_id.id,
            rows=approvers.ids,
            skipped=skipped.ids,
            start=self.start_date,
            end=self.end_date,
        )
        approvers.write(
            {
                "delegate_id": self.delegate_id.id,
                "delegate_start_date": self.start_date,
                "delegate_end_date": self.end_date,
            },
        )

        self._notify_delegate(approvers)

        message = self.env._(
            "Successfully delegated %(count)d approval(s) to %(delegate)s from %(start)s to %(end)s",
            count=len(approvers),
            delegate=self.delegate_id.name,
            start=self.start_date,
            end=self.end_date,
        )
        if skipped:
            message += "\n\n" + self.env._(
                "%(count)d approval(s) were skipped because %(delegate)s "
                "is the request owner or already an approver on them.",
                count=len(skipped),
                delegate=self.delegate_id.name,
            )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": self.env._("Delegation Set"),
                "message": message,
                "type": "warning" if skipped else "success",
            },
        }

    def _notify_delegate(self, approvers):
        today = fields.Date.context_today(self)
        if not (self.start_date <= today <= self.end_date):
            return

        actionable = approvers.filtered(lambda a: a.state == "pending")
        trace.DELEGATION.event(
            "notify_delegate",
            delegate=self.delegate_id.id,
            rows=approvers.ids,
            actionable=actionable.ids,
        )
        if not actionable:
            return

        approval_type = self.env.ref("approval.mail_activity_data_approval")
        for approver in actionable:
            request = approver.request_id
            delegated = {
                "summary": self.env._("Delegated Approval: %s", request.name),
                "note": self.env._(
                    "<p>%(user)s has delegated their approval to you for this request.</p>"
                    "<p>Delegation period: %(start)s to %(end)s</p>",
                    user=self.user_id.name,
                    start=self.start_date,
                    end=self.end_date,
                ),
            }
            # The row's write already handed the principal's activity over.
            handed_over = request._get_approval_activities(
                user=self.delegate_id
            ).filtered(lambda activity, row=approver: activity.approver_id == row)
            if handed_over:
                handed_over.write(delegated)
                continue
            if request._get_approval_activities(user=self.delegate_id):
                continue
            approver._get_activity_target().activity_schedule(
                activity_type_id=(approver._get_activity_type() or approval_type).id,
                user_id=self.delegate_id.id,
                approver_id=approver.id,
                **delegated,
            )
