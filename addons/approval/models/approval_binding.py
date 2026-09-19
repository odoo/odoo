import annotationlib
import datetime
import inspect
import logging

from odoo import SUPERUSER_ID, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import ormcache

from . import approval_trace as trace

_logger = logging.getLogger(__name__)

AUTOMATION_CLAIMED_METHODS = frozenset(
    {
        "create",
        "write",
        "unlink",
        "_compute_field_value",
        "_onchange_methods__",
        "message_post",
    }
)

ORM_LIFECYCLE_ACTIONS = frozenset(
    {"action_archive", "action_unarchive", "toggle_active"}
)

ORIGIN_ATTR = "approval_binding_origin"
ENABLED_PARAM = "approval.binding_enabled"
REPLAY_CONTEXT_KEY = "approval_binding_replay"
INVOKE_CONTEXT_KEY = "approval_binding_invoking"
SYNC_CONTEXT_KEY = "approval_binding_syncing"
ADMITTED_CONTEXT_KEY = "approval_binding_admitted"
ENFORCEABLE_ACTION_TYPES = frozenset({"ir.actions.server", "ir.actions.report"})


class ApprovalBinding(models.Model):
    _name = "approval.binding"
    _inherit = ["mixin.approval.domain"]
    _description = "Approval Binding"
    _order = "model_name, method, sequence, id"

    name = fields.Char(
        compute="_compute_name",
        store=True,
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    model_id = fields.Many2one(
        comodel_name="ir.model",
        index=True,
        required=True,
        ondelete="cascade",
    )
    model_name = fields.Char(
        related="model_id.model",
        string="Model Name",
    )
    method = fields.Char(
        help="Method to gate. It is wrapped at registry load, so the gate "
        "holds for every caller, not only the user interface. A binding gates "
        "a method or an action, never both."
    )
    action_id = fields.Many2one(
        comodel_name="ir.actions.actions",
        index="btree_not_null",
        ondelete="cascade",
        help="Action to gate, instead of a method. A server action or a report is "
        "refused on the server; a window or client action only opens a view, so a "
        "binding on one is honoured by the client's check alone.",
    )
    is_enforced = fields.Boolean(
        compute="_compute_is_enforced",
        help="Whether the server itself refuses the operation. False for a window "
        "or client action: opening a view is nothing the server can intercept, so "
        "only the client's check stands in the way.",
    )
    category_id = fields.Many2one(
        comodel_name="approval.category",
        ondelete="cascade",
        help="Approval configuration consulted for this operation. Required "
        "for every mode but 'Observe'.",
    )
    subject_domain = fields.Char(
        string="Applies When",
        help="Domain on the gated model. Empty means every record.",
    )
    mode = fields.Selection(
        selection=[
            ("advise", "Observe"),
            ("block", "Block"),
            ("request", "Request"),
        ],
        default="advise",
        required=True,
        help="""What the binding does when it applies:

        • Observe: the operation runs. Every call is recorded, including
          whether the caller was elevated. This is how a gate is sized before
          it is switched on -- turning a gate straight to Block surfaces the
          flows that were quietly relying on not being gated, in production.
        • Block: the operation is refused unless an approved request covers
          the record. A document implementing mixin.approval asks through its
          own button; any other record is covered by an approved request that
          points at it in this binding's category.
        • Request: the call raises an approval instead of running. With Run On
          Approval, the operation then runs once the request is approved --
          exactly once, and as the person who called it; without it, approval
          only clears the gate for the next call.""",
    )
    sudo_policy = fields.Selection(
        selection=[
            ("enforce", "Applies to everyone"),
            ("superuser", "Superuser passes"),
            ("bypass", "Any elevated caller passes"),
        ],
        default="superuser",
        required=True,
        help="""Who the gate does NOT apply to.

        `sudo()` flips `su` and keeps `uid`, so "elevated" covers both the
        real superuser and an ordinary user who called through `sudo()`. Those
        are different risks and this is deliberately not one switch:

        • Applies to everyone: nothing passes. Correct for a gate that must
          hold against internal callers too.
        • Superuser passes: the default. Internal machinery keeps working, an
          ordinary user cannot self-elevate past the gate.
        • Any elevated caller passes: what `web_studio` does unconditionally.
          Every bypass is still recorded, which is the part it does not do.""",
    )

    approve_on_invoke = fields.Boolean(
        help="Request mode only. When somebody who may approve a pending step of "
        "this record calls the operation, the call records their approval -- the "
        "way a Studio approval button works -- and the operation runs if nothing "
        "is left to approve. Otherwise the remaining approvers are asked and the "
        "call waits."
    )
    run_on_approval = fields.Boolean(
        default=True,
        help="Request mode only. Run the operation, once and as the person who "
        "asked, when the request is approved. Off, approval only clears the gate "
        "and the operation runs when it is next called, which is how Studio "
        "approvals behave.",
    )
    observation_ids = fields.One2many(
        comodel_name="approval.observation",
        inverse_name="binding_id",
    )
    observation_count = fields.Count(
        count_of="observation_ids",
        string="Observations",
    )
    elevated_count = fields.Integer(compute="_compute_elevation_counts")
    self_elevated_count = fields.Integer(compute="_compute_elevation_counts")

    _model_method_domain_uniq = models.Constraint(
        "unique nulls not distinct (model_id, method, action_id, subject_domain)",
        "A binding already covers that model, operation and condition.",
    )

    @api.depends("model_id", "method", "action_id", "mode")
    def _compute_name(self) -> None:
        for binding in self:
            target = binding.method or binding.action_id.name or "?"
            binding.name = f"{binding.model_name or '?'}.{target} ({binding.mode})"

    @api.depends("method", "action_id", "action_id.type")
    def _compute_is_enforced(self) -> None:
        for binding in self:
            binding.is_enforced = bool(binding.method) or (
                binding.action_id.type in ENFORCEABLE_ACTION_TYPES
            )

    def _compute_elevation_counts(self) -> None:
        grouped = self.env["approval.observation"]._read_group(
            [("binding_id", "in", self.ids)],
            ["binding_id", "elevation"],
            ["__count"],
        )
        elevated = dict.fromkeys(self.ids, 0)
        self_elevated = dict.fromkeys(self.ids, 0)
        for binding, elevation, count in grouped:
            if elevation == "none":
                continue
            elevated[binding.id] = elevated.get(binding.id, 0) + count
            if elevation == "self_elevated":
                self_elevated[binding.id] = count
        for binding in self:
            binding.elevated_count = elevated.get(binding.id, 0)
            binding.self_elevated_count = self_elevated.get(binding.id, 0)
            trace.BINDING.event(
                "elevation_counts",
                binding=binding.id,
                elevated=binding.elevated_count,
                self_elevated=binding.self_elevated_count,
            )

    def _domain_source_field(self) -> str:
        return "subject_domain"

    # -- configuration-time validation ------------------------------------

    @api.constrains(
        "model_id",
        "method",
        "mode",
        "subject_domain",
        "category_id",
        "approve_on_invoke",
        "run_on_approval",
        "action_id",
    )
    def _check_binding(self) -> None:
        for binding in self:
            model = self.env.get(binding.model_id.model)
            if model is None:
                trace.REFUSAL.event(
                    "binding_model_not_in_registry",
                    binding=binding.id,
                    model=binding.model_id.model,
                )
                raise ValidationError(
                    self.env._(
                        "%(model)s is not in the registry.",
                        model=binding.model_id.model,
                    ),
                )
            if bool(binding.method) == bool(binding.action_id):
                trace.REFUSAL.event(
                    "binding_gates_none_or_both",
                    binding=binding.id,
                    method=binding.method or None,
                    action=binding.action_id.id or None,
                )
                raise ValidationError(
                    self.env._(
                        "%(name)s must gate exactly one thing: a method or an action.",
                        name=binding.name,
                    ),
                )
            if binding.method:
                binding._check_method_available(model)
            else:
                binding._check_action_available()
            if binding.subject_domain:
                binding._check_domain_against_model(model)
            if binding.mode != "advise" and not binding.category_id:
                trace.REFUSAL.event(
                    "binding_without_category", binding=binding.id, mode=binding.mode
                )
                raise ValidationError(
                    self.env._(
                        "%(name)s is in %(mode)s mode, so it needs an approval "
                        "category to consult.",
                        name=binding.name,
                        mode=binding.mode,
                    ),
                )
            if binding.approve_on_invoke and binding.mode != "request":
                trace.REFUSAL.event(
                    "approve_on_invoke_needs_request",
                    binding=binding.id,
                    mode=binding.mode,
                )
                raise ValidationError(
                    self.env._(
                        "%(name)s approves on invoke, which needs Request mode: "
                        "Block mode raises no request for the caller to approve.",
                        name=binding.name,
                    ),
                )
            if binding.mode == "request" and binding.run_on_approval:
                if binding.method:
                    binding._check_method_replayable(model)
                elif binding.action_id.type != "ir.actions.server":
                    trace.REFUSAL.event(
                        "only_a_server_action_replays",
                        binding=binding.id,
                        action=binding.action_id.id,
                        type=binding.action_id.type,
                    )
                    raise ValidationError(
                        self.env._(
                            "%(name)s would run its action again once approved, "
                            "but only a server action can be run again. Turn Run "
                            "On Approval off for this one.",
                            name=binding.name,
                        ),
                    )

    def _check_action_available(self) -> None:
        self.check_singleton()
        action_type = self.action_id.type
        if action_type == "ir.actions.server":
            action_model = (
                self.env["ir.actions.server"].sudo().browse(self.action_id.id).model_id
            )
            if action_model != self.model_id:
                trace.REFUSAL.event(
                    "action_runs_on_another_model",
                    binding=self.id,
                    action=self.action_id.id,
                    action_model=action_model.model,
                    model=self.model_id.model,
                )
                raise ValidationError(
                    self.env._(
                        "%(action)s runs on %(action_model)s, not on %(model)s.",
                        action=self.action_id.name,
                        action_model=action_model.model,
                        model=self.model_id.model,
                    ),
                )
        elif action_type == "ir.actions.report":
            report_model = (
                self.env["ir.actions.report"].sudo().browse(self.action_id.id).model
            )
            if report_model != self.model_id.model:
                trace.REFUSAL.event(
                    "report_prints_another_model",
                    binding=self.id,
                    action=self.action_id.id,
                    report_model=report_model,
                    model=self.model_id.model,
                )
                raise ValidationError(
                    self.env._(
                        "%(action)s prints %(report_model)s, not %(model)s.",
                        action=self.action_id.name,
                        report_model=report_model,
                        model=self.model_id.model,
                    ),
                )
            if self.mode == "request":
                trace.REFUSAL.event(
                    "report_cannot_wait", binding=self.id, action=self.action_id.id
                )
                raise ValidationError(
                    self.env._(
                        "%(action)s is a report, and a report cannot wait for an "
                        "approval: refusing to render rolls back the request that "
                        "would have asked for one. Use Block, and let the client "
                        "raise the request before printing.",
                        action=self.action_id.name,
                    ),
                )

    def _check_method_available(self, model) -> None:
        self.check_singleton()
        if self.method in AUTOMATION_CLAIMED_METHODS:
            trace.REFUSAL.event(
                "method_claimed_by_automation", binding=self.id, method=self.method
            )
            raise ValidationError(
                self.env._(
                    "%(method)s cannot be gated. `automation` removes that "
                    "method from every model in the registry when it "
                    "re-registers its own hooks, without checking who "
                    "installed it, so the gate would disappear silently "
                    "rather than fail.",
                    method=self.method,
                ),
            )
        if refusal := self._get_method_refusal(self.method):
            trace.REFUSAL.event(
                "method_is_orm_api", binding=self.id, method=self.method
            )
            raise ValidationError(refusal)
        if self.model_id.model == self._name:
            trace.REFUSAL.event("binding_gates_itself", binding=self.id)
            raise ValidationError(
                self.env._("A binding cannot gate the binding machinery."),
            )
        function = getattr(model, self.method, None)
        if function is None or not callable(function):
            trace.REFUSAL.event(
                "method_does_not_exist",
                binding=self.id,
                model=model._name,
                method=self.method,
            )
            raise ValidationError(
                self.env._(
                    "%(model)s has no method %(method)s.",
                    model=model._name,
                    method=self.method,
                ),
            )

    @api.model
    def _get_method_refusal(self, method: str) -> str | None:
        if method not in ORM_LIFECYCLE_ACTIONS and hasattr(models.BaseModel, method):
            return self.env._(
                "%(method)s is the ORM's own API, not an operation. Every caller of "
                "the model goes through it, the gate included, so wrapping it "
                "recurses or breaks the model. Gate the method that performs the "
                "business operation instead.",
                method=method,
            )
        return None

    @api.constrains("model_id", "method")
    def _check_private_method_from_module_data(self) -> None:
        if self.env.context.get("install_module"):
            return
        for binding in self:
            if binding.method and binding.method.startswith("_"):
                trace.REFUSAL.event(
                    "private_method_outside_module_data",
                    binding=binding.id,
                    method=binding.method,
                )
                raise ValidationError(
                    self.env._(
                        "%(method)s is private. A binding on a private method is "
                        "accepted only from a module's data, where it is reviewed "
                        "with the code that calls the method.",
                        method=binding.method,
                    ),
                )

    def _check_method_replayable(self, model) -> None:
        self.check_singleton()
        function = getattr(model, self.method)
        signature = inspect.signature(
            function, annotation_format=annotationlib.Format.FORWARDREF
        )
        required = [
            parameter
            for name, parameter in signature.parameters.items()
            if name != "self"
            and parameter.default is inspect.Parameter.empty
            and parameter.kind not in (parameter.VAR_POSITIONAL, parameter.VAR_KEYWORD)
        ]
        if required:
            trace.REFUSAL.event(
                "method_takes_arguments",
                binding=self.id,
                method=self.method,
                args=[parameter.name for parameter in required],
            )
            raise ValidationError(
                self.env._(
                    "%(method)s takes %(args)s, so it cannot be replayed after "
                    "approval. Request mode only gates methods that take no "
                    "argument; use Block mode for this one.",
                    method=self.method,
                    args=", ".join(p.name for p in required),
                ),
            )

    @api.model
    def _enabled(self) -> bool:
        return self.env["ir.config_parameter"].sudo().get_param(
            ENABLED_PARAM, "True"
        ).strip().lower() not in ("false", "0", "no")

    @api.model
    def _elevation(self) -> str:
        if not self.env.su:
            return "none"
        return "superuser" if self.env.uid == SUPERUSER_ID else "self_elevated"

    def _passes_on_elevation(self, elevation: str) -> bool:
        self.check_singleton()
        if elevation == "none":
            passes, rule = False, "not_elevated"
        elif self.sudo_policy == "enforce":
            passes, rule = False, "enforced"
        elif self.sudo_policy == "bypass":
            passes, rule = True, "bypass"
        else:
            passes, rule = elevation == "superuser", "superuser_only"
        trace.BINDING.event(
            "elevation",
            binding=self.id,
            elevation=elevation,
            policy=self.sudo_policy,
            rule=rule,
            passes=passes,
        )
        return passes

    def _has_anyone_to_ask(self) -> bool:
        self.check_singleton()
        category = self.category_id.sudo()
        anyone = bool(category.step_ids or category.rule_ids)
        if not anyone:
            trace.DEGRADED.event(
                "binding_has_nobody_to_ask",
                binding=self.id,
                category=category.id,
                mode=self.mode,
            )
        return anyone

    def _get_selected(self, records):
        self.check_singleton()
        if self.mode != "advise" and not self._has_anyone_to_ask():
            return records.browse()
        if self.subject_domain:
            domain = self._parse_domain_or_warn()
            if domain is None:
                return records.browse()
            records = records.filtered_domain(domain)
        steps = self.category_id.sudo().step_ids if self.mode != "advise" else ()
        if not steps:
            trace.BINDING.event("selected", binding=self.id, records=records)
            return records
        selected = records.filtered(
            lambda record: any(
                step._is_applicable_to_document(record) for step in steps
            )
        )
        trace.BINDING.event(
            "selected",
            binding=self.id,
            asked=records,
            records=selected.ids,
            steps=steps.ids,
        )
        return selected

    def _get_covered_ids(self, records) -> set[int]:
        self.check_singleton()
        if not records:
            return set()
        if "approval_request_id" in records._fields:
            return {
                record.id
                for record in records.sudo()
                if record.approval_request_id.state == "approved"
                and (
                    not self.category_id
                    or record.approval_request_id.category_id == self.category_id
                )
            }
        domain = [
            ("res_model", "=", records._name),
            ("res_id", "in", records.ids),
            ("state", "=", "approved"),
        ]
        if self.category_id:
            domain.append(("category_id", "=", self.category_id.id))
        by_id = {record.id: record for record in records}
        covered = set()
        for request in self.env["approval.request"].sudo().search(domain):
            record = by_id.get(request.res_id)
            if record is None or record.id in covered:
                continue
            if (
                request.binding_id == self
                and request.binding_snapshot
                and request.binding_snapshot != self._get_snapshot(record)
            ):
                continue
            covered.add(record.id)
        return covered

    def _get_snapshot(self, record) -> dict:
        self.check_singleton()
        if not self.subject_domain:
            return {}
        domain = self._parse_domain()
        if domain is None:
            _logger.warning(
                "Approval binding %s: subject_domain %r does not parse, so the "
                "snapshot taken for %s#%s is empty and no later change to it can "
                "move this approval's coverage.",
                self.id,
                self.subject_domain,
                record._name,
                record.id,
            )
            return {}
        probe = record.sudo()
        return {
            path: self._get_snapshot_value(probe.mapped(path))
            for path in sorted(self._domain_field_paths(domain))
        }

    @api.model
    def _get_snapshot_value(self, value):
        if isinstance(value, models.BaseModel):
            return sorted(value.ids)
        if isinstance(value, (list, tuple)):
            return [self._get_snapshot_value(item) for item in value]
        if isinstance(value, datetime.date):
            return value.isoformat()
        return value

    def _get_observation_vals(self, record, elevation: str, would_block: bool) -> dict:
        self.check_singleton()
        return {
            "binding_id": self.id,
            "model_name": record._name,
            "operation": self.method or self.action_id.name or "?",
            "res_id": record.id,
            "user_id": self.env.uid,
            "elevation": elevation,
            "would_block": would_block,
        }

    def _enforce(self, record, elevation: str, observations: list, covered_ids) -> bool:
        self.check_singleton()
        covered = record.id in covered_ids

        if self.mode == "advise" or self._passes_on_elevation(elevation):
            trace.BINDING.event(
                "observed",
                binding=self.id,
                record=record.id,
                mode=self.mode,
                elevation=elevation,
                would_block=not covered,
            )
            observations.append(
                self._get_observation_vals(record, elevation, not covered)
            )
            return False

        if covered:
            trace.BINDING.event(
                "covered", binding=self.id, record=record.id, mode=self.mode
            )
            return False

        if self.mode == "block":
            trace.REFUSAL.event(
                "blocked",
                binding=self.id,
                record=record.id,
                method=self.method,
                elevation=elevation,
            )
            raise UserError(
                self.env._(
                    "%(record)s needs an approval before %(method)s can run.\n\n"
                    "Ask for approval on the document first.",
                    record=record.display_name,
                    method=self.method,
                ),
            )
        trace.BINDING.note(
            "wants_request",
            binding=self.id,
            record=record.id,
            method=self.method,
            elevation=elevation,
        )
        return True

    def _raise_requests_for(self, records):
        self.check_singleton()
        Request = self.env["approval.request"]
        requests = Request
        if "approval_request_id" in records._fields:
            for record in records:
                request = record.sudo().approval_request_id
                if request.state == "refused":
                    requests |= request
                    continue
                if request.state not in ("new", "pending"):
                    record.with_context(
                        approval_binding_for=(record._name, record.id, self.id),
                    ).action_create_approval_request()
                    request = record.sudo().approval_request_id
                elif request.state == "new":
                    request.action_confirm()
                requests |= request
            return requests

        latest_by_res_id = {}
        for request in Request.search(
            [
                ("binding_id", "=", self.id),
                ("res_model", "=", records._name),
                ("res_id", "in", records.ids),
            ],
            order="id desc",
        ):
            latest_by_res_id.setdefault(request.res_id, request)
        for record in records:
            request = latest_by_res_id.get(record.id)
            if request and request.state == "refused":
                requests |= request
                continue
            if not request or request.state not in ("new", "pending"):
                request = Request.create(
                    {
                        "name": record.display_name,
                        "category_id": self.category_id.id,
                        "request_owner_id": self.env.uid,
                        "res_model": record._name,
                        "res_id": record.id,
                        "binding_id": self.id,
                        "binding_snapshot": self._get_snapshot(record),
                    }
                )
                request.action_confirm()
            elif request.state == "new":
                request.write({"binding_snapshot": self._get_snapshot(record)})
                request.action_confirm()
            requests |= request
        trace.BINDING.note(
            "requests_raised",
            binding=self.id,
            records=records,
            requests=requests.ids,
        )
        return requests

    def _approve_on_invoke(self, requests) -> None:
        self.check_singleton()
        user = self.env.user
        for request in requests.filtered(lambda r: r.state == "pending"):
            approver = request._get_rows_decidable_by(user)
            if not approver:
                trace.BINDING.event(
                    "invoke_not_decidable",
                    binding=self.id,
                    request=request.id,
                    uid=user.id,
                )
                continue
            try:
                with self.env.cr.savepoint():
                    request.with_user(user).with_context(
                        **{INVOKE_CONTEXT_KEY: True}
                    ).action_approve(approver)
            except UserError as exc:
                _logger.info(
                    "Approval binding %s: %s could not approve request %s on "
                    "invoke: %s",
                    self.id,
                    user.login,
                    request.id,
                    exc,
                )

    def _mark_invoked_run(self, records) -> None:
        self.check_singleton()
        if not records:
            return
        if "approval_request_id" in records._fields:
            requests = records.sudo().approval_request_id
        else:
            requests = (
                self.env["approval.request"]
                .sudo()
                .search(
                    [
                        ("binding_id", "=", self.id),
                        ("res_model", "=", records._name),
                        ("res_id", "in", records.ids),
                    ],
                )
            )
        consumed = requests.filtered(
            lambda r: (
                r.binding_id == self
                and r.state == "approved"
                and not r.date_binding_replayed
            ),
        )
        trace.BINDING.note(
            "invoke_consumed",
            binding=self.id,
            records=records,
            requests=consumed.ids,
            already_stamped=len(requests) - len(consumed),
        )
        consumed.write({"date_binding_replayed": fields.Datetime.now()})

    def _get_requests_action(self, requests):
        if not requests:
            return False
        action = {
            "type": "ir.actions.act_window",
            "res_model": "approval.request",
            "name": self.env._("Approval Required"),
        }
        if len(requests) == 1:
            action.update(view_mode="form", res_id=requests.id)
        else:
            action.update(view_mode="list,form", domain=[("id", "in", requests.ids)])
        return action

    def _replay(self, request) -> None:
        self.check_singleton()
        owner = request.request_owner_id
        record = self.env[request.res_model].browse(request.res_id).with_user(owner)
        if owner.id == SUPERUSER_ID:
            record = record.sudo()
        error = False
        try:
            with self.env.cr.savepoint():
                probe = record.sudo()
                if not probe.exists():
                    trace.REFUSAL.event(
                        "replay_record_gone",
                        binding=self.id,
                        model=request.res_model,
                        res_id=request.res_id,
                    )
                    raise UserError(self.env._("The record no longer exists."))
                if self._get_selected(probe) and probe.id not in self._get_covered_ids(
                    probe
                ):
                    trace.REFUSAL.event(
                        "replay_snapshot_moved",
                        binding=self.id,
                        request=request.id,
                        record=probe,
                    )
                    raise UserError(
                        self.env._(
                            "What was approved is no longer what is there: a "
                            "value this gate reads changed after the request was "
                            "raised. Ask for approval again."
                        )
                    )
                replaying = record.with_context(**{REPLAY_CONTEXT_KEY: request.id})
                if self.action_id:
                    self._run_action_on(replaying)
                else:
                    getattr(replaying, self.method)()
        except UserError as exc:
            error = str(exc) or type(exc).__name__
            trace.BINDING.note(
                "replay_failed",
                binding=self.id,
                request=request.id,
                method=self.method,
                error=type(exc).__name__,
            )
            _logger.info(
                "Approval binding %s: request %s approved, operation %s not run: %s",
                self.id,
                request.id,
                self.method,
                error,
            )

        if error:
            request.sudo().write({"binding_replay_error": error})
            body = self.env._(
                "The gated operation %(method)s did not run: %(error)s",
                method=self.method,
                error=error,
            )
        else:
            request.sudo().write(
                {
                    "date_binding_replayed": fields.Datetime.now(),
                    "binding_replay_error": False,
                }
            )
            trace.BINDING.note(
                "replay_ran",
                binding=self.id,
                request=request.id,
                method=self.method,
                owner=owner.id,
            )
            body = self.env._(
                "The gated operation %(method)s ran as %(user)s.",
                method=self.method,
                user=owner.display_name,
            )
        request.sudo().message_post(body=body, message_type="notification")

    @api.model
    def _bindings_for(self, model_name: str, method: str):
        return self.sudo().browse(self._get_binding_ids(model_name, method))

    @api.model
    @ormcache("model_name", "method")
    def _get_binding_ids(self, model_name: str, method: str) -> tuple[int, ...]:
        return tuple(
            self.sudo()
            .with_context(active_test=True)
            .search([("model_name", "=", model_name), ("method", "=", method)])
            .ids
        )

    @api.model
    def _bindings_for_action(self, action_id: int):
        return self.sudo().browse(self._get_action_binding_ids(action_id))

    @api.model
    @ormcache("action_id")
    def _get_action_binding_ids(self, action_id: int) -> tuple[int, ...]:
        """The bindings on one action, cached like the method lookup and for the same reason."""
        return tuple(
            self.sudo()
            .with_context(active_test=True)
            .search([("action_id", "=", action_id)])
            .ids
        )

    def _run_action_on(self, records):
        """Run this binding's server action on `records`, in their environment."""
        self.check_singleton()
        action = records.env["ir.actions.server"].browse(self.action_id.id)
        trace.BINDING.note(
            "run_action", binding=self.id, action=action.id, records=records
        )
        return action.with_context(
            active_model=records._name,
            active_ids=records.ids,
            active_id=records[:1].id,
        ).run()

    # -- keeping the registry in step with the configuration ---------------

    @api.model_create_multi
    def create(self, vals_list):
        bindings = super().create(vals_list)
        bindings._apply_to_registry()
        return bindings

    def write(self, vals):
        if {"model_id", "method", "action_id"} & vals.keys():
            self._check_target_unchanged_once_requested(vals)
        result = super().write(vals)
        self._apply_to_registry()
        return result

    def _check_target_unchanged_once_requested(self, vals) -> None:
        requested = (
            self.env["approval.request"]
            .sudo()
            .search([("binding_id", "in", self.ids)])
            .binding_id
        )
        for binding in requested:
            current = {
                "model_id": binding.model_id.id,
                "method": binding.method or False,
                "action_id": binding.action_id.id or False,
            }
            if any(
                field in vals and (vals[field] or False) != value
                for field, value in current.items()
            ):
                trace.REFUSAL.event(
                    "binding_target_frozen",
                    binding=binding.id,
                    fields=sorted(set(vals) & set(current)),
                )
                raise UserError(
                    self.env._(
                        "%(binding)s already has approval requests, so what it gates "
                        "cannot change. Archive it and bind the new target instead.",
                        binding=binding.name,
                    ),
                )

    def unlink(self):
        result = super().unlink()
        self.env.registry.clear_cache()
        return result

    def _get_requests_holding_decisions(self, records):
        """The requests a reset clears: approved ones, and waiting ones already decided in part."""
        self.check_singleton()
        waiting = (
            self.env["approval.request"]
            .sudo()
            .search(
                [
                    ("binding_id", "=", self.id),
                    ("res_model", "=", records._name),
                    ("res_id", "in", records.ids),
                    ("state", "=", "pending"),
                ]
            )
            .filtered(
                lambda request: request.approver_ids.filtered(
                    lambda approver: approver.decided_by_user_id
                )
            )
        )
        covering = self._get_covering_requests(records)
        trace.BINDING.event(
            "requests_holding_decisions",
            binding=self.id,
            records=records,
            covering=covering.ids,
            waiting_with_decisions=waiting.ids,
        )
        return covering | waiting

    def _get_covering_requests(self, records):
        """Every approved request that could be covering these records."""
        self.check_singleton()
        Request = self.env["approval.request"].sudo()
        if "approval_request_id" in records._fields:
            requests = records.sudo().approval_request_id
        else:
            requests = Request.search(
                [
                    ("res_model", "=", records._name),
                    ("res_id", "in", records.ids),
                    ("state", "=", "approved"),
                ]
            )
        return requests.filtered(
            lambda r: (
                r.state == "approved"
                and (not self.category_id or r.category_id == self.category_id)
            )
        )

    def _reset_coverage(self, records) -> None:
        """Reset to draft the approvals that covered these records.

        Through `action_reset_to_draft`, the framework's own lifecycle, so an
        adopter is told through `_on_approval_reset` and the decisions stay in the
        request's chatter. The one-shot stamp is cleared, so a binding that runs on
        approval runs again in the next cycle.
        """
        self.check_singleton()
        holding = self._get_requests_holding_decisions(records)
        trace.BINDING.note(
            "reset_coverage",
            binding=self.id,
            records=records,
            requests=holding.ids,
        )
        for request in holding:
            try:
                with self.env.cr.savepoint():
                    if request.state == "approved":
                        request.action_reset_to_draft()
                    else:
                        request._lock_and_reload(with_approvers=True)
                        if request.state != "pending":
                            continue
                        request._force_draft()
                    request.write(
                        {"date_binding_replayed": False, "binding_replay_error": False}
                    )
            except UserError as exc:
                _logger.info(
                    "Approval binding %s: request %s was not reset: %s",
                    self.id,
                    request.id,
                    exc,
                )
                continue
            request.message_post(
                body=self.env._(
                    "%(record)s came to match the reset condition of %(binding)s, so "
                    "this approval no longer covers it and was reset to draft.",
                    record=request.res_name or request.display_name,
                    binding=self.name,
                ),
                message_type="notification",
            )

    def _apply_to_registry(self) -> None:
        self.env.registry.clear_cache()
        unwrapped = False
        for binding in self:
            if not binding.method:
                continue
            ModelClass = self.env.registry.get(binding.model_name)
            if ModelClass is None:
                continue
            method = getattr(ModelClass, binding.method, None)
            if method is not None and getattr(method, ORIGIN_ATTR, None) is None:
                unwrapped = True
        if unwrapped:
            self._register_hook()
            self.env.registry.registry_invalidated = True

    # -- registry patching -------------------------------------------------

    def _register_hook(self):
        super()._register_hook()
        pairs = {}
        for binding in self.sudo().with_context(active_test=True).search([]):
            model = self.env.get(binding.model_name)
            if model is None:
                _logger.warning(
                    "Approval binding %s names model %s, which is not in this "
                    "registry; skipped.",
                    binding.id,
                    binding.model_name,
                )
                continue
            if not binding.method or binding.method in AUTOMATION_CLAIMED_METHODS:
                continue
            if refusal := self._get_method_refusal(binding.method):
                trace.REGISTRY.note(
                    "binding_not_applied",
                    binding=binding.id,
                    model=binding.model_name,
                    method=binding.method,
                    refusal=refusal,
                )
                _logger.warning(
                    "Approval binding %s is not applied: %s", binding.id, refusal
                )
                continue
            pairs.setdefault(binding.model_name, set()).add(binding.method)

        trace.REGISTRY.note(
            "bindings_wrapped",
            models=len(pairs),
            methods=sum(len(methods) for methods in pairs.values()),
        )
        for model_name, methods in pairs.items():
            ModelClass = self.env.registry[model_name]
            for method_name in methods:
                origin = getattr(ModelClass, method_name, None)
                if origin is None or getattr(origin, ORIGIN_ATTR, None) is not None:
                    continue
                guarded = self._get_guarded_method(model_name, method_name)
                setattr(guarded, ORIGIN_ATTR, origin)
                setattr(ModelClass, method_name, guarded)
            checkpoints = getattr(ModelClass, "_operation_checkpoints", {})
            for checkpoint in {checkpoints[m] for m in methods if m in checkpoints}:
                origin = getattr(ModelClass, checkpoint, None)
                if origin is None or getattr(origin, ORIGIN_ATTR, None) is not None:
                    continue
                operations = tuple(
                    sorted(m for m, c in checkpoints.items() if c == checkpoint)
                )
                guarded = self._get_checkpoint_guard(model_name, checkpoint, operations)
                setattr(guarded, ORIGIN_ATTR, origin)
                setattr(ModelClass, checkpoint, guarded)

    def _unregister_hook(self):
        """Remove only our own wrappers, identified by the marker we set."""
        for ModelClass in self.env.registry.values():
            for name, function in list(vars(ModelClass).items()):
                if getattr(function, ORIGIN_ATTR, None) is not None:
                    setattr(ModelClass, name, getattr(function, ORIGIN_ATTR))

    @api.model
    def _gate(self, records, bindings, label: str, call):
        elevation = self._elevation()
        observations = []
        wanting = {}
        for binding in bindings:
            selected = binding._get_selected(records)
            if not selected:
                continue
            covered_ids = binding._get_covered_ids(selected)
            for record in selected:
                if binding._enforce(record, elevation, observations, covered_ids):
                    wanting[binding] = wanting.get(binding, records.browse()) | record

        if observations:
            records.env["approval.observation"].sudo().create(observations)
        if not wanting:
            return call(records)
        if records.env.context.get(REPLAY_CONTEXT_KEY):
            trace.REFUSAL.event(
                "replay_uncovered",
                method=label,
                records=records,
            )
            raise UserError(
                records.env._(
                    "%(method)s still needs an approval that does not cover "
                    "this record, so it was not run again.",
                    method=label,
                ),
            )
        waiting = records.browse()
        shown = records.env["approval.request"]
        for binding, pending in wanting.items():
            requests = binding._raise_requests_for(pending)
            if binding.approve_on_invoke:
                binding._approve_on_invoke(requests)
            covered_ids = binding._get_covered_ids(pending)
            still = pending.filtered(
                lambda record, ids=covered_ids: record.id not in ids,
            )
            if still:
                waiting |= still
                shown |= requests
        runnable = records - waiting
        trace.BINDING.note(
            "gate",
            method=label,
            records=records,
            wanting=[binding.id for binding in wanting],
            waiting=waiting.ids,
            runnable=runnable.ids,
            shown=shown.ids,
        )
        result = False
        if runnable:
            result = call(runnable)
            for binding, pending in wanting.items():
                binding._mark_invoked_run(pending & runnable)
        if waiting:
            return self._get_requests_action(shown)
        return result

    def _get_guarded_method(self, model_name: str, method_name: str):
        def guarded(records, *args, **kwargs):
            origin = getattr(guarded, ORIGIN_ATTR)
            Binding = records.env["approval.binding"]
            if not Binding._enabled():
                trace.BINDING.event(
                    "guard_skipped",
                    model=model_name,
                    method=method_name,
                    records=records.ids,
                    reason="kill_switch",
                )
                return origin(records, *args, **kwargs)

            bindings = Binding._bindings_for(model_name, method_name)
            if not bindings:
                trace.BINDING.event(
                    "guard_skipped",
                    model=model_name,
                    method=method_name,
                    records=records.ids,
                    reason="no_binding",
                )
                return origin(records, *args, **kwargs)
            trace.BINDING.event(
                "guard_entered",
                model=model_name,
                method=method_name,
                records=records.ids,
                bindings=bindings.ids,
            )

            return Binding._gate(
                records,
                bindings,
                method_name,
                lambda runnable: origin(
                    Binding._admit(runnable, method_name), *args, **kwargs
                ),
            )

        guarded.__name__ = method_name
        guarded.__qualname__ = f"{model_name}.{method_name}"
        return guarded

    @api.model
    def _admit(self, records, operation: str):
        """Mark these records as let through `operation`'s own wrapper.

        The ids are part of the mark: an operation that posts other records inside
        the admitted call leaves those records to be checked on their own.
        """
        admitted = records.env.context.get(ADMITTED_CONTEXT_KEY, ())
        return records.with_context(
            **{
                ADMITTED_CONTEXT_KEY: (
                    *admitted,
                    (records._name, operation, tuple(records.ids)),
                )
            }
        )

    @api.model
    def _get_admitted_ids(self, records, operation: str) -> set[int]:
        return {
            record_id
            for model_name, admitted_operation, ids in records.env.context.get(
                ADMITTED_CONTEXT_KEY, ()
            )
            if model_name == records._name and admitted_operation == operation
            for record_id in ids
        }

    def _get_checkpoint_guard(
        self, model_name: str, checkpoint: str, operations: tuple[str, ...]
    ):
        def guarded(records, *args, **kwargs):
            origin = getattr(guarded, ORIGIN_ATTR)
            Binding = records.env["approval.binding"]
            if not records:
                return origin(records, *args, **kwargs)
            if not Binding._enabled():
                trace.BINDING.event(
                    "checkpoint_disabled",
                    checkpoint=checkpoint,
                    model=model_name,
                    records=len(records),
                )
                return origin(records, *args, **kwargs)
            for operation in operations:
                bindings = Binding._bindings_for(model_name, operation)
                trace.BINDING.event(
                    "checkpoint",
                    checkpoint=checkpoint,
                    model=model_name,
                    operation=operation,
                    records=len(records),
                    bindings=bindings.ids,
                )
                if bindings:
                    Binding._enforce_at_checkpoint(records, bindings, operation)
            return origin(records, *args, **kwargs)

        guarded.__name__ = checkpoint
        guarded.__qualname__ = f"{model_name}.{checkpoint}"
        return guarded

    @api.model
    def _enforce_at_checkpoint(self, records, bindings, operation: str) -> None:
        """Hold `operation`'s bindings on a path that reaches its checkpoint.

        A checkpoint can neither ask for an approval nor keep a request it raised,
        so a record Block or Request mode would stop is refused here.
        """
        admitted = self._get_admitted_ids(records, operation)
        pending = records.filtered(lambda record: record.id not in admitted)
        trace.BINDING.event(
            "checkpoint",
            operation=operation,
            records=records,
            admitted=sorted(admitted),
            checked=pending.ids,
        )
        if not pending:
            return
        elevation = self._elevation()
        observations = []
        refused = pending.browse()
        for binding in bindings:
            selected = binding._get_selected(pending)
            if not selected:
                continue
            covered_ids = binding._get_covered_ids(selected)
            for record in selected:
                if binding._enforce(record, elevation, observations, covered_ids):
                    refused |= record
        if observations:
            records.env["approval.observation"].sudo().create(observations)
        if refused:
            trace.REFUSAL.event(
                "checkpoint_blocked",
                operation=operation,
                records=refused,
                bindings=bindings.ids,
            )
            raise UserError(
                self.env._(
                    "%(records)s need an approval before %(operation)s can run, and "
                    "this way of running it cannot ask for one. Use %(operation)s "
                    "itself, which raises the request.",
                    records=", ".join(refused.mapped("display_name")),
                    operation=operation,
                ),
            )
