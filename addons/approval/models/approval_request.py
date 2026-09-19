import logging
from collections import Counter
from typing import Any, Self

from odoo import api, fields, models
from odoo.fields import Domain

from . import approval_trace as trace
from .approval_utils import boolean_search_domain, is_approval_manager

_logger = logging.getLogger(__name__)


class ApprovalRequest(models.Model):
    _name = "approval.request"
    _description = "Approval Request"
    _inherit = ["mixin.mail.thread.main.attachment", "mixin.mail.activity"]
    _check_company_auto = True
    _mail_post_access = "read"
    _order = "create_date desc, id desc"

    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        index=True,
        required=True,
    )
    category_id = fields.Many2one(
        comodel_name="approval.category",
        index=True,
        required=True,
        domain="""
            [
                '|', '|', '&',
                ('allowed_user_ids', '=', False),
                ('allowed_group_ids', '=', False),
                ('allowed_user_ids', '=', uid),
                ('allowed_group_ids.all_user_ids', '=', uid)
            ]
        """,
    )
    category_image = fields.Binary(related="category_id.image")
    request_owner_id = fields.Many2one(
        comodel_name="res.users",
        default=lambda self: self.env.user,
        index=True,
        required=True,
        domain="[('company_ids', 'in', company_id)]",
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        index="btree_not_null",
        check_company=True,
    )
    name = fields.Char(
        copy=False,
        tracking=True,
        help="Empty until the request is confirmed, then set to the "
        "category's sequence consecutive (deferred so discarded drafts "
        "never burn sequence numbers). Draft requests display a "
        "translated 'New' placeholder via display_name. The column "
        "itself stays language-neutral: storing a translated "
        "placeholder made the numbering check fail when the creator "
        "and the confirmer used different languages.",
    )
    priority = fields.Selection(
        selection=[
            ("0", "Low"),
            ("1", "Normal"),
            ("2", "High"),
            ("3", "Urgent"),
        ],
        default="1",
        index=True,
        required=True,
        tracking=True,
        help="Priority drives how quickly reminders and manager escalation "
        "fire for pending approvals (see the escalation schedule in the "
        "category/cron documentation; configurable via system parameters). "
        "Indexed because cron_smart_escalation filters and groups pending "
        "requests by (state, priority) every 4 hours.",
    )
    last_reminder_date = fields.Datetime(
        copy=False,
        readonly=True,
        help="Timestamp of last escalation reminder sent to approvers",
    )
    reminder_count = fields.Integer(
        default=0,
        copy=False,
        readonly=True,
        help="Number of escalation reminders sent for this request",
    )
    escalated_to_manager = fields.Boolean(
        default=False,
        copy=False,
        readonly=True,
        help="Whether this request has been escalated to approver's manager",
    )
    date = fields.Datetime()
    date_start = fields.Datetime()
    date_end = fields.Datetime()
    date_confirmed = fields.Datetime(
        index=True,
        copy=False,
        help="Set at confirmation (action_confirm). Never copied: a "
        "duplicated request is a fresh draft and must not inherit the "
        "source's submission time, which would skew SLA/deadline "
        "arithmetic and the analytics views.",
    )
    date_approval_granted = fields.Datetime(
        compute="_compute_date_approval_granted",
        store=True,
        index=True,
        copy=False,
        readonly=True,
        help="Date and time when final approval was granted",
    )
    revoked_state = fields.Selection(
        selection=[("refused", "Refused"), ("cancelled", "Cancelled")],
        copy=False,
        readonly=True,
        help="Set when an approved request was overturned from outside its decisions, "
        "e.g. a validated leave refused by an officer. The state reads it before the "
        "approver rows, whose decisions stay as they were given.",
    )
    revoked_by_user_id = fields.Many2one(
        comodel_name="res.users",
        copy=False,
        readonly=True,
    )
    date_revoked = fields.Datetime(
        copy=False,
        readonly=True,
    )
    granted_by_user_id = fields.Many2one(
        comodel_name="res.users",
        copy=False,
        readonly=True,
        help="Set when a pending request was approved from outside its decisions, "
        "e.g. a leave the system validated. The state reads it before the approver "
        "rows, none of which is recorded as deciding.",
    )
    date_refused = fields.Datetime(
        compute="_compute_date_refused",
        store=True,
        index=True,
        copy=False,
        readonly=True,
        help="Date and time when request reached the terminal refused state "
        "(set on refuse).",
    )
    date_cancelled = fields.Datetime(
        compute="_compute_date_cancelled",
        store=True,
        index=True,
        copy=False,
        readonly=True,
        help="Date and time when the request reached the terminal cancelled "
        "state (owner cancellation or auto-expiration).",
    )
    refusal_reason_id = fields.Many2one(
        comodel_name="approval.refusal.reason",
        copy=False,
        readonly=True,
        tracking=True,
        help="Canonical reason for the terminal refused transition. "
        "For refused requests it stores the deciding approver's choice.",
    )
    refusal_note = fields.Text(
        copy=False,
        readonly=True,
        tracking=True,
        help="Free-text note attached to the terminal refused transition.",
    )
    pending_change_field = fields.Selection(
        selection=[
            ("date", "Date"),
            ("reason", "Description"),
        ],
        string="Requested Change",
        copy=False,
        readonly=True,
        help="Field the requester must update before approval can resume. "
        "Set by the approver via the decision wizard; cleared by the "
        "requester through the Re-submit button. The approver's note "
        "explaining the change lives in the chatter.",
    )
    reason = fields.Html()
    quantity = fields.Float()
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        default=lambda self: self.env.company.currency_id,
        required=True,
        help="Currency the request amount is expressed in. Defaults to the "
        "company currency; set from the source document by approval.mixin. "
        "Tiers and conditional rules convert this amount into their own "
        "reference currency before comparing thresholds, so a shared "
        "category's amount routing is correct across companies with "
        "different currencies.",
    )
    amount = fields.Monetary(
        currency_field="currency_id",
        help="Request amount, in currency_id. Monetary (currency-rounded) "
        "so amount-based tier/rule routing is currency-aware.",
    )
    approver_ids = fields.One2many(
        comodel_name="approval.approver",
        inverse_name="request_id",
        readonly=False,
        check_company=True,
    )
    user_ids = fields.Many2many(
        comodel_name="res.users",
        compute="_compute_user_ids",
        readonly=True,
    )
    state = fields.Selection(
        selection=[
            ("new", "To Submit"),
            ("pending", "Submitted"),
            ("approved", "Approved"),
            ("refused", "Refused"),
            ("cancelled", "Cancelled"),
        ],
        compute="_compute_state",
        default="new",
        store=True,
        index=True,
        group_expand=True,
        tracking=True,
    )
    user_approver_state = fields.Selection(
        selection=[
            ("new", "New"),
            ("pending", "To Approve"),
            ("waiting", "Waiting"),
            ("approved", "Approved"),
            ("refused", "Refused"),
            ("cancelled", "Cancelled"),
        ],
        compute="_compute_user_approver_state",
    )
    is_terminal = fields.Boolean(
        compute="_compute_is_terminal",
        help="True once the request reaches approved, refused or cancelled. "
        "Exists so views can express 'this is over' by NAME: the membership "
        "test was written out as a literal triple in four `invisible` "
        "expressions, which is a second copy of _TERMINAL_STATES that no "
        "amount of Python discipline keeps in step.",
    )
    can_change_request_owner = fields.Boolean(
        compute="_compute_can_change_request_owner"
    )
    approval_minimum = fields.Integer(
        default=1,
        copy=True,
        readonly=True,
        help="Effective minimum approvals needed. Defaults from category, "
        "overridden by matching tier when applicable.",
    )
    allow_self_approval = fields.Boolean(related="category_id.allow_self_approval")
    approval_type = fields.Selection(
        related="category_id.approval_type",
        help="Category for filtering (e.g., purchase, expense)",
    )
    target_model = fields.Selection(
        related="category_id.target_model",
        help="Model to create when approval is granted (if any)",
    )
    approval_progress = fields.Float(
        compute="_compute_approval_progress",
        help="Percentage of approvals completed (approved / total approvers)",
    )
    pending_approver_ids = fields.Many2many(
        comodel_name="res.users",
        compute="_compute_pending_approver_ids",
        help="Users who still need to approve this request",
    )
    approval_deadline = fields.Datetime(
        compute="_compute_approval_deadline",
        store=True,
        index=True,
        help="Deadline for approval decision based on category settings",
    )
    is_overdue = fields.Boolean(
        compute="_compute_is_overdue",
        search="_search_is_overdue",
        help="True if approval deadline has passed and request still pending",
    )
    sla_status = fields.Selection(
        selection=[
            ("on_track", "On Track"),
            ("at_risk", "At Risk"),
            ("breached", "SLA Breached"),
            ("met", "SLA Met"),
            ("no_sla", "No SLA"),
        ],
        compute="_compute_sla_status",
        search="_search_sla_status",
        help="SLA compliance status for this request. Non-stored: the "
        "value tracks the wall clock (see _compute_sla_status); "
        "filtering goes through _search_sla_status.",
    )
    sla_elapsed_hours = fields.Float(
        compute="_compute_sla_elapsed_hours",
        help="Hours elapsed since request was submitted",
    )
    sla_remaining_hours = fields.Float(
        compute="_compute_sla_remaining_hours",
        help="Hours remaining until SLA target (negative if breached)",
    )
    can_withdraw = fields.Boolean(
        compute="_compute_can_withdraw",
        help="Whether current user can withdraw their approval on this request.",
    )
    is_pending_my_review = fields.Boolean(
        string="Awaiting My Decision",
        compute="_compute_is_pending_my_review",
        search="_search_is_pending_my_review",
        help="True when this request is pending AND the current user is the "
        "effective approver of a row that is itself still pending. "
        "Exists so XML domains (menu actions, search filters) can express "
        "'awaiting my decision' by NAME instead of re-typing the leaves: "
        "hand-written copies drifted from _get_domain_pending_review() and "
        "inverted delegation — the delegate's inbox came up empty while "
        "the delegator, who can no longer act, still saw the request.",
    )
    applied_rule_ids = fields.Many2many(
        comodel_name="approval.rule",
        copy=False,
        readonly=True,
        help="Conditional rules that added approvers to this request",
    )
    category_snapshot = fields.Json(
        copy=False,
        readonly=True,
        help="Snapshot of category configuration at confirmation time",
    )
    res_model = fields.Char(
        index=True,
        copy=False,
        readonly=True,
        help="Model name of the source document (e.g., 'purchase.order', "
        "'sale.order'). Never copied: a duplicated request is a fresh, "
        "unlinked draft — inheriting the source pointer would make the "
        "clone's decision drive a document it does not own (see "
        "_notify_source_document_state_change, which additionally "
        "verifies the reverse link before firing any hook).",
    )
    res_id = fields.Many2oneReference(
        model_field="res_model",
        copy=False,
        readonly=True,
        help="Reference to the source document that requested this "
        "approval. Never copied (see res_model).",
    )
    operation = fields.Char(
        index="btree_not_null",
        copy=False,
        readonly=True,
        help="The gated operation this request was raised for, when a document's own "
        "gate raised it. A grant clears that operation and no other.",
    )
    operation_snapshot = fields.Json(
        string="Approved Subject",
        copy=False,
        readonly=True,
        help="What the document looked like when the request was raised, as its own "
        "gate described it. The grant covers the document only while it still matches.",
    )
    date_operation_run = fields.Datetime(
        string="Operation Run On",
        copy=False,
        readonly=True,
        help="When the grant ran the gated operation, so it runs once.",
    )
    binding_id = fields.Many2one(
        comodel_name="approval.binding",
        index="btree_not_null",
        copy=False,
        readonly=True,
        ondelete="set null",
        help="The gated operation this request was raised for, when an "
        "approval.binding in Request mode raised it. Approving the request "
        "runs that operation once, as the requester.",
    )
    subject_key = fields.Char(
        index="btree_not_null",
        copy=False,
        readonly=True,
        help="What this request asks about, when its source record holds one "
        "request per subject (mixin.approval.subjects): a partner asking to join "
        "a course, a stage an engineering change passes.",
    )
    binding_snapshot = fields.Json(
        copy=False,
        readonly=True,
        help="Values the binding's condition read from the source document "
        "when the request was raised. An approval covers the record as it was "
        "approved: once one of these values moves, it no longer does.",
    )
    date_binding_replayed = fields.Datetime(
        copy=False,
        readonly=True,
        help="When the gated operation ran after approval. Set once, so a "
        "withdrawal followed by a second approval does not run it again.",
    )
    binding_replay_error = fields.Text(
        copy=False,
        readonly=True,
        help="Why the gated operation did not run after approval. The approval "
        "itself stands.",
    )
    res_model_id = fields.Many2one(
        comodel_name="ir.model",
        string="Source Model",
        compute="_compute_res_model_id",
        store=True,
        help="Technical model reference for filtering",
    )
    res_name = fields.Char(
        compute="_compute_res_name",
        help="Display name of the source document",
    )
    attachment_ids = fields.One2many(
        comodel_name="ir.attachment",
        inverse_name="res_id",
        domain=[("res_model", "=", "approval.request")],
    )
    count_attachment = fields.Integer(compute="_compute_count_attachment")

    @api.model
    def _get_fields_approver_sync_trigger(self) -> frozenset[str]:
        return self._get_routing_fields_frozen() | self._get_routing_fields_live()

    @api.model
    def _get_routing_fields_live(self) -> frozenset[str]:
        return frozenset({"priority", "date", "date_start", "date_end"})

    @api.model
    def _get_routing_fields_frozen(self) -> frozenset[str]:
        declared = (
            frozenset({"category_id", "request_owner_id"})
            | self.env["approval.rule"]._get_fields_request_trigger()
        )
        return declared - self._get_routing_fields_live()

    @api.model_create_multi
    def create(self, vals_list: list[dict[str, Any]]) -> Self:
        categories = self.env["approval.category"].browse(
            {vals["category_id"] for vals in vals_list if vals.get("category_id")},
        )
        minimum_by_category = {
            category.id: category.approval_minimum for category in categories
        }
        for vals in vals_list:
            self._check_no_forged_computed_fields(vals)
            if not vals.get("category_id"):
                continue
            if "approval_minimum" not in vals:
                vals["approval_minimum"] = minimum_by_category[vals["category_id"]]

        created_requests = super().create(vals_list)

        trace.CRUD.items(
            "created",
            lambda: [
                {
                    "request": request.id,
                    "category": request.category_id.id,
                    "owner": request.request_owner_id.id,
                    "minimum": request.approval_minimum,
                    "model": request.res_model or None,
                    "res_id": request.res_id or None,
                }
                for request in created_requests
            ],
        )
        created_requests._subscribe_owners()

        created_requests._sync_approvers()

        return created_requests

    def _subscribe_owners(self) -> None:
        by_partner: dict[int, list[int]] = {}
        for request in self:
            partner_id = request.request_owner_id.partner_id.id
            if partner_id:
                by_partner.setdefault(partner_id, []).append(request.id)
        for partner_id, request_ids in by_partner.items():
            self.browse(request_ids).message_subscribe(partner_ids=[partner_id])

    def write(self, vals: dict[str, Any]) -> bool:
        self._check_access_write()

        self._check_no_forged_computed_fields(vals)

        self._check_locked_fields(vals)

        if "category_id" in vals:
            new_category_id = vals["category_id"] or False
            for request in self:
                if request.state != "new" and request.category_id.id != new_category_id:
                    request._raise_category_change_blocked(request.category_id)

        if "request_owner_id" in vals:
            outgoing: dict[int, list[int]] = {}
            for approval in self:
                partner_id = approval.request_owner_id.partner_id.id
                if partner_id:
                    outgoing.setdefault(partner_id, []).append(approval.id)
            for partner_id, request_ids in outgoing.items():
                self.browse(request_ids).message_unsubscribe(partner_ids=[partner_id])

        if "approver_ids" in vals:
            self._check_approver_ids_business_rules(vals["approver_ids"])

        self._check_routing_fields_after_submit(vals)

        res = super().write(vals)

        resync = self._get_fields_approver_sync_trigger() & vals.keys()
        if trace.CRUD.on():
            trace.CRUD.event(
                "write",
                requests=self.ids,
                fields=sorted(vals),
                resync=sorted(resync),
            )
        if resync:
            self._sync_approvers()
            self._extend_approvers_live()

        if "request_owner_id" in vals:
            self._subscribe_owners()

        return res

    def copy(self, default: dict[str, Any] | None = None) -> Self:
        new_records = super().copy(default=default)
        for source, new in zip(self, new_records, strict=True):
            new._message_log(
                body=self.env._("Duplicated from %s", source._get_html_link()),
            )
        return new_records

    def unlink(self) -> bool:
        self._check_access_unlink()
        self._check_business_rules_unlink()
        trace.CRUD.note("unlink", requests=self.ids, uid=self.env.uid)
        return super().unlink()

    @api.ondelete(at_uninstall=False)
    def unlink_attachments(self) -> None:
        attachment_ids = self.env["ir.attachment"].search(
            [
                ("res_model", "=", "approval.request"),
                ("res_id", "in", self.ids),
            ],
        )
        trace.ATTACHMENT.note(
            "unlink_with_requests",
            requests=self.ids,
            attachments=len(attachment_ids),
        )
        if attachment_ids:
            attachment_ids.unlink()

    def _track_subtype(self, init_values: dict[str, Any]) -> str | bool:
        self.check_singleton()
        if "state" in init_values:
            return self.env.ref("approval.mt_approval_state")

        return super()._track_subtype(init_values)

    @api.depends("name")
    def _compute_display_name(self) -> None:
        placeholder = self.env._("New")
        for request in self:
            request.display_name = request.name or placeholder

    def _compute_count_attachment(self) -> None:
        domain = [
            ("res_model", "=", "approval.request"),
            ("res_id", "in", self.ids),
        ]
        with trace.COMPUTE.span("count_attachment", n=len(self)) as span:
            attachment_data = self.env["ir.attachment"]._read_group(
                domain,
                groupby=["res_id"],
                aggregates=["__count"],
            )
            attachment_counts = dict(attachment_data)
            for request in self:
                request.count_attachment = attachment_counts.get(request.id, 0)
            span["with_attachments"] = len(attachment_counts)
            span["attachments"] = sum(attachment_counts.values())

    @api.depends("res_model")
    def _compute_res_model_id(self) -> None:
        for request in self:
            if request.res_model:
                request.res_model_id = self.env["ir.model"]._get(request.res_model)
            else:
                request.res_model_id = False

    @api.depends("res_model", "res_id")
    def _compute_res_name(self) -> None:
        ids_by_model: dict[str, list[int]] = {}
        for request in self:
            if request.res_model and request.res_id:
                ids_by_model.setdefault(request.res_model, []).append(request.res_id)

        names_by_model: dict[str, dict[int, str] | None] = {}
        existing_by_model: dict[str, set[int]] = {}
        for model, ids in ids_by_model.items():
            try:
                records = self.env[model].browse(ids).exists()
            except KeyError:
                trace.DEGRADED.note("res_model_not_in_registry", model=model, ids=ids)
                names_by_model[model] = None
                continue
            existing_by_model[model] = set(records.ids)
            accessible = records._filtered_access("read")
            names_by_model[model] = {
                record.id: record.display_name for record in accessible
            }

        outcomes: Counter[str] = Counter()
        for request in self:
            if not (request.res_model and request.res_id):
                request.res_name = False
                outcomes["unset"] += 1
                continue
            names = names_by_model.get(request.res_model)
            if names is None:
                request.res_name = self.env._("Unknown Model")
                outcomes["model_gone"] += 1
            elif request.res_id in names:
                request.res_name = names[request.res_id]
                outcomes["named"] += 1
            elif request.res_id in existing_by_model.get(request.res_model, ()):
                request.res_name = self.env._("Access Denied")
                outcomes["unreadable"] += 1
            else:
                request.res_name = self.env._("Deleted Document")
                outcomes["deleted"] += 1
        if trace.COMPUTE.on():
            trace.COMPUTE.event(
                "res_name",
                n=len(self),
                models=len(ids_by_model),
                **outcomes,
            )

    def _get_snapshot_config(self, key: str) -> Any:
        self.check_singleton()
        snapshot = self.category_snapshot or {}
        value = snapshot.get(key)
        source = "snapshot"
        if value is None:
            value = self.category_id[key]
            source = "category" if snapshot else "no_snapshot"
        trace.SNAPSHOT.event(
            "config_read", request=self.id, key=key, source=source, value=value
        )
        return value

    @api.depends_context("uid")
    @api.depends(
        "state",
        "approver_ids.state",
        "approver_ids.user_id",
        "approver_ids.delegate_id",
        "approver_ids.delegate_start_date",
        "approver_ids.delegate_end_date",
        "granted_by_user_id",
    )
    def _compute_can_withdraw(self) -> None:
        for request in self:
            request.can_withdraw = (
                request.state in ("pending", "approved")
                and request.user_approver_state == "approved"
                and not request.granted_by_user_id
            )

    @api.depends_context("uid")
    @api.depends(
        "state",
        "approver_ids.state",
        "approver_ids.user_id",
        "approver_ids.delegate_id",
        "approver_ids.delegate_start_date",
        "approver_ids.delegate_end_date",
    )
    def _compute_is_pending_my_review(self) -> None:
        user = self.env.user
        for request in self:
            request.is_pending_my_review = bool(
                request.state == "pending"
                and request._get_current_pending_approver(user)
            )

    @api.depends_context("uid")
    def _compute_can_change_request_owner(self) -> None:
        is_manager = is_approval_manager(self.env)
        for request in self:
            request.can_change_request_owner = is_manager

    @api.depends("approver_ids")
    def _compute_user_ids(self) -> None:
        for request in self:
            request.user_ids = request.approver_ids.user_id

    @api.depends_context("uid")
    @api.depends(
        "approver_ids.state",
        "approver_ids.delegate_id",
        "approver_ids.delegate_start_date",
        "approver_ids.delegate_end_date",
    )
    def _compute_user_approver_state(self) -> None:
        current_user = self.env.user
        resolved = 0
        for approval in self:
            approval.user_approver_state = approval.approver_ids.filtered(
                lambda approver: approver._get_effective_approver() == current_user,
            )[:1].state
            resolved += bool(approval.user_approver_state)
        trace.COMPUTE.event(
            "user_approver_state",
            n=len(self),
            uid=current_user.id,
            resolved=resolved,
        )

    @api.depends("approver_ids.state")
    def _compute_approval_progress(self) -> None:
        for request in self:
            approvers = request.approver_ids
            if not approvers:
                request.approval_progress = 0.0
                continue

            approved_count = len(approvers.filtered(lambda a: a.state == "approved"))
            total_count = len(approvers)
            request.approval_progress = (
                (approved_count / total_count) * 100.0 if total_count else 0.0
            )

    @api.depends("state")
    def _compute_is_terminal(self) -> None:
        terminal = self._TERMINAL_STATES
        for request in self:
            request.is_terminal = request.state in terminal

    @api.depends("approver_ids", "approver_ids.state")
    def _compute_pending_approver_ids(self) -> None:
        for request in self:
            pending = request.approver_ids.filtered(lambda a: a.state == "pending")
            request.pending_approver_ids = pending.mapped("user_id")

    @api.depends(
        "approver_ids.state",
        "approver_ids.required",
        "approval_minimum",
        "approver_ids.step_ids",
        "approver_ids.decided_step_ids",
        "approver_ids.step_ids.minimum",
        "approver_ids.step_ids.exclusive",
        "approver_ids.step_ids.active",
        "revoked_state",
        "granted_by_user_id",
    )
    def _compute_state(self) -> None:
        for request in self:
            if request.revoked_state:
                request.state = request.revoked_state
                continue
            if request.granted_by_user_id:
                request.state = "approved"
                continue

            state_lst = request.mapped("approver_ids.state")

            if not state_lst:
                request.state = "new"
                continue

            required_approved = all(
                a.state == "approved" for a in request.approver_ids.filtered("required")
            )

            approval_threshold = request.approval_minimum

            state_counts = Counter(state_lst)

            if request._get_deciding_refusals():
                request.state = "refused"
            elif state_counts.get("cancelled", 0) > 0:
                request.state = "cancelled"
            elif state_counts.get("new", 0) > 0:
                request.state = "new"
            elif required_approved and request._is_quorum_met(
                state_counts, approval_threshold
            ):
                request.state = "approved"
            else:
                request.state = "pending"

            if trace.COMPUTE.on():
                trace.COMPUTE.event(
                    "state",
                    request=request.id,
                    state=request.state,
                    counts=dict(state_counts),
                    minimum=approval_threshold,
                    required_ok=required_approved,
                    refusals=request._get_deciding_refusals().ids,
                    unmet=request._get_unmet_steps().ids
                    if request.approver_ids.step_ids
                    else None,
                )

    def _get_deciding_refusals(self):
        """Refused rows that refuse the request: all but those refused only for
        advisory steps."""
        self.check_singleton()
        refused = self.approver_ids.filtered(
            lambda approver: approver.state == "refused"
        )
        deciding = refused.filtered(lambda approver: not approver._is_advisory_only())
        if refused and trace.DECISION.on():
            trace.DECISION.event(
                "deciding_refusals",
                request=self.id,
                refused=refused.ids,
                deciding=deciding.ids,
                advisory_only=(refused - deciding).ids,
            )
        return deciding

    def _is_quorum_met(self, state_counts, approval_threshold: int) -> bool:
        self.check_singleton()
        if self.approver_ids.step_ids:
            blocking = self._get_blocking_unmet_steps()
            trace.DECISION.event(
                "quorum",
                request=self.id,
                rule="steps",
                blocking=blocking.ids,
                met=not blocking,
            )
            return not blocking
        approved = state_counts.get("approved", 0)
        trace.DECISION.event(
            "quorum",
            request=self.id,
            rule="minimum",
            approved=approved,
            minimum=approval_threshold,
            met=approved >= approval_threshold,
        )
        return approved >= approval_threshold

    def _get_step_counts(self) -> dict[int, int]:
        self.check_singleton()
        return {
            step_id: len(approvers)
            for step_id, approvers in self._get_step_assignment().items()
        }

    def _get_step_assignment(self) -> dict[int, Any]:
        """Which approved rows count toward each step, exclusivity applied.

        An approved row counts toward every step its decision was given for. That is
        Studio's rule -- a user who decided an exclusive step decides nothing else on
        the same record, and the other way round -- which a decision keeps when it
        is taken (_get_steps_for_decision, _check_steps_decidable). A row approved
        for several steps one of which is exclusive, as consent or an automatic rule
        approves, counts toward exactly one: the lowest still short of its quorum.
        The approval button shows this assignment, so what it draws is what the
        quorum counts.
        """
        self.check_singleton()
        steps = self.approver_ids.step_ids.sorted(lambda step: (step.sequence, step.id))
        assigned = {step.id: self.env["approval.approver"] for step in steps}
        approved = self.approver_ids.filtered(
            lambda approver: approver.state == "approved" and approver.decided_step_ids,
        ).sorted(lambda approver: (approver.sequence, approver.id))
        for approver in approved:
            own = approver.decided_step_ids.filtered(
                lambda step: step.id in assigned
            ).sorted(lambda step: (step.sequence, step.id))
            if any(own.mapped("exclusive")):
                target = own.sorted(
                    lambda step: (step.sequence, not step.exclusive, step.id)
                ).filtered(lambda step: len(assigned[step.id]) < step.minimum)[:1]
                if target:
                    assigned[target.id] |= approver
                continue
            for step in own:
                assigned[step.id] |= approver
        if trace.STEPS.on():
            trace.STEPS.event(
                "assignment",
                request=self.id,
                steps={step_id: rows.ids for step_id, rows in assigned.items()},
            )
        return assigned

    def _get_unmet_steps(self):
        self.check_singleton()
        counts = self._get_step_counts()
        return self.approver_ids.step_ids.filtered(
            lambda step: (
                counts[step.id] < step.minimum
                or self._get_step_required_rows_pending(step)
            ),
        )

    def _get_step_required_rows_pending(self, step):
        """The rows of a step's required members that have not approved it yet."""
        self.check_singleton()
        required = set(step.member_ids.filtered("required").user_id.ids)
        if step.subject_user_required:
            named = step.sudo()._get_source_user_ids(self.get_source_document(), self)
            trace.STEPS.event(
                "named_users_required",
                request=self.id,
                step=step.id,
                named=sorted(named),
            )
            required |= named
        if not required:
            return self.env["approval.approver"]
        return self.approver_ids.filtered(
            lambda row: (
                row.user_id.id in required
                and step in row.step_ids
                and not (row.state == "approved" and step in row.decided_step_ids)
            )
        )

    def _get_blocking_unmet_steps(self):
        """The unmet steps the request waits for: advisory steps never hold it."""
        self.check_singleton()
        return self._get_unmet_steps().filtered(lambda step: not step.advisory)

    def _get_step_turn_row(self, step):
        """On a step whose members decide in order, the row whose turn it is: the first
        member, in the members' order, whose row has not approved the step yet."""
        self.check_singleton()
        named = step.sudo()._get_source_user_ids(self.get_source_document(), self)
        member_sequence = dict.fromkeys(named, step.subject_user_sequence)
        member_sequence.update(
            {member.user_id.id: member.sequence for member in step.member_ids}
        )
        # A member takes its member sequence; an approver added to the request takes
        # its own row sequence, which is how the approver list ordered them.
        rows = self.approver_ids.filtered(lambda row: step in row.step_ids).sorted(
            lambda row: (member_sequence.get(row.user_id.id, row.sequence), row.id)
        )
        turn = rows.filtered(
            lambda row: not (row.state == "approved" and step in row.decided_step_ids)
        )[:1]
        trace.STEPS.event(
            "turn", request=self.id, step=step.id, rows=rows.ids, turn=turn.ids
        )
        return turn

    def _refresh_turn_states(self) -> None:
        for request in self.filtered(lambda request: request.state == "pending"):
            rows = request.approver_ids.filtered(
                lambda row: row.state in ("pending", "waiting") and row.step_ids
            )
            waiting = rows.filtered(
                lambda row, request=request: (
                    all(
                        step.in_order and not request._is_row_turn(row, step)
                        for step in row.step_ids - row.decided_step_ids
                    )
                    and row.step_ids - row.decided_step_ids
                )
            )
            to_wait = waiting.filtered(lambda row: row.state == "pending")
            to_open = (rows - waiting).filtered(lambda row: row.state == "waiting")
            trace.STEPS.event(
                "turn_states",
                request=request.id,
                waiting=to_wait.ids,
                opened=to_open.ids,
            )
            if to_wait:
                to_wait.sudo().write({"flow_state": "waiting", "pending_since": False})
            if to_open:
                to_open.sudo().write({"flow_state": "pending"})
                to_open._create_activity()

    def _is_row_turn(self, row, step) -> bool:
        self.check_singleton()
        return not step.in_order or self._get_step_turn_row(step) == row

    def _get_open_steps(self):
        """The unmet steps an approver is asked for now: the lowest sequence among the
        blocking ones, and every advisory step still unmet, which waits for nobody."""
        self.check_singleton()
        unmet = self._get_unmet_steps()
        blocking = unmet.filtered(lambda step: not step.advisory)
        advisory = unmet - blocking
        if not blocking:
            open_steps = advisory
        else:
            lowest = min(blocking.mapped("sequence"))
            open_steps = (
                blocking.filtered(lambda step: step.sequence == lowest) | advisory
            )
        trace.STEPS.event(
            "open",
            request=self.id,
            unmet=unmet.ids,
            blocking=blocking.ids,
            advisory=advisory.ids,
            open=open_steps.ids,
        )
        return open_steps

    def _compute_terminal_date_stamp(self, field_name: str, target_state: str) -> None:
        now = fields.Datetime.now()
        cleared = 0
        stamped = 0
        for request in self:
            if request.state != target_state:
                cleared += bool(request[field_name])
                request[field_name] = False
            elif not request[field_name]:
                request[field_name] = now
                stamped += 1
        if cleared or stamped:
            trace.LIFECYCLE.event(
                "terminal_date_stamp",
                field=field_name,
                state=target_state,
                n=len(self),
                cleared=cleared,
                stamped=stamped,
            )

    @api.depends("state", "revoked_state")
    def _compute_date_approval_granted(self) -> None:
        revoked = self.filtered("revoked_state")
        for request in revoked:
            request.date_approval_granted = request.date_approval_granted
        (self - revoked)._compute_terminal_date_stamp(
            "date_approval_granted", "approved"
        )

    @api.depends("state")
    def _compute_date_refused(self) -> None:
        self._compute_terminal_date_stamp("date_refused", "refused")

    @api.depends("state")
    def _compute_date_cancelled(self) -> None:
        self._compute_terminal_date_stamp("date_cancelled", "cancelled")

    _TERMINAL_STATES = frozenset({"approved", "refused", "cancelled"})

    _DECISION_STATES = frozenset({"approved", "refused"})

    @api.model
    def _decision_states_sql(self) -> str:
        members = ", ".join(f"'{state}'" for state in sorted(self._DECISION_STATES))
        return f"({members})"

    def _label(self) -> str:
        self.check_singleton()
        return self.name or self.category_id.name

    def get_source_document(self) -> Any:
        self.check_singleton()
        if not self.res_model:
            return False
        try:
            if self.res_id:
                return self.env[self.res_model].browse(self.res_id)
            return self.env[self.res_model]
        except KeyError:
            trace.SYNC.event("source_model_gone", request=self.id, model=self.res_model)
            _logger.warning(
                "Source model %s not found for approval request %s",
                self.res_model,
                self.id,
            )
            return False

    def action_view_attachment(self) -> dict[str, Any]:
        self.check_singleton()
        res = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "base.action_attachment"
        )
        res["domain"] = [
            ("res_model", "=", "approval.request"),
            ("res_id", "in", self.ids),
        ]
        res["context"] = {
            "default_res_model": "approval.request",
            "default_res_id": self.id,
        }
        return res

    @api.model
    def _get_domain_pending_review(self, user: models.BaseModel) -> list:
        return [
            ("state", "=", "pending"),
            "|",
            (
                "approver_ids",
                "any",
                [
                    ("user_id", "=", user.id),
                    ("is_delegated", "=", False),
                    ("state", "=", "pending"),
                ],
            ),
            (
                "approver_ids",
                "any",
                [
                    ("delegate_id", "=", user.id),
                    ("is_delegated", "=", True),
                    ("state", "=", "pending"),
                ],
            ),
        ]

    @api.model
    def _search_is_pending_my_review(self, operator: str, value: Any) -> Domain:
        awaiting = Domain(self._get_domain_pending_review(self.env.user))
        return boolean_search_domain(operator, value, awaiting, ~awaiting)

    @api.model
    def action_view_to_review(self) -> dict[str, Any]:
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Approvals to Review"),
            "res_model": "approval.request",
            "view_mode": "list,kanban,form",
            "domain": self._get_domain_pending_review(self.env.user),
            "context": {},
        }

    def _get_current_pending_approver(
        self, user: models.BaseModel | None = None
    ) -> models.BaseModel:
        self.check_singleton()
        user = user or self.env.user
        return self.approver_ids.filtered(
            lambda a: a.state == "pending" and a._get_effective_approver() == user,
        )
