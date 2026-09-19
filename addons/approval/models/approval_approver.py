from typing import Any, Self

from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Command, Domain
from odoo.tools import TransactionMemo

from . import approval_trace as trace
from .approval_utils import boolean_search_domain, is_approval_manager

DELEGATION_TZ_BUCKETS = TransactionMemo(
    "approval_delegation_tz_buckets", invalidated_by={"res.users": ("tz",)}
)


class ApprovalApprover(models.Model):
    _name = "approval.approver"
    _description = "Approver"
    _order = "sequence, id"
    _check_company_auto = True

    _SETTLED_STATES = frozenset({"approved", "refused", "cancelled"})

    _request_user_uniq = models.Constraint(
        "unique(request_id, user_id)",
        "You cannot assign the same approver multiple times on the same request.",
    )

    request_id = fields.Many2one(
        comodel_name="approval.request",
        index=True,
        required=True,
        ondelete="cascade",
        check_company=True,
    )
    company_id = fields.Many2one(
        related="request_id.company_id",
        string="Company",
        readonly=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        index=True,
        required=True,
        check_company=True,
    )
    sequence = fields.Integer(default=10)
    state = fields.Selection(
        selection=[
            ("new", "New"),
            ("pending", "To Approve"),
            ("waiting", "Waiting"),
            ("approved", "Approved"),
            ("refused", "Refused"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        compute="_compute_state",
        store=True,
        index=True,
        copy=False,
        readonly=True,
        help="Approved or refused while the decision ledger holds this row's latest "
        "approval or refusal since the request was last reset; otherwise the "
        "routing state. Never written: a decision exists only as a ledger row.",
    )
    flow_state = fields.Selection(
        selection=[
            ("new", "New"),
            ("pending", "To Approve"),
            ("waiting", "Waiting"),
            ("refused", "Refused"),
            ("cancelled", "Cancelled"),
        ],
        string="Routing Status",
        default="new",
        copy=False,
        readonly=True,
        required=True,
        help="Where routing has put this row: asked, waiting its turn, or closed by "
        "a refusal or a forced end. The status shows it whenever no standing "
        "decision does.",
    )
    decision_log_ids = fields.One2many(
        comodel_name="approval.decision.log",
        inverse_name="approver_id",
        readonly=True,
    )
    required = fields.Boolean(
        default=False,
        readonly=True,
    )
    step_ids = fields.Many2many(
        comodel_name="approval.category.step",
        relation="approval_approver_step_rel",
        column1="approver_id",
        column2="step_id",
        string="Steps",
        copy=False,
        readonly=True,
        context={"active_test": True},
        help="The steps this approver may decide. Rows are one per user per "
        "request, so a user in the pools of two steps appears once, with both here.",
    )
    decided_step_ids = fields.Many2many(
        comodel_name="approval.category.step",
        relation="approval_approver_decided_step_rel",
        column1="approver_id",
        column2="step_id",
        string="Decided Steps",
        copy=False,
        readonly=True,
        context={"active_test": True},
        help="The steps this row's decision was given for, which are the steps the "
        "quorum counts it toward. The approval button decides the step it is drawn "
        "under; any other decision is given for every step of the row.",
    )
    source_rule_id = fields.Many2one(
        comodel_name="approval.rule",
        index="btree_not_null",
        copy=False,
        readonly=True,
        ondelete="set null",
        help="Conditional rule that injected this approver, if any — an "
        "adding rule or the replacing rule this request fell into (audit + "
        "re-sync provenance). There used to be a second column, "
        "source_tier_id, for the separate approval.tier model.",
    )
    source_synced = fields.Boolean(
        copy=False,
        readonly=True,
        help="Set when this row was produced by the approver sync from an "
        "automated source (category approver, tier, rule, security group, "
        "extension hook such as the HR manager). False on genuinely manual "
        "rows. Drives the orphan-vs-manual classification on re-sync: a "
        "synced row whose source stopped producing it (approver removed "
        "from the category, owner changed away from a manager) is deleted "
        "instead of surviving as a phantom optional approver.",
    )
    pending_since = fields.Datetime(
        index="btree_not_null",
        copy=False,
        readonly=True,
        help="When this row ENTERED the decision window (state became "
        "'pending'). The symmetric half of decision_date, which records "
        "when it left. Approver-response analytics measure "
        "decision_date - pending_since so they report THIS approver's "
        "turnaround; measuring against the request's date_confirmed "
        "instead charged every approver in a sequential chain for the "
        "delays of everyone ahead of them, which made the dashboard's "
        "'Slowest Approver' reliably name whoever sits last in the "
        "chain. Cleared when the row returns to 'new' (reset-to-draft) "
        "and re-stamped on every re-entry, so a withdraw-and-reopen "
        "cycle times the new decision window, not the original one.",
    )
    decided_by_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Decided By",
        index="btree_not_null",
        copy=False,
        readonly=True,
        help="Who actually made the decision recorded in decision_date — "
        "the delegate when the row was decided inside an active delegation "
        "window, otherwise user_id itself. The pair (user_id, "
        "decided_by_user_id) separates WHOSE approval slot this is from WHO "
        "exercised it; every other identity question in the module resolves "
        "the effective approver, and without this column the analytics were "
        "the one place that could not: approver.performance credited the "
        "delegated decision (and its response time) to the absent principal "
        "while the delegate who did the work scored nothing. Left empty for "
        "rows flipped by non-decisions, exactly like decision_date, and "
        "cleared beside it on withdraw and reset-to-draft.",
    )
    decision_date = fields.Datetime(
        index="btree_not_null",
        copy=False,
        readonly=True,
        help="When THIS approver personally approved or refused, stamped "
        "by the decision funnel (_apply_decision). Left empty for rows "
        "flipped by non-decisions — consent auto-approval, sequential/"
        "cascade refusal, owner cancellation, expiration — so the "
        "approver-performance analytics count only genuine decisions and "
        "measure each approver's own response time (cleared on withdraw "
        "and reset-to-draft).",
    )
    delegate_id = fields.Many2one(
        comodel_name="res.users",
        string="Delegate To",
        copy=False,
        check_company=True,
        help="Temporary delegate who can approve on your behalf",
    )
    delegate_start_date = fields.Date(
        string="Delegation Start",
        copy=False,
        help="Start date for delegation period",
    )
    delegate_end_date = fields.Date(
        string="Delegation End",
        copy=False,
        help="End date for delegation period",
    )
    is_delegated = fields.Boolean(
        string="Currently Delegated",
        compute="_compute_is_delegated",
        search="_search_is_delegated",
        copy=False,
        help="Indicates if approval is currently delegated to another user. "
        "Non-stored on purpose: the value is a function of wall-clock "
        "'today' vs the delegation window, and no ORM write happens when "
        "the clock advances past delegate_start_date. A stored compute "
        "would freeze at False forever for any delegation scheduled "
        "in advance. A custom search method keeps the field usable in "
        "domain filters (e.g. the 'Delegated to Me' search view).",
    )

    note = fields.Text(
        copy=False,
        help="Optional note or comment added when approving or refusing the request. "
        "Use this to provide context, conditions, or reasons for your decision.",
    )
    refusal_reason_id = fields.Many2one(
        comodel_name="approval.refusal.reason",
        copy=False,
        help="Structured reason for refusing the request",
    )

    @api.constrains("delegate_id", "delegate_start_date", "delegate_end_date")
    def _check_delegation_dates(self):
        for approver in self:
            if approver.delegate_id:
                if not (approver.delegate_start_date and approver.delegate_end_date):
                    trace.REFUSAL.event(
                        "delegation_dates_missing", approver=approver.id
                    )
                    raise ValidationError(
                        self.env._(
                            "Both start and end dates are required for delegation."
                        ),
                    )
                if approver.delegate_end_date < approver.delegate_start_date:
                    trace.REFUSAL.event(
                        "delegation_dates_backwards",
                        approver=approver.id,
                        start=approver.delegate_start_date,
                        end=approver.delegate_end_date,
                    )
                    raise ValidationError(
                        self.env._("Delegation end date must be after start date."),
                    )

    @api.constrains("delegate_id", "user_id", "request_id")
    def _check_delegate_identity(self):
        for approver in self:
            delegate = approver.delegate_id
            other_approvers = approver.request_id.approver_ids - approver
            if approver.user_id and approver.user_id in other_approvers.delegate_id:
                trace.REFUSAL.event(
                    "delegate_already_covers_a_row",
                    approver=approver.id,
                    user=approver.user_id.id,
                )
                raise ValidationError(
                    self.env._(
                        "%(user)s already covers another approval on this "
                        "request as a delegate. Holding an approval of their "
                        "own as well would let one person satisfy two "
                        "approvals — end that delegation first.",
                        user=approver.user_id.name,
                    ),
                )
            if not delegate:
                continue
            if delegate == approver.user_id:
                trace.REFUSAL.event("delegate_is_self", approver=approver.id)
                raise ValidationError(
                    self.env._(
                        "You cannot delegate an approval to yourself.",
                    ),
                )
            if delegate == approver.request_id.request_owner_id:
                trace.REFUSAL.event(
                    "delegate_is_request_owner",
                    approver=approver.id,
                    delegate=delegate.id,
                )
                raise ValidationError(
                    self.env._(
                        "You cannot delegate this approval to the request "
                        "owner (%(owner)s) — they would approve their own "
                        "request.",
                        owner=delegate.name,
                    ),
                )
            if delegate in other_approvers.mapped("user_id"):
                trace.REFUSAL.event(
                    "delegate_is_co_approver",
                    approver=approver.id,
                    delegate=delegate.id,
                )
                raise ValidationError(
                    self.env._(
                        "%(delegate)s is already an approver on this "
                        "request. Delegating to a co-approver would let "
                        "one person hold two approvals.",
                        delegate=delegate.name,
                    ),
                )

    @api.model_create_multi
    def create(self, vals_list: list[dict]) -> Self:
        if any("state" in vals for vals in vals_list):
            self._raise_state_is_derived()
        self._check_access_create(vals_list)
        self._check_business_rules_create(vals_list)
        return super().create([self._stamp_pending_since(v) for v in vals_list])

    def write(self, vals: dict) -> bool:
        self._check_access_write(vals)
        self._check_business_rules_write(vals)
        delegation = self._DELEGATION_ONLY_FIELDS & vals.keys()
        previous_delegates = (
            {approver.id: approver.delegate_id for approver in self}
            if delegation
            else {}
        )
        if "state" in vals:
            self._raise_state_is_derived()
        result = super().write(self._stamp_pending_since(vals))
        if delegation:
            self._hand_activities_to_effective_approver(previous_delegates)
        return result

    def _hand_activities_to_effective_approver(
        self, previous_delegates: dict | None = None
    ) -> None:
        """A pending row's approval activity belongs to whoever may decide it now.

        Who that is changes without the delegation wizard: a delegation written on
        the row itself (the request form edits it), and the clock, since
        `is_delegated` is computed from today against the window. Left alone, the
        delegate may decide with nothing asking them to, and the principal holds a
        to-do they are refused on -- or the other way round once the window ends.
        """
        previous_delegates = previous_delegates or {}
        rows = self.filtered(
            lambda row: (
                row.state == "pending"
                and (row.delegate_id or previous_delegates.get(row.id))
            )
        )
        if not rows:
            return
        activities = rows.request_id._get_approval_activities().filtered(
            lambda activity: activity.approver_id in rows
        )
        for approver in rows:
            holder = approver._get_effective_approver()
            parties = (
                approver.user_id
                | approver.delegate_id
                | previous_delegates.get(approver.id, approver.delegate_id)
            )
            misplaced = activities.filtered(
                lambda activity, row=approver, holder=holder, parties=parties: (
                    activity.approver_id == row
                    and activity.user_id in parties
                    and activity.user_id != holder
                )
            )
            if not misplaced:
                continue
            trace.DELEGATION.event(
                "activity_follows_effective_approver",
                approver=approver.id,
                holder=holder.id,
                activities=misplaced.ids,
            )
            misplaced.write({"user_id": holder.id})

    @api.model
    def cron_hand_delegated_activities_over(self) -> None:
        """Move activities when a delegation window opens or closes today."""
        self.search(
            [("state", "=", "pending"), ("delegate_id", "!=", False)]
        )._hand_activities_to_effective_approver()

    def _raise_state_is_derived(self) -> None:
        trace.REFUSAL.event("approver_state_written", rows=self.ids, uid=self.env.uid)
        raise AccessError(
            self.env._(
                "An approver's status is derived from the decisions recorded on the "
                "request, and cannot be written."
            )
        )

    @api.depends("flow_state", "decision_log_ids", "decided_step_ids")
    def _compute_state(self):
        standing = self._get_standing_decisions()
        for row in self:
            verdict = standing.get(row.id)
            if verdict == "approved" or (
                verdict == "withdrawn" and row.decided_step_ids
            ):
                row.state = "approved"
            elif verdict == "refused":
                row.state = "refused"
            else:
                row.state = row.flow_state or "new"

    def _get_standing_decisions(self) -> dict:
        rows = self.filtered("id")
        if not rows:
            return {}
        facts = (
            self.env["approval.decision.log"]
            .sudo()
            .search_fetch(
                [
                    ("request_id", "in", rows.request_id.ids),
                    ("verdict", "in", ("approved", "refused", "withdrawn", "reset")),
                ],
                ["request_id", "approver_id", "verdict"],
                order="id",
            )
        )
        standing = {}
        for fact in facts:
            if fact.verdict == "reset":
                for row_id in [
                    row_id
                    for row_id, request_id in standing.items()
                    if request_id[1] == fact.request_id.id
                ]:
                    del standing[row_id]
                continue
            if fact.approver_id:
                standing[fact.approver_id.id] = (fact.verdict, fact.request_id.id)
        trace.DECISION.event(
            "standing_decisions",
            rows=rows.ids,
            facts=len(facts),
            standing=len(standing),
        )
        return {row_id: verdict for row_id, (verdict, _request) in standing.items()}

    def _stamp_pending_since(self, vals: dict) -> dict:
        state = vals.get("flow_state")
        if state == "pending":
            trace.DECISION.event("pending_clock", rows=self.ids, action="started")
            return {**vals, "pending_since": fields.Datetime.now()}
        if state == "new":
            trace.DECISION.event("pending_clock", rows=self.ids, action="cleared")
            return {**vals, "pending_since": False}
        return vals

    def unlink(self) -> bool:
        self._check_access_unlink()
        self._check_business_rules_unlink()
        trace.CRUD.note(
            "unlink_approvers",
            rows=self.ids,
            requests=self.request_id.ids,
            uid=self.env.uid,
        )
        return super().unlink()

    def _delegation_today(self):
        self.check_singleton()
        return self._delegation_today_by_tz()[self.user_id.tz or "UTC"]

    def _delegation_today_by_tz(self) -> dict:
        return {
            tz or "UTC": fields.Date.context_today(self.with_context(tz=tz or "UTC"))
            for tz in set(self.user_id.mapped("tz"))
        }

    @api.depends(
        "delegate_start_date", "delegate_end_date", "delegate_id", "user_id.tz"
    )
    def _compute_is_delegated(self):
        schedulable = self.filtered(
            lambda a: a.delegate_id and a.delegate_start_date and a.delegate_end_date,
        )
        (self - schedulable).is_delegated = False
        today_by_tz = schedulable._delegation_today_by_tz()
        for approver in schedulable:
            today = today_by_tz[approver.user_id.tz or "UTC"]
            approver.is_delegated = (
                approver.delegate_start_date <= today <= approver.delegate_end_date
            )

    @api.model
    def _delegation_date_buckets(self) -> dict:
        if (buckets := DELEGATION_TZ_BUCKETS.peek(self.env)) is not None:
            return buckets
        buckets = DELEGATION_TZ_BUCKETS(self.env)
        rows = (
            self.env["res.users"]
            .sudo()
            .with_context(active_test=False)
            ._read_group([], ["tz"])
        )
        for (tz,) in rows:
            local = fields.Date.context_today(self.with_context(tz=tz or "UTC"))
            buckets.setdefault(local, []).append(tz)
        return buckets

    @api.model
    def _search_is_delegated(self, operator, value):
        active = Domain.FALSE
        for local_date, tz_names in self._delegation_date_buckets().items():
            active |= Domain(
                [
                    ("user_id.tz", "in", tz_names),
                    ("delegate_id", "!=", False),
                    ("delegate_start_date", "<=", local_date),
                    ("delegate_end_date", ">=", local_date),
                ],
            )
        return boolean_search_domain(operator, value, active, ~active)

    def _fan_in_siblings(self) -> Self:
        siblings = self.request_id._get_current_pending_approver(
            self._get_effective_approver(),
        )
        trace.DECISION.event(
            "fan_in",
            request=self.request_id.id,
            approver=self.id,
            siblings=siblings.ids,
        )
        return siblings

    def action_approve(self) -> dict[str, Any] | None:
        self.check_singleton()
        return self.request_id.action_approve(self._fan_in_siblings())

    def action_refuse(self) -> dict[str, Any]:
        self.check_singleton()

        if self.env.context.get("skip_wizard"):
            return self.request_id.action_refuse(self._fan_in_siblings())

        return self.request_id._get_decision_wizard_action("refuse")

    def _create_activity(self):
        if not self:
            return
        if self.env.context.get("mail_activity_automation_skip"):
            return
        self = self._filtered_notifiable()
        if not self:
            return
        default_type = self.env.ref("approval.mail_activity_data_approval")
        date_deadline = fields.Date.context_today(self)

        taken = {
            (activity.approver_id.request_id.id, activity.user_id.id)
            for activity in self.request_id._get_approval_activities()
        }
        create_vals_list = []
        for approver in self:
            key = (approver.request_id.id, approver._get_effective_approver().id)
            if key in taken:
                continue
            taken.add(key)
            target = approver._get_activity_target()
            activity_type = approver._get_activity_type() or default_type
            create_vals_list.append(
                {
                    "activity_type_id": activity_type.id,
                    "summary": activity_type.summary,
                    "automated": True,
                    "note": activity_type.default_note,
                    "date_deadline": date_deadline,
                    "res_model_id": self.env["ir.model"]._get_id(target._name),
                    "res_id": target.id,
                    "user_id": key[1],
                    "approver_id": approver.id,
                    **approver._get_source_activity_values(target),
                },
            )
        trace.annotate(work=len(create_vals_list))
        trace.ACTIVITY.event(
            "create_plan",
            rows=self.ids,
            activities=len(create_vals_list),
            already_asked=len(taken) - len(create_vals_list),
        )
        trace.ACTIVITY.items(
            "create",
            lambda: [
                {
                    "approver": vals["approver_id"],
                    "user": vals["user_id"],
                    "model": vals["res_model_id"],
                    "res_id": vals["res_id"],
                    "type": vals["activity_type_id"],
                }
                for vals in create_vals_list
            ],
        )
        if create_vals_list:
            self.env["mail.activity"].create(create_vals_list)

    def _get_source_activity_values(self, target) -> dict:
        """What the source record adds to an activity asked on it; nothing when the
        activity lives on the request, which is no approval source."""
        self.check_singleton()
        if not isinstance(target, self.env.registry["mixin.approval.source"]):
            return {}
        return target.sudo()._get_approval_activity_values(self)

    def _is_advisory_only(self) -> bool:
        """Whether every step this row counts toward is advisory."""
        self.check_singleton()
        advisory_only = bool(self.step_ids) and all(self.step_ids.mapped("advisory"))
        trace.STEPS.event(
            "advisory_only",
            approver=self.id,
            steps=self.step_ids.ids,
            advisory_only=advisory_only,
        )
        return advisory_only

    def _get_activity_target(self):
        """The record this row's approver is asked on: the request, or its document."""
        self.check_singleton()
        request = self.request_id
        if request.category_id.activity_target == "document":
            document = request.get_source_document()
            if document and document.exists() and "activity_ids" in document._fields:
                trace.ACTIVITY.event(
                    "activity_target", approver=self.id, target=document
                )
                return document
        trace.ACTIVITY.event("activity_target", approver=self.id, target=request)
        return request

    def _get_activity_type(self):
        """The activity type of the first of this row's steps that names one, as the
        request's document chooses it."""
        self.check_singleton()
        step_type = (
            self.step_ids.sorted(lambda step: (step.sequence, step.id))
            .filtered("activity_type_id")[:1]
            .activity_type_id
        )
        document = self.request_id.get_source_document()
        if (
            isinstance(document, self.env.registry["mixin.approval.source"])
            and len(document) == 1
        ):
            chosen = document.sudo()._get_approval_activity_type(self, step_type)
            trace.ACTIVITY.event(
                "activity_type",
                approver=self.id,
                step_type=step_type.id if step_type else None,
                chosen=chosen.id if chosen else None,
                by="document",
            )
            return chosen
        trace.ACTIVITY.event(
            "activity_type",
            approver=self.id,
            step_type=step_type.id if step_type else None,
            chosen=step_type.id if step_type else None,
            by="step",
        )
        return step_type

    def _filtered_notifiable(self):
        """The rows whose approver should be asked now.

        Every activity is created through `_create_activity`, so this one filter
        orders the asking for all of its callers. A row that counts toward no step
        is asked as it always was. On a category that requests its steps in order,
        a row is asked only once one of its steps is among the lowest steps still
        unmet -- the decision is open from the start, the asking is not.
        """
        notifiable = self.filtered(lambda approver: approver._is_notifiable())
        trace.ACTIVITY.event(
            "notifiable_rows",
            rows=self.ids,
            asked=notifiable.ids,
            held=(self - notifiable).ids,
        )
        return notifiable

    def _is_notifiable(self) -> bool:
        """A step's group lets its members decide; only its listed members are asked.

        They are asked while a step they are listed for is still short of its quorum
        -- in order, once it opens -- and not for a step they may decide only through
        its group.
        """
        self.check_singleton()
        if not self.step_ids:
            return True
        document = self.request_id.get_source_document()
        listed = self.step_ids.filtered(
            lambda step: (
                (step.counts_added_approvers and not self.source_synced)
                or (
                    step.asks_group_members
                    and self.user_id in step.group_id.all_user_ids
                )
                or self.user_id.id
                in step._get_member_user_ids(document, request=self.request_id)
            )
        )
        if not listed:
            trace.ACTIVITY.event(
                "not_asked",
                approver=self.id,
                request=self.request_id.id,
                reason="group_only",
                steps=self.step_ids.ids,
            )
            return False
        if not self.request_id.category_id.notify_sequentially:
            wanted = listed & self.request_id._get_unmet_steps()
        else:
            wanted = listed & self.request_id._get_open_steps()
        wanted = wanted.filtered(lambda step: self.request_id._is_row_turn(self, step))
        trace.ACTIVITY.event(
            "notifiable",
            approver=self.id,
            request=self.request_id.id,
            listed=listed.ids,
            asked_for=wanted.ids,
            sequentially=self.request_id.category_id.notify_sequentially,
        )
        return bool(wanted)

    def _get_effective_approver(self):
        self.check_singleton()
        if self.is_delegated:
            trace.DELEGATION.event(
                "effective",
                approver=self.id,
                principal=self.user_id.id,
                delegate=self.delegate_id.id,
                until=self.delegate_end_date,
            )
            return self.delegate_id
        return self.user_id

    def _record_decision(
        self, verdict: str, actor=None, steps=None, date=None, note: str | None = None
    ) -> None:
        assert verdict in ("approved", "refused")
        for request, rows in self.grouped("request_id").items():
            decided = {
                row.id: steps if steps is not None else row.step_ids for row in rows
            }
            for row in rows:
                row.write(
                    {
                        "decided_step_ids": [Command.set(decided[row.id].ids)],
                        "decided_by_user_id": (actor or row.user_id).id,
                        **({"decision_date": date} if date else {}),
                    }
                )
            request._append_decision_log(
                verdict,
                rows=rows,
                actor=actor,
                steps_by_row=decided,
                note=note,
                date=date,
            )

    def _approve_for_every_step(self, note: str | None = None) -> None:
        """Approve rows nobody decided -- consent, an automatic rule -- for all their steps."""
        trace.DECISION.note("approve_every_step", rows=self.ids)
        for request, rows in self.grouped("request_id").items():
            for approver in rows:
                approver.write(
                    {"decided_step_ids": [Command.set(approver.step_ids.ids)]},
                )
            request._append_decision_log(
                "approved",
                rows=rows,
                actor=self.env.ref("base.user_root"),
                steps_by_row={row.id: row.step_ids for row in rows},
                note=note,
            )

    def _check_access_create(self, vals_list: list[dict]) -> None:
        if self._skip_check_access():
            return

        if not vals_list:
            return
        first_with_request = next(
            (v for v in vals_list if v.get("request_id")),
            None,
        )
        request_name = self.env._("New")
        if first_with_request:
            request = self.env["approval.request"].browse(
                first_with_request["request_id"]
            )
            if request.exists():
                request_name = request._label()
        trace.REFUSAL.event(
            "approver_create_manual",
            uid=self.env.uid,
            rows=len(vals_list),
        )
        raise AccessError(
            self.env._(
                "Approvers cannot be added manually.\n\n"
                "Approvers are defined by the approval category and "
                "managed automatically.\n\n"
                "Request: %(name)s",
                name=request_name,
            ),
        )

    def _check_access_unlink(self) -> None:
        if self._skip_check_access():
            return

        approver = self[:1]
        if approver:
            trace.REFUSAL.event(
                "approver_unlink_manual",
                uid=self.env.uid,
                rows=self.ids,
                request=approver.request_id.id,
            )
            raise AccessError(
                self.env._(
                    "Approvers cannot be removed from requests.\n\n"
                    "Approvers are defined by the approval category and managed "
                    "automatically. Removing them would break the approval workflow.\n\n"
                    "Request: %(name)s\nApprover: %(approver)s",
                    name=approver.request_id._label(),
                    approver=approver.user_id.name,
                ),
            )

    _DELEGATION_ONLY_FIELDS = frozenset(
        {"delegate_id", "delegate_start_date", "delegate_end_date"},
    )

    _SELF_WRITABLE_FIELDS = frozenset({"refusal_reason_id", "note"})

    def _check_access_write(self, vals: dict | None = None) -> None:
        if self._skip_check_access():
            return

        written = set(vals or ())
        if not written:
            return
        delegation_only = bool(written) and written.issubset(
            self._DELEGATION_ONLY_FIELDS,
        )
        decision_metadata_only = bool(written) and written.issubset(
            self._SELF_WRITABLE_FIELDS,
        )

        for approver in self:
            if delegation_only and self.env.user == approver.user_id:
                continue

            effective_approver = approver._get_effective_approver()
            if decision_metadata_only and effective_approver == self.env.user:
                continue

            if delegation_only and self.env.user == approver.delegate_id:
                trace.REFUSAL.event(
                    "delegation_write_by_delegate",
                    approver=approver.id,
                    uid=self.env.uid,
                )
                raise AccessError(
                    self.env._(
                        "Only the original approver (%(approver)s) can "
                        "modify the delegation of this approval.\n\n"
                        "Request: %(name)s",
                        name=approver.request_id._label(),
                        approver=approver.user_id.name,
                    ),
                )
            if effective_approver == self.env.user:
                trace.REFUSAL.event(
                    "workflow_managed_write",
                    approver=approver.id,
                    uid=self.env.uid,
                    fields=sorted(written),
                )
                raise AccessError(
                    self.env._(
                        "These fields are managed by the approval workflow "
                        "and cannot be modified directly (%(fields)s).\n\n"
                        "Use the Approve/Refuse buttons to record a "
                        "decision.\n\n"
                        "Request: %(name)s\nApprover: %(approver)s",
                        fields=", ".join(sorted(written)),
                        name=approver.request_id._label(),
                        approver=approver.user_id.name,
                    ),
                )
            if approver.is_delegated:
                trace.REFUSAL.event(
                    "write_while_delegated",
                    approver=approver.id,
                    uid=self.env.uid,
                    delegate=approver.delegate_id.id,
                )
                raise AccessError(
                    self.env._(
                        "This approval is currently delegated to %(delegate)s.\n\n"
                        "Request: %(name)s\nOriginal approver: %(approver)s",
                        name=approver.request_id._label(),
                        approver=approver.user_id.name,
                        delegate=approver.delegate_id.name,
                    ),
                )
            trace.REFUSAL.event(
                "write_not_approver",
                approver=approver.id,
                uid=self.env.uid,
                fields=sorted(written),
            )
            raise AccessError(
                self.env._(
                    "Only the assigned approver can modify their approval record.\n\n"
                    "Request: %(name)s\nApprover: %(approver)s",
                    name=approver.request_id._label(),
                    approver=approver.user_id.name,
                ),
            )

    _WORKFLOW_MANAGED_FIELDS = frozenset(
        {
            "state",
            "flow_state",
            "sequence",
            "required",
            "request_id",
            "user_id",
            "source_rule_id",
            "source_synced",
            "pending_since",
            "decision_date",
            "decided_by_user_id",
        },
    )

    def _check_business_rules_write(self, vals: dict) -> None:
        if self.env.su:
            return
        forced = set(vals) & self._WORKFLOW_MANAGED_FIELDS
        if forced:
            trace.REFUSAL.event(
                "forced_workflow_fields",
                rows=self.ids,
                uid=self.env.uid,
                fields=sorted(forced),
            )
            raise ValidationError(
                self.env._(
                    "%(fields)s cannot be modified directly — they are "
                    "managed by the approval workflow.\n\n"
                    "Use the Approve/Refuse buttons to record a decision, "
                    "or reconfigure the category/tier/rule that governs "
                    "this approver instead.",
                    fields=", ".join(sorted(forced)),
                ),
            )
        decision_metadata = set(vals) & self._SELF_WRITABLE_FIELDS
        if decision_metadata:
            terminal = self.env["approval.request"]._TERMINAL_STATES
            frozen = self.filtered(lambda a: a.request_id.state in terminal)
            if frozen:
                trace.REFUSAL.event(
                    "decision_metadata_frozen",
                    rows=frozen.ids,
                    fields=sorted(decision_metadata),
                )
                raise ValidationError(
                    self.env._(
                        "%(fields)s cannot be changed once the request is "
                        "approved, refused or cancelled — the decision record "
                        "is part of the audit trail.",
                        fields=", ".join(sorted(decision_metadata)),
                    ),
                )

    def _check_business_rules_create(self, vals_list: list[dict]) -> None:
        if self.env.su and self.env.context.get("approver_ids_computation"):
            return

        for vals in vals_list:
            request_id = vals.get("request_id")
            if not request_id:
                continue

            request = self.env["approval.request"].browse(request_id)
            if not request.exists():
                continue

            if request.state != "new":
                trace.REFUSAL.event(
                    "approver_create_not_draft",
                    request=request.id,
                    state=request.state,
                )
                raise ValidationError(
                    self.env._(
                        "Cannot add approvers to requests in %(state)s state.\n\n"
                        "Request: %(name)s\n\n"
                        "Approvers can only be modified while the request is "
                        "a draft. Reset a decided request to draft first — "
                        "the approver list is recomputed there.",
                        name=request._label(),
                        state=request.state,
                    ),
                )

    def _check_business_rules_unlink(self) -> None:
        if self.env.su and self.env.context.get("approver_ids_computation"):
            return

        for approver in self:
            if approver.request_id.state != "new":
                trace.REFUSAL.event(
                    "approver_unlink_not_draft",
                    approver=approver.id,
                    request=approver.request_id.id,
                    state=approver.request_id.state,
                )
                raise ValidationError(
                    self.env._(
                        "Cannot remove approvers from submitted requests.\n\n"
                        "Request: %(name)s\nApprover: %(approver)s\n"
                        "Current state: %(state)s\n\n"
                        "Approvers can only be removed from draft requests "
                        "to preserve the audit trail. Reset a decided "
                        "request to draft first — the approver list is "
                        "recomputed there.",
                        name=approver.request_id._label(),
                        approver=approver.user_id.name,
                        state=approver.request_id.state,
                    ),
                )

    def _skip_check_access(self) -> bool:
        return self.env.su or is_approval_manager(self.env)
