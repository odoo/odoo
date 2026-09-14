import base64
from typing import Any

from odoo import api, fields, models, tools
from odoo.exceptions import ValidationError
from odoo.fields import Command, Domain

from . import approval_trace as trace
from odoo.addons.base.models.mixin_catalog import name_uniq_index

ROUTES_BY_STEPS_CONTEXT = "approval_category_routes_by_steps"

CATEGORY_SELECTION = [
    ("required", "Required"),
    ("optional", "Optional"),
    ("no", "None"),
]


class ApprovalCategory(models.Model):
    _name = "approval.category"
    _description = "Approval Category"
    _inherit = ["mixin.mail.thread", "mixin.catalog"]
    _check_company_auto = True
    _order = "sequence, id"

    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        index=True,
        copy=False,
        tracking=True,
    )
    company_currency_id = fields.Many2one(
        related="company_id.currency_id",
        string="Company Currency",
        readonly=True,
    )
    active = fields.Boolean(tracking=True)
    color = fields.Integer(
        string="Color Index",
        help="Color used in kanban views for visual distinction",
    )
    sequence = fields.Integer()
    sequence_code = fields.Char(
        string="Code",
        required=True,
        help="Prefix used to build the request numbering sequence "
        "(e.g. 'BIZTRIP' → BIZTRIP00001). Must be unique per company.",
    )
    sequence_id = fields.Many2one(
        comodel_name="ir.sequence",
        string="Reference Sequence",
        copy=False,
        check_company=True,
    )
    image = fields.Binary(default=lambda self: self._default_image())
    description = fields.Char(translate=True)

    allow_self_approval = fields.Boolean(
        tracking=True,
        help="Whether the person asking may also decide their own request. Off, "
        "the requester is never asked by any step and any decision they attempt "
        "is refused.",
    )
    allowed_user_ids = fields.Many2many(
        comodel_name="res.users",
        relation="approval_category_allowed_user_rel",
        column1="category_id",
        column2="user_id",
        string="Allowed Users",
        help="Users who can create requests for this category. Leave empty to "
        "allow all users. This list does DOUBLE DUTY: with Approval "
        "Visibility set to 'Restricted to selected users' it is also the "
        "read audience, so filling it in to grant visibility necessarily "
        "restricts creation to the same people.",
    )
    allowed_group_ids = fields.Many2many(
        comodel_name="res.groups",
        relation="approval_category_allowed_group_rel",
        column1="category_id",
        column2="group_id",
        string="Allowed Groups",
        help="Security groups whose members can create requests for this "
        "category. Leave empty to allow all users. Does double duty as the "
        "read audience under 'Restricted to selected groups' — see Allowed "
        "Users.",
    )
    privacy_visibility = fields.Selection(
        selection=[
            ("private", "Only people involved"),
            ("restricted_users", "Restricted to selected users"),
            ("restricted_groups", "Restricted to selected groups"),
            ("employees", "All internal users"),
        ],
        string="Approval Visibility",
        default="private",
        required=True,
        tracking=True,
        help="""Who may READ the requests of this category (additive on top of
        the always-allowed requester/approvers/delegate and managers):

        • Only people involved: no extra read audience (requester, approvers
          and delegates always retain access regardless of this setting).
        • Restricted to selected users: the users in 'Allowed Users' may
          read every request in the category.
        • Restricted to selected groups: members of the groups in
          'Allowed Groups' may read every request in the category.
        • All internal users: every internal user may read every request.

        The 'restricted_*' modes read the audience from the SAME 'Allowed
        Users'/'Allowed Groups' lists that gate request creation, and those
        lists mean "everyone" only while they are EMPTY. So choosing a
        restricted mode is not a read-only decision: to name an audience you
        must fill a list in, and filling it in restricts creation to exactly
        those people. There is deliberately no way to say "anyone may
        request, only this group may read" — that would need an audience
        list separate from the create-gate. Widening read access to a
        supervisor group therefore also hands that group exclusive rights to
        file in the category; if that is not what you want, keep the category
        'Only people involved' and give the supervisors the Administrator
        group instead, which reads everything without touching creation.""",
    )
    approval_minimum = fields.Integer(
        string="Minimum Approval",
        default=1,
        required=True,
        tracking=True,
    )
    approval_type = fields.Selection(
        selection=[("general", "General")],
        tracking=True,
        help="Category of approval for filtering and grouping purposes "
        "(e.g., 'purchase', 'expense', 'vacation'). "
        "Used to organize and filter approval requests.",
    )
    target_model = fields.Selection(
        selection=[],
        tracking=True,
        help="Technical name of the model to create when this approval is granted. "
        "Leave empty if the approval is for an existing record (e.g., approving a purchase order). "
        "Set to model name (e.g., 'purchase.order') if approval should create a new record.",
    )
    rule_ids = fields.One2many(
        comodel_name="approval.rule",
        inverse_name="category_id",
        string="Conditional Rules",
    )
    step_ids = fields.One2many(
        comodel_name="approval.category.step",
        inverse_name="category_id",
        string="Steps",
        context={"active_test": True},
        help="The pools a request of this category must pass, each needing its own "
        "approvals. Every request routes by the steps whose condition it meets.",
    )
    notify_sequentially = fields.Boolean(
        string="Request Steps In Order",
        tracking=True,
        help="Only for categories with steps. Every step may be decided at any time, "
        "but its approvers are only asked -- given an activity -- once every earlier "
        "step is met. It orders the asking, not the deciding.",
    )
    activity_target = fields.Selection(
        selection=[
            ("request", "Approval Request"),
            ("document", "Source Document"),
        ],
        string="Ask Approvers On",
        default="request",
        help="Where an approver's activity is created. Source Document asks on the "
        "record being approved, when the request has one that can hold activities; "
        "the activity still decides the request when done.",
    )
    rule_count = fields.Integer(
        compute="_compute_rule_count",
        help="Number of active conditional rules",
    )
    count_request_to_validate = fields.Integer(
        string="Number of requests to validate",
        compute="_compute_count_request_to_validate",
    )

    kanban_dashboard = fields.Json(
        compute="_compute_kanban_dashboard",
        help="The counters the category kanban card renders. A Json field, "
        "not Text holding JSON: the template used to JSON.parse() the raw "
        "value in two separate t-set expressions, which is the client "
        "re-deriving a structure the ORM can hand it directly.",
    )
    show_on_dashboard = fields.Boolean(
        string="Show on Dashboard",
        default=True,
        help="Show this category on the approval dashboard",
    )

    approval_deadline_hours = fields.Integer(
        string="Approval Deadline (Hours)",
        default=48,
        tracking=True,
        help="Number of hours before approval is considered overdue. "
        "Set to 0 to disable deadline tracking for this category.",
    )
    escalate_overdue = fields.Boolean(
        string="Auto-Escalate Overdue Requests",
        default=False,
        tracking=True,
        help="Automatically escalate overdue requests to escalation contact",
    )
    escalation_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Escalation Contact",
        tracking=True,
        help="User notified by the escalation cron when this category's "
        "requests are overdue and no approver-specific manager is found "
        "(see _get_escalation_manager). Leave empty to fall back to a "
        "plain reminder to the pending approvers.",
    )
    auto_expire_hours = fields.Integer(
        string="Auto-Expire After (Hours)",
        default=0,
        tracking=True,
        help="Automatically CANCEL requests that remain pending beyond this "
        "many hours (terminal 'cancelled', recoverable via reset to draft — "
        "expiration is not a refusal: nobody decided). Set to 0 to disable.",
    )

    sla_target_hours = fields.Integer(
        string="SLA Target (Hours)",
        default=0,
        tracking=True,
        help="Target time for complete approval cycle. "
        "Used for compliance reporting. 0 = no SLA tracking.",
    )
    sla_warning_pct = fields.Integer(
        string="SLA Warning (%)",
        default=80,
        tracking=True,
        help="Warn when this percentage of SLA time has elapsed",
    )

    consent_approval_hours = fields.Integer(
        string="Consent Approval (Hours)",
        default=0,
        tracking=True,
        help="Auto-approve if no objection within N hours. "
        "0 = disabled. Only applies when all required approvers "
        "have not refused within the window.",
    )

    _name_src_uniq = name_uniq_index(
        "company_id",
        message="An approval category with this name already exists for this company.",
    )

    _sequence_code_uniq = models.Constraint(
        "unique nulls not distinct (sequence_code, company_id)",
        "The sequence code must be unique per company.",
    )

    @api.constrains("approval_minimum")
    def _constrains_approval_minimum(self) -> None:
        for category in self:
            if category.approval_minimum < 1:
                trace.REFUSAL.event(
                    "minimum_below_one",
                    category=category.id,
                    minimum=category.approval_minimum,
                )
                raise ValidationError(
                    self.env._(
                        "Minimum Approval must be at least 1.",
                    ),
                )

    @api.constrains("consent_approval_hours", "step_ids")
    def _constrains_consent_sequential(self) -> None:
        for category in self:
            ordered = any(category.step_ids.mapped("in_order"))
            if ordered and category.consent_approval_hours:
                trace.REFUSAL.event(
                    "consent_with_sequential",
                    category=category.id,
                    hours=category.consent_approval_hours,
                )
                raise ValidationError(
                    self.env._(
                        "Consent-based auto-approval cannot be used with "
                        "sequential approval. Disable one or the other.",
                    ),
                )

    @api.model
    def default_get(self, fields):
        defaults = super().default_get(fields)
        if (
            "step_ids" in fields
            and "step_ids" not in defaults
            and self.env.context.get(ROUTES_BY_STEPS_CONTEXT)
        ):
            defaults["step_ids"] = [
                Command.create(
                    {
                        "name": self.env._("Approvers"),
                        "sequence": 10,
                        "minimum": 1,
                        "counts_added_approvers": True,
                    }
                )
            ]
            trace.STEPS.event("category_born_with_steps", fields=len(fields))
        return defaults

    @api.model_create_multi
    def create(self, vals_list: list[dict[str, Any]]) -> Any:
        batch_codes: set[str] = {
            vals["sequence_code"] for vals in vals_list if vals.get("sequence_code")
        }
        bases = {
            vals_index: (
                "".join(c for c in (vals.get("name") or "APR").upper() if c.isalnum())[
                    :8
                ]
                or "APR"
            )
            for vals_index, vals in enumerate(vals_list)
            if not vals.get("sequence_code")
        }
        taken_by_base: dict[str, set[str]] = {base: set() for base in bases.values()}
        if taken_by_base:
            existing = (
                self.sudo()
                .with_context(active_test=False)
                .search(
                    Domain.OR(
                        Domain("sequence_code", "=like", f"{base}%")
                        for base in taken_by_base
                    ),
                )
                .mapped("sequence_code")
            )
            for code in existing:
                for base, taken in taken_by_base.items():
                    if code.startswith(base):
                        taken.add(code)
        for vals_index, vals in enumerate(vals_list):
            if not vals.get("sequence_code"):
                base = bases[vals_index]
                taken = taken_by_base[base]
                code = base
                counter = 1
                while code in batch_codes or code in taken:
                    counter += 1
                    code = f"{base}{counter}"
                vals["sequence_code"] = code
                batch_codes.add(code)
            if vals.get("sequence_code") and not vals.get("sequence_id"):
                code = vals["sequence_code"]
                sequence = (
                    self.env["ir.sequence"]
                    .sudo()
                    .create(
                        {
                            "name": self.env._("Sequence %(code)s", code=code),
                            "padding": 5,
                            "prefix": code,
                            "company_id": vals.get("company_id"),
                        },
                    )
                )
                vals["sequence_id"] = sequence.id
                trace.CRUD.event(
                    "category_sequence",
                    code=code,
                    sequence=sequence.id,
                    company=vals.get("company_id"),
                )
        return super().create(vals_list)

    def write(self, vals: dict[str, Any]) -> bool:
        if "sequence_code" in vals and "sequence_id" not in vals:
            sequence_vals = {
                "name": self.env._("Sequence %(code)s", code=vals["sequence_code"]),
                "padding": 5,
                "prefix": vals["sequence_code"],
            }
            if "company_id" in vals:
                sequence_vals["company_id"] = vals["company_id"]
            have_seq = self.filtered("sequence_id")
            need_seq = self - have_seq
            have_seq.sequence_id.sudo().write(sequence_vals)
            new_sequences = (
                self.env["ir.sequence"]
                .sudo()
                .create(
                    [
                        {
                            **sequence_vals,
                            "company_id": vals.get(
                                "company_id", category.company_id.id
                            ),
                        }
                        for category in need_seq
                    ],
                )
            )
            result = super().write(vals)
            for category, sequence in zip(need_seq, new_sequences, strict=True):
                category.sequence_id = sequence
            return result

        if "company_id" in vals:
            for category in self:
                if category.sequence_id:
                    category.sequence_id.company_id = vals.get("company_id")

        return super().write(vals)

    @api.depends_context("uid")
    def _compute_count_request_to_validate(self) -> None:
        domain = self.env["approval.request"]._get_domain_pending_review(
            self.env.user,
        )
        requests_data = self.env["approval.request"]._read_group(
            domain,
            ["category_id"],
            ["__count"],
        )
        requests_mapped_data = {category.id: count for category, count in requests_data}
        for category in self:
            category.count_request_to_validate = requests_mapped_data.get(
                category.id,
                0,
            )
        trace.COMPUTE.event(
            "count_request_to_validate",
            n=len(self),
            uid=self.env.uid,
            with_requests=len(requests_mapped_data),
            requests=sum(requests_mapped_data.values()),
        )

    def _compute_rule_count(self) -> None:
        data = self.env["approval.rule"]._read_group(
            [("category_id", "in", self.ids), ("active", "=", True)],
            ["category_id"],
            ["__count"],
        )
        mapped = {cat.id: count for cat, count in data}
        for category in self:
            category.rule_count = mapped.get(category.id, 0)
        trace.RULES.event(
            "rule_count",
            n=len(self),
            with_rules=len(mapped),
            rules=sum(mapped.values()),
        )

    @api.depends_context("uid")
    def _compute_kanban_dashboard(self) -> None:
        if not self:
            return

        approval_request = self.env["approval.request"]
        today = fields.Date.today()
        first_day_of_month = today.replace(day=1)
        category_ids = self.ids
        show_company = len(self.env.companies) > 1

        state_data = approval_request._read_group(
            domain=[("category_id", "in", category_ids)],
            groupby=["category_id", "state"],
            aggregates=["__count"],
        )
        state_counts: dict[int, dict[str, int]] = {cid: {} for cid in category_ids}
        for category, state, count in state_data:
            state_counts[category.id][state] = count

        approved_data = approval_request._read_group(
            domain=[
                ("category_id", "in", category_ids),
                ("state", "=", "approved"),
                ("date_approval_granted", ">=", first_day_of_month),
            ],
            groupby=["category_id"],
            aggregates=["__count"],
        )
        approved_this_month = {cat.id: count for cat, count in approved_data}

        refused_data = approval_request._read_group(
            domain=[
                ("category_id", "in", category_ids),
                ("state", "=", "refused"),
                ("date_refused", ">=", first_day_of_month),
            ],
            groupby=["category_id"],
            aggregates=["__count"],
        )
        refused_this_month = {cat.id: count for cat, count in refused_data}

        my_requests_data = approval_request._read_group(
            domain=[
                ("category_id", "in", category_ids),
                ("request_owner_id", "=", self.env.user.id),
                ("state", "in", ["new", "pending"]),
            ],
            groupby=["category_id"],
            aggregates=["__count"],
        )
        my_requests_counts = {cat.id: count for cat, count in my_requests_data}

        late_counts: dict[int, int] = {}
        categories_with_deadlines = self.filtered(
            lambda c: c.approval_deadline_hours > 0
        )
        if categories_with_deadlines:
            late_data = approval_request._read_group(
                [
                    ("category_id", "in", categories_with_deadlines.ids),
                    *approval_request._get_domain_overdue(),
                ],
                groupby=["category_id"],
                aggregates=["__count"],
            )
            late_counts = {cat.id: count for cat, count in late_data}

        for category in self:
            cat_states = state_counts.get(category.id, {})
            total = sum(cat_states.values())
            late_count = late_counts.get(category.id, 0)

            dashboard_data = {
                "total_requests": total,
                "new_count": cat_states.get("new", 0),
                "pending_count": cat_states.get("pending", 0),
                "approved_count": approved_this_month.get(category.id, 0),
                "refused_count": refused_this_month.get(category.id, 0),
                "late_count": late_count,
                "to_review_count": category.count_request_to_validate,
                "my_requests_count": my_requests_counts.get(category.id, 0),
                "has_late_requests": late_count > 0,
                "show_company": show_company,
                "rule_count": category.rule_count,
            }
            trace.COMPUTE.event(
                "kanban_dashboard",
                category=category.id,
                total=total,
                late=late_count,
                to_review=dashboard_data["to_review_count"],
                mine=dashboard_data["my_requests_count"],
            )
            category.kanban_dashboard = dashboard_data

    def _add_approver(self, user, required=False, sequence=10) -> None:
        """Add `user` as an approver of every request: a member of the category's pool
        step, the first step counting approvers added by hand."""
        for category in self:
            pool = (
                category.step_ids.filtered("counts_added_approvers")
                or category.step_ids
            )[:1]
            trace.STEPS.event(
                "approver_added_to_step",
                category=category.id,
                user=user.id,
                required=required,
                step=pool.id,
                counts_added=pool.counts_added_approvers,
            )
            if not pool:
                category.step_ids = [
                    Command.create(
                        {
                            "name": self.env._("Approvers"),
                            "sequence": 10,
                            "minimum": max(category.approval_minimum, 1),
                            "counts_added_approvers": True,
                        }
                    )
                ]
                pool = category.step_ids[:1]
            pool.member_ids = [
                Command.create(
                    {"user_id": user.id, "required": required, "sequence": sequence}
                )
            ]

    def create_request(self) -> dict[str, Any]:
        self.check_singleton()
        return {
            "type": "ir.actions.act_window",
            "res_model": "approval.request",
            "views": [[False, "form"]],
            "context": {
                "default_category_id": self.id,
                "default_request_owner_id": self.env.user.id,
            },
        }

    def _default_image(self) -> bytes:
        with tools.file_open("approval/static/src/img/Folder.png", "rb") as icon_file:
            return base64.b64encode(icon_file.read())

    def _is_applicable_for(self, document) -> bool:
        self.check_singleton()
        trace.SUBJECTS.event(
            "category_applicable", category=self.id, subject=document, applicable=True
        )
        return True

    def _get_view_request(
        self, label: str, extra_domain: list | None = None
    ) -> dict[str, Any]:
        self.check_singleton()
        domain = [("category_id", "=", self.id)]
        if extra_domain:
            domain.extend(extra_domain)
        trace.REPORT.note(
            "view_request",
            category=self.id,
            label=label or None,
            filters=len(extra_domain or ()),
        )
        return {
            "type": "ir.actions.act_window",
            "name": f"{label} - {self.name}" if label else self.name,
            "res_model": "approval.request",
            "view_mode": "list,kanban,form",
            "domain": domain,
            "context": {"default_category_id": self.id},
        }

    def action_view(self) -> dict[str, Any]:
        return self._get_view_request("")

    def view_requests_pending(self) -> dict[str, Any]:
        return self._get_view_request(
            self.env._("Pending"), [("state", "=", "pending")]
        )

    def view_requests_draft(self) -> dict[str, Any]:
        return self._get_view_request(self.env._("Drafts"), [("state", "=", "new")])

    def view_requests_late(self) -> dict[str, Any]:
        if self.approval_deadline_hours <= 0:
            return self.view_requests_pending()
        return self._get_view_request(
            self.env._("Overdue"),
            self.env["approval.request"]._get_domain_overdue(),
        )

    def view_requests_user(self) -> dict[str, Any]:
        return self._get_view_request(
            self.env._("My Requests"),
            [
                ("request_owner_id", "=", self.env.user.id),
            ],
        )

    def view_requests_approved(self) -> dict[str, Any]:
        first_day_of_month = fields.Date.today().replace(day=1)
        return self._get_view_request(
            self.env._("Approved"),
            [
                ("state", "=", "approved"),
                ("date_approval_granted", ">=", first_day_of_month),
            ],
        )

    def view_requests_refused(self) -> dict[str, Any]:
        first_day_of_month = fields.Date.today().replace(day=1)
        return self._get_view_request(
            self.env._("Refused"),
            [
                ("state", "=", "refused"),
                ("date_refused", ">=", first_day_of_month),
            ],
        )

    def view_requests_to_review(self) -> dict[str, Any]:
        return self._get_view_request(
            self.env._("To Review"),
            self.env["approval.request"]._get_domain_pending_review(self.env.user),
        )

    def view_rules(self) -> dict[str, Any]:
        self.check_singleton()
        return {
            "name": self.env._("Rules: %s", self.name),
            "type": "ir.actions.act_window",
            "res_model": "approval.rule",
            "view_mode": "list,form",
            "domain": [("category_id", "=", self.id)],
            "context": {"default_category_id": self.id},
        }
