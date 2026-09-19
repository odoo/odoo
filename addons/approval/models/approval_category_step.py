from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command

from . import approval_trace as trace


class ApprovalCategoryStep(models.Model):
    _name = "approval.category.step"
    _inherit = ["mixin.approval.threshold", "mixin.approval.domain"]
    _description = "Approval Step"
    _order = "category_id, sequence, id"

    category_id = fields.Many2one(
        comodel_name="approval.category",
        index=True,
        required=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(
        related="category_id.company_id",
        # mixin.approval.threshold declares it stored, indexed and precomputed
        precompute=False,
        store=False,
        index=False,
        readonly=True,
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(
        translate=True,
        required=True,
    )
    active = fields.Boolean(default=True)
    minimum = fields.Integer(
        string="Approvals Needed",
        default=1,
        help="How many approvals from this step's pool complete it.",
    )
    member_ids = fields.One2many(
        comodel_name="approval.category.step.member",
        inverse_name="step_id",
        string="Members",
    )
    user_ids = fields.Many2many(
        comodel_name="res.users",
        string="Approvers",
        compute="_compute_user_ids",
        inverse="_inverse_user_ids",
        help="The step's current members, as an editable list. Delegated members are "
        "kept as they are when this list is edited.",
    )
    group_id = fields.Many2one(
        comodel_name="res.groups",
        string="Approval Group",
        help="Every member of this group may approve the step, together with the "
        "step's own members.",
    )
    exclusive = fields.Boolean(
        help="An approval that counts toward this step counts toward no other step "
        "of the same request, and the other way round: a user who decided an "
        "exclusive step decides nothing else on that request."
    )
    asks_group_members = fields.Boolean(
        string="Asks the Group's Members",
        help="Every member of the approval group is asked, with an activity and an "
        "e-mail. Off, the group is a queue its members decide from To Review, and "
        "only the step's listed members are asked.",
    )
    counts_added_approvers = fields.Boolean(
        string="Counts Approvers Added to the Request",
        help="Approvers added by hand to a request, beyond those routing names, join "
        "this step: they are asked, may decide it, and their approvals count toward "
        "its quorum. It is how a category routed by its approver list treated them.",
    )
    in_order = fields.Boolean(
        string="Members Decide in Order",
        help="The step's members decide one after another, in the members' order: "
        "only the first who has not approved it yet is asked and may decide. The "
        "step's quorum ends the chain, so a quorum of one stops at the first "
        "approval.",
    )
    advisory = fields.Boolean(
        help="The step's approvers are asked and their decisions recorded, but the "
        "step decides nothing: the request is approved without it, and a refusal "
        "given for it alone refuses nothing."
    )
    notify_user_ids = fields.Many2many(
        comodel_name="res.users",
        relation="approval_step_notify_user_rel",
        column1="step_id",
        column2="user_id",
        string="Notify",
        help="Posted an internal note when an approver of this step decides.",
    )
    subject_model_id = fields.Many2one(
        comodel_name="ir.model",
        string="Source Model",
        ondelete="cascade",
        help="Model the condition reads. Required when a condition is set.",
    )
    subject_model_name = fields.Char(
        related="subject_model_id.model",
        string="Source Model Name",
        help="The source model's technical name, which the condition's domain editor "
        "reads its fields from.",
    )
    subject_domain = fields.Char(
        string="Applies When",
        help="Domain on the request's source document. The step applies only to "
        "requests whose source document matches; empty means every request.",
    )

    when_rule_ids = fields.Many2many(
        comodel_name="approval.rule",
        relation="approval_step_when_rule_rel",
        column1="step_id",
        column2="rule_id",
        string="When Rules Match",
        help="The step applies only when every one of these rules matches the "
        "request, as the rule itself evaluates it: a figure, the source document, "
        "and the rule's company.",
    )
    unless_rule_ids = fields.Many2many(
        comodel_name="approval.rule",
        relation="approval_step_unless_rule_rel",
        column1="step_id",
        column2="rule_id",
        string="Unless Rules Match",
        help="The step does not apply when any of these rules matches the request.",
    )

    activity_type_id = fields.Many2one(
        comodel_name="mail.activity.type",
        help="The activity this step's approvers are asked with. Empty uses the "
        "approval activity.",
    )
    subject_user_sequence = fields.Integer(
        string="Place in Order",
        default=10,
        help="On a step whose members decide in order, where the users the source "
        "field names stand among the members' sequences.",
    )
    subject_user_required = fields.Boolean(
        string="Named Users Are Required",
        help="The step waits for every user the source field names, whatever its "
        "quorum.",
    )
    subject_user_path = fields.Char(
        string="Approvers From",
        help="Field path on the source document naming users who approve this step, "
        "e.g. employee_id.leave_manager_id. Each document names its own approvers.",
    )

    @api.constrains("in_order")
    def _check_in_order_without_consent(self) -> None:
        for step in self.filtered("in_order"):
            if step.category_id.consent_approval_hours:
                trace.REFUSAL.event(
                    "in_order_step_with_consent",
                    step=step.id,
                    category=step.category_id.id,
                )
                raise ValidationError(
                    self.env._(
                        "Step '%(step)s' lets its members decide in order, and "
                        "consent-based auto-approval approves every member at once. "
                        "Disable one or the other.",
                        step=step.name,
                    )
                )

    @api.constrains("in_order", "group_id")
    def _check_in_order_pool(self) -> None:
        for step in self.filtered("in_order"):
            if step.group_id:
                trace.REFUSAL.event(
                    "step_in_order_unordered_pool",
                    step=step.id,
                    group=step.group_id.id,
                )
                raise ValidationError(
                    self.env._(
                        "Step '%(step)s' lets its members decide in order, so a "
                        "group's users, who have no place in that order, cannot "
                        "decide it.",
                        step=step.name,
                    )
                )

    @api.constrains("condition_field", "operator", "threshold", "threshold_max")
    def _check_figure_condition(self) -> None:
        for step in self.filtered("condition_field"):
            if not step.operator:
                trace.REFUSAL.event(
                    "step_figure_without_operator",
                    step=step.id,
                    field=step.condition_field,
                )
                raise ValidationError(
                    self.env._(
                        "Step '%(step)s' compares the request's %(field)s but says "
                        "not how: choose a comparison.",
                        step=step.name,
                        field=step.condition_field,
                    )
                )
            if (
                step.operator == "between"
                and step.threshold_max
                and step.threshold_max <= step.threshold
            ):
                trace.REFUSAL.event(
                    "step_figure_band_inverted",
                    step=step.id,
                    threshold=step.threshold,
                    threshold_max=step.threshold_max,
                )
                raise ValidationError(
                    self.env._(
                        "Step '%(step)s' applies between %(low)s and %(high)s: the "
                        "upper bound must be above the lower one, or 0 for no bound.",
                        step=step.name,
                        low=step.threshold,
                        high=step.threshold_max,
                    )
                )

    def _domain_source_field(self) -> str:
        return "subject_domain"

    @api.constrains(
        "minimum", "member_ids", "group_id", "user_ids", "subject_user_path"
    )
    def _check_pool(self) -> None:
        for step in self:
            if step.minimum < 1:
                trace.REFUSAL.event(
                    "step_minimum_below_one", step=step.id, minimum=step.minimum
                )
                raise ValidationError(
                    self.env._(
                        "Step '%(step)s' needs at least one approval.", step=step.name
                    ),
                )
            if not (
                step.member_ids
                or step.group_id
                or step.subject_user_path
                or step.counts_added_approvers
            ):
                trace.REFUSAL.event("step_has_no_pool", step=step.id)
                raise ValidationError(
                    self.env._(
                        "Step '%(step)s' has nobody who could approve it: give it "
                        "members, an approval group, or a field on the source "
                        "document that names its approvers.",
                        step=step.name,
                    ),
                )

    @api.constrains("subject_user_path", "subject_model_id")
    def _check_source_user_path(self) -> None:
        for step in self.filtered("subject_user_path"):
            model = step.subject_model_id and self.env.get(step.subject_model_id.model)
            if model is None or not step.subject_model_id:
                trace.REFUSAL.event(
                    "source_user_path_without_model",
                    step=step.id,
                    path=step.subject_user_path,
                )
                raise ValidationError(
                    self.env._(
                        "Step '%(step)s' names its approvers through %(path)s, so it "
                        "needs the source model that field is on.",
                        step=step.name,
                        path=step.subject_user_path,
                    ),
                )
            step._check_field_path(model, step.subject_user_path)
            if step._get_path_terminal_field(model).comodel_name != "res.users":
                trace.REFUSAL.event(
                    "source_user_path_not_users",
                    step=step.id,
                    path=step.subject_user_path,
                    model=step.subject_model_id.model,
                )
                raise ValidationError(
                    self.env._(
                        "Step '%(step)s' names its approvers through %(path)s, which "
                        "does not lead to users.",
                        step=step.name,
                        path=step.subject_user_path,
                    ),
                )

    def _get_path_terminal_field(self, model):
        self.check_singleton()
        current, field = model, None
        for part in self.subject_user_path.split("."):
            field = current._fields[part]
            if field.relational:
                current = self.env[field.comodel_name]
        return field

    @api.constrains("subject_domain", "subject_model_id")
    def _check_condition(self) -> None:
        for step in self.filtered("subject_domain"):
            model = step.subject_model_id and self.env.get(step.subject_model_id.model)
            if model is None or not step.subject_model_id:
                trace.REFUSAL.event(
                    "step_condition_without_model",
                    step=step.id,
                    condition=step.subject_domain,
                )
                raise ValidationError(
                    self.env._(
                        "Step '%(step)s' has a condition, so it needs the source "
                        "model that condition reads.",
                        step=step.name,
                    ),
                )
            step._check_domain_against_model(model)

    @api.depends("member_ids.user_id", "member_ids.date_end")
    def _compute_user_ids(self) -> None:
        today = fields.Date.context_today(self)
        for step in self:
            step.user_ids = step.member_ids.filtered(
                lambda member: not member.date_end or member.date_end >= today
            ).user_id

    def _inverse_user_ids(self) -> None:
        for step in self:
            users = step.user_ids
            missing = users - step.member_ids.user_id
            if missing:
                step.member_ids = [
                    Command.create({"user_id": user.id}) for user in missing
                ]
            step.member_ids.filtered(
                lambda member, users=users: (
                    not member.delegated_by_id and member.user_id not in users
                )
            ).unlink()
        self._check_pool()

    def _get_member_user_ids(
        self, document=None, company=None, request=None
    ) -> set[int]:
        self.check_singleton()
        today = fields.Date.context_today(self)
        current = {
            member.user_id.id
            for member in self.member_ids
            if not member.date_end or member.date_end >= today
        }
        from_document = self._get_source_user_ids(document, request)
        in_company = self._filter_company_user_ids(current | from_document, company)
        trace.STEPS.event(
            "member_users",
            step=self.id,
            members=len(self.member_ids),
            current=sorted(current),
            from_document=sorted(from_document),
            excluded_by_company=sorted((current | from_document) - in_company),
        )
        return in_company

    def _get_subject(self, document, request):
        """The record the step's condition and approver path read: the request itself
        when the step's source model is approval.request, else its source document."""
        self.check_singleton()
        if request and self.subject_model_id.model == request._name:
            return request
        return document

    def _get_source_user_ids(self, document, request=None) -> set[int]:
        self.check_singleton()
        subject = self._get_subject(document, request)
        if (
            not self.subject_user_path
            or not subject
            or subject._name != self.subject_model_id.model
        ):
            return set()
        users = subject.sudo().exists().mapped(self.subject_user_path)
        named = set(users.filtered("active").ids)
        trace.STEPS.event(
            "source_users",
            step=self.id,
            path=self.subject_user_path,
            document=subject,
            users=sorted(named),
        )
        return named

    def _get_pool_user_ids(self, document=None, company=None, request=None) -> set[int]:
        """Who may approve this step today: valid members, the users the document
        names, and the group's users -- of those, the ones who work in `company` and
        whom the document's own policy lets decide it."""
        self.check_singleton()
        members = self._get_member_user_ids(document, company, request)
        users = set(members)
        if self.group_id:
            users.update(
                self._filter_company_user_ids(
                    set(self.group_id.all_user_ids.ids), company
                )
            )
        pool = self._filter_document_user_ids(users, document)
        trace.STEPS.event(
            "pool",
            step=self.id,
            minimum=self.minimum,
            company=company.id if company else None,
            members=sorted(members),
            with_group=sorted(users - members),
            refused_by_document=sorted(users - pool),
            pool=sorted(pool),
        )
        return pool

    def _get_candidate_user_ids(self, document=None, request=None) -> set[int]:
        """Every user the step names for `document`, before the request's company or
        the document's policy narrows them: routing owns the rows of all of them."""
        self.check_singleton()
        users = self._get_member_user_ids(document, request=request)
        if self.group_id:
            users.update(self.group_id.all_user_ids.ids)
        return users

    def _filter_document_user_ids(self, user_ids: set[int], document) -> set[int]:
        """A record an approval request is raised for (mixin.approval.source) keeps a
        user off its step when its own policy would refuse that user's decision."""
        self.check_singleton()
        if (
            not user_ids
            or not isinstance(document, self.env.registry["mixin.approval.source"])
            or len(document) != 1
        ):
            return user_ids
        kept = document.sudo()._filter_approval_step_user_ids(self, set(user_ids))
        trace.STEPS.event(
            "document_filtered_users",
            step=self.id,
            document=document,
            asked=sorted(user_ids),
            refused=sorted(set(user_ids) - set(kept)),
        )
        return kept

    def _filter_company_user_ids(self, user_ids: set[int], company) -> set[int]:
        """An approver row belongs to its request's company, so only a user allowed
        in that company can hold one."""
        if not company or not user_ids:
            return user_ids
        users = self.env["res.users"].sudo().browse(user_ids)
        return set(users.filtered(lambda user: company in user.company_ids).ids)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_step_holding_decisions(self) -> None:
        decided = (
            self.env["approval.approver"]
            .sudo()
            .search_count(
                [
                    ("step_ids", "in", self.ids),
                    ("state", "in", ("approved", "refused")),
                ],
                limit=1,
            )
        )
        if decided:
            trace.REFUSAL.event("step_holds_decisions", steps=self.ids)
            raise UserError(
                self.env._(
                    "A step that holds decisions cannot be deleted. Archive it "
                    "instead, so the decisions keep the step they were given for."
                ),
            )

    def _is_applicable_to_request(self, request, matched_rules=None) -> bool:
        self.check_singleton()
        if self.condition_field and not self._matches_request_figure(request):
            return False
        if not self._matches_request_rules(request, matched_rules):
            return False
        if not self.subject_domain:
            return True
        return self._is_applicable_to_document(
            self._get_subject(request.get_source_document(), request)
        )

    def _matches_request_rules(self, request, matched=None) -> bool:
        self.check_singleton()
        if not self.when_rule_ids and not self.unless_rule_ids:
            return True
        if matched is None:
            matched = request._get_step_rule_matches(
                self.when_rule_ids | self.unless_rule_ids
            )
        matches = self.when_rule_ids <= matched and not (self.unless_rule_ids & matched)
        trace.STEPS.event(
            "rule_conditions",
            step=self.id,
            request=request.id,
            when=self.when_rule_ids.ids,
            unless=self.unless_rule_ids.ids,
            matched=matched.ids,
            matches=matches,
        )
        return matches

    def _matches_request_figure(self, request) -> bool:
        """The step's numeric condition on the request itself: its amount, quantity,
        date range or priority, which a request with no source document has too."""
        self.check_singleton()
        measured = self._get_field_value(request)
        matches = measured is not None and self._compare(measured, self.threshold)
        trace.STEPS.event(
            "figure_condition",
            step=self.id,
            request=request.id,
            field=self.condition_field,
            operator=self.operator,
            value=measured,
            threshold=self.threshold,
            matches=matches,
        )
        return matches

    def _is_applicable_to_document(self, document) -> bool:
        self.check_singleton()
        if not self.subject_domain:
            return True
        if (
            not document
            or not self.subject_model_id
            or document._name != self.subject_model_id.model
        ):
            return False
        domain = self._parse_domain_or_warn()
        if domain is None:
            return False
        applies = bool(document.exists().filtered_domain(domain))
        trace.STEPS.event(
            "condition",
            step=self.id,
            document=document,
            applies=applies,
        )
        return applies


class ApprovalCategoryStepMember(models.Model):
    _name = "approval.category.step.member"
    _description = "Approval Step Member"
    _order = "step_id, sequence, id"
    _rec_name = "user_id"

    _step_user_uniq = models.Constraint(
        "unique(step_id, user_id)",
        "A user is a member of a step only once.",
    )

    step_id = fields.Many2one(
        comodel_name="approval.category.step",
        index=True,
        required=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(
        related="step_id.company_id",
        readonly=True,
    )
    sequence = fields.Integer(
        default=10,
        help="The member's place when the step's members decide in order.",
    )
    required = fields.Boolean(
        help="The step is not met without this member's approval, whatever its quorum."
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        index=True,
        required=True,
        ondelete="cascade",
    )
    date_end = fields.Date(
        string="Valid Until",
        help="Last day this user may approve the step. Empty means no end, so a "
        "delegation until a date is a membership with an end date.",
    )
    delegated_by_id = fields.Many2one(
        comodel_name="res.users",
        help="Who handed over the right, when this membership is a delegation.",
    )
