import logging
from dataclasses import dataclass, field
from typing import Any

from odoo import api, models
from odoo.fields import Command

from . import approval_trace as trace

_logger = logging.getLogger(__name__)


@dataclass
class DesiredApprovers:
    staging: dict[int, dict]
    existing_by_user: dict[int, Any]
    duplicates: list[Any]
    matched_rules: Any
    superseded_delegations: Any
    to_create: dict[int, dict] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.to_create = {
            user_id: vals
            for user_id, vals in self.staging.items()
            if user_id not in self.existing_by_user
        }


class ApprovalRequestRouting(models.Model):
    _inherit = "approval.request"

    def _prepare_category_snapshot(self) -> dict[str, Any]:
        self.check_singleton()
        cat = self.category_id
        document = self.get_source_document()
        snapshot: dict[str, Any] = {
            "category_name": cat.name,
            "approval_minimum": cat.approval_minimum,
            "approval_type": cat.approval_type,
            "allow_self_approval": cat.allow_self_approval,
            "approval_deadline_hours": cat.approval_deadline_hours,
            "sla_target_hours": cat.sla_target_hours,
            "sla_warning_pct": cat.sla_warning_pct,
            "rules": [
                {
                    "name": r.name,
                    "condition_field": r.condition_field,
                    "operator": r.operator,
                    "threshold": r.threshold,
                    "action_type": r.action_type,
                }
                for r in cat.rule_ids.filtered("active")
            ],
            "steps": [
                {
                    "name": step.name,
                    "sequence": step.sequence,
                    "minimum": step.minimum,
                    "exclusive": step.exclusive,
                    "group": step.group_id.name or False,
                    "members": sorted(
                        step._get_pool_user_ids(document, self.company_id, self)
                    ),
                    "condition": step.subject_domain or False,
                    "source_user_path": step.subject_user_path or False,
                }
                for step in self._get_applicable_steps()
            ],
            "effective_approval_minimum": self.approval_minimum,
            "effective_approvers": [
                {
                    "user_id": a.user_id.id,
                    "user_name": a.user_id.name,
                    "required": a.required,
                    "sequence": a.sequence,
                }
                for a in self.approver_ids
            ],
        }
        trace.SNAPSHOT.event(
            "prepared",
            request=self.id,
            category=cat.id,
            rules=len(snapshot["rules"]),
            steps=len(snapshot["steps"]),
            effective=len(snapshot["effective_approvers"]),
            minimum=snapshot["effective_approval_minimum"],
        )
        return snapshot

    def _get_applicable_steps(self):
        """The category's steps whose condition this request meets, in order."""
        self.check_singleton()
        steps = self.category_id.step_ids
        matched = self._get_step_rule_matches(
            steps.when_rule_ids | steps.unless_rule_ids
        )
        applicable = steps.filtered(
            lambda step: step._is_applicable_to_request(self, matched),
        ).sorted(lambda step: (step.sequence, step.id))
        trace.STEPS.event(
            "applicable",
            request=self.id,
            declared=len(self.category_id.step_ids),
            applicable=applicable.ids,
        )
        return applicable

    def _get_step_rule_matches(self, rules):
        self.check_singleton()
        remembered = self.env.context.get("approval_rule_matches", {}).get(self.id)
        if remembered is not None:
            return rules & rules.browse(remembered)
        matched = rules.sudo().filtered(
            lambda rule: self._rule_applies_to_company(rule) and rule._evaluate(self)
        )
        return matched.with_env(rules.env)

    def _applied_rule_ids_after_sync(self, matched_rules):
        self.check_singleton()
        preserved = self.applied_rule_ids.filtered(
            lambda r: r.action_type != "condition",
        )
        kept = preserved | matched_rules
        trace.RULES.event(
            "applied_rules_after_sync",
            request=self.id,
            was=self.applied_rule_ids.ids,
            preserved=preserved.ids,
            matched=matched_rules.ids,
            dropped=(self.applied_rule_ids - kept).ids,
        )
        return kept

    def _get_managed_approver_user_ids(self, steps) -> set[int]:
        self.check_singleton()
        managed = set()
        document = self.get_source_document()
        for step in steps:
            managed.update(step._get_candidate_user_ids(document, self))
        trace.ROUTING.event("managed_users", request=self.id, managed=sorted(managed))
        return managed

    def _rule_applies_to_company(self, rule) -> bool:
        self.check_singleton()
        rule_company = rule.company_id
        applies = not rule_company or rule_company == self.company_id
        if not applies:
            trace.RULES.event(
                "rule_other_company",
                request=self.id,
                rule=rule.id,
                rule_company=rule_company.id,
                company=self.company_id.id,
            )
        return applies

    def _check_auto_action_rules(self) -> bool:
        self.check_singleton()
        rules = self.category_id.rule_ids.filtered(
            lambda r: (
                r.active
                and r.action_type in ("auto_approve", "auto_refuse")
                and self._rule_applies_to_company(r)
            ),
        )
        matching = rules.filtered(lambda r: r._evaluate(self))
        trace.RULES.event(
            "auto_action_rules",
            request=self.id,
            candidates=rules.ids,
            matched=matching.ids,
        )
        if not matching:
            return False
        rule = self._resolve_auto_action(matching)
        if rule:
            trace.RULES.note(
                "auto_action_applied",
                request=self.id,
                rule=rule.id,
                action=rule.action_type,
            )
            if rule.action_type == "auto_approve":
                self.approver_ids.sudo()._approve_for_every_step(
                    note=self.env._("Approved by rule %(rule)s.", rule=rule.name)
                )
                self.message_post(
                    body=self.env._(
                        "Auto-approved by rule: %(rule)s "
                        "(%(field)s %(op)s %(threshold)s)",
                        rule=rule.name,
                        field=rule.condition_field,
                        op=rule.operator,
                        threshold=rule.threshold,
                    ),
                    message_type="notification",
                )
                self.applied_rule_ids |= rule
                return True

            if rule.action_type == "auto_refuse":
                self._flip_unsettled_approvers("refused")
                self._stamp_refusal_metadata(
                    self.env.ref("approval.refusal_reason_auto_rule"),
                    self.env._(
                        "Automatically refused by rule '%(rule)s'.",
                        rule=rule.name,
                    ),
                )
                self._cancel_activities()
                self.message_post(
                    body=self.env._(
                        "Auto-refused by rule: %(rule)s "
                        "(%(field)s %(op)s %(threshold)s)",
                        rule=rule.name,
                        field=rule.condition_field,
                        op=rule.operator,
                        threshold=rule.threshold,
                    ),
                    message_type="notification",
                )
                self.applied_rule_ids |= rule
                if self.state == "refused":
                    self._refuse_approval_request()
                return True

        return False

    def _resolve_auto_action(self, matching_rules):
        refusals = matching_rules.filtered(
            lambda r: r.action_type == "auto_refuse",
        )
        candidates = refusals or matching_rules
        chosen = candidates.sorted(lambda r: (r.sequence, r.id))[:1]
        trace.RULES.event(
            "auto_action_resolved",
            matching=matching_rules.ids,
            refusals=refusals.ids,
            preempted=(candidates - chosen).ids,
            chosen=chosen.id or None,
        )
        return chosen

    def _get_sequence_param(self, kind: str, default: int) -> int:
        raw = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(f"approval.sequence.{kind}", default)
        )
        try:
            return int(raw)
        except TypeError, ValueError:
            _logger.warning(
                "Ignoring invalid approval.sequence.%s = %r; using %d.",
                kind,
                raw,
                default,
            )
            return default

    def _get_sequence_manager(self) -> int:
        return self._get_sequence_param("manager", 9)

    def _merge_approver_to_staging(
        self,
        staging: dict[int, dict],
        user_id: int,
        required: bool,
        sequence: int,
    ) -> None:
        if user_id in staging:
            trace.ROUTING.event(
                "staging_merge",
                user=user_id,
                required=staging[user_id]["required"] or required,
                was_required=staging[user_id]["required"],
                sequence=min(staging[user_id]["sequence"], sequence),
                was_sequence=staging[user_id]["sequence"],
            )
            staging[user_id]["required"] |= required
            staging[user_id]["sequence"] = min(staging[user_id]["sequence"], sequence)
            staging[user_id]["source_synced"] = True
        else:
            staging[user_id] = {
                "required": required,
                "sequence": sequence,
                "flow_state": "new",
                "source_synced": True,
            }

    def _sync_approvers(self) -> None:
        self = self.filtered(lambda r: r.state == "new")
        if not self:
            return
        minimum_updates: dict[int, int] = {}
        rows_to_delete: list[int] = []
        rows_to_create: list[dict[str, Any]] = []
        rows_to_update: dict[tuple, list[int]] = {}

        self.category_id.fetch(["step_ids"])

        for request in self:
            step_rules = request.category_id.step_ids.when_rule_ids | (
                request.category_id.step_ids.unless_rule_ids
            )
            request = request.with_context(
                approval_rule_matches={
                    **request.env.context.get("approval_rule_matches", {}),
                    request.id: request._get_step_rule_matches(step_rules).ids,
                }
            )
            desired = request._get_desired_approvers()
            approver_staging = desired.staging
            users_to_approver = desired.existing_by_user

            if desired.superseded_delegations:
                request._retire_superseded_delegations(desired.superseded_delegations)

            desired_applied = request._applied_rule_ids_after_sync(
                desired.matched_rules
            )
            if desired_applied != request.applied_rule_ids:
                request.applied_rule_ids = desired_applied

            rows_to_delete.extend(
                dup_approver.id for dup_approver in desired.duplicates
            )

            for user_id, vals in approver_staging.items():
                if user_id not in users_to_approver:
                    rows_to_create.append(
                        {
                            "request_id": request.id,
                            "user_id": user_id,
                            "flow_state": vals["flow_state"],
                            "required": vals["required"],
                            "sequence": vals["sequence"],
                            "source_rule_id": vals.get("source_rule_id"),
                            "source_synced": vals.get("source_synced", True),
                            "step_ids": [Command.set(list(vals.get("step_ids", ())))],
                        },
                    )
                else:
                    existing_approver = users_to_approver.pop(user_id)
                    self._stage_approver_update(
                        existing_approver,
                        rows_to_update,
                        vals["required"],
                        vals["sequence"],
                        vals.get("source_rule_id"),
                        vals.get("source_synced", True),
                        vals.get("step_ids", ()),
                    )

            rows_to_delete.extend(
                current_approver.id for current_approver in users_to_approver.values()
            )

            applicable_steps = request._get_applicable_steps()
            if applicable_steps:
                effective_minimum = sum(applicable_steps.mapped("minimum"))
            else:
                effective_minimum = request.category_id.approval_minimum
            trace.ROUTING.event(
                "desired",
                request=request.id,
                staged=len(approver_staging),
                existing=len(desired.existing_by_user),
                duplicates=len(desired.duplicates),
                rules=desired.matched_rules.ids,
                steps=applicable_steps.ids,
                minimum=effective_minimum,
                was_minimum=request.approval_minimum,
            )
            if request.approval_minimum != effective_minimum:
                minimum_updates[request.id] = effective_minimum

        plan = self._prepare_sync_plan(rows_to_delete, rows_to_create, rows_to_update)
        updates = sum(len(ids) for ids in rows_to_update.values())
        trace.annotate(work=len(rows_to_delete) + len(rows_to_create) + updates)
        trace.ROUTING.event(
            "sync_plan",
            requests=self.ids,
            delete=len(rows_to_delete),
            create=len(rows_to_create),
            update=updates,
            minimums=len(minimum_updates),
        )
        if _logger.isEnabledFor(logging.DEBUG):
            self._log_sync_plan(plan)
        self._execute_sync_plan(plan)

        if minimum_updates:
            by_minimum: dict[int, list[int]] = {}
            for rid, minimum in minimum_updates.items():
                by_minimum.setdefault(minimum, []).append(rid)
            for minimum, ids in by_minimum.items():
                self.browse(ids).sudo().write({"approval_minimum": minimum})

    def _extend_approvers_live(self) -> models.BaseModel:
        live = self.filtered(
            lambda r: r.state == "pending" and not r.pending_change_field,
        )
        if not live:
            return self.env["approval.approver"]

        live.category_id.fetch(["step_ids"])

        added = self.env["approval.approver"]
        for request in live:
            request._lock_and_reload()
            if request.state != "pending" or request.pending_change_field:
                continue
            added |= request._reroute_steps_live(request._get_desired_approvers())
        return added

    def _reroute_steps_live(self, desired) -> models.BaseModel:
        self.check_singleton()
        Step = self.env["approval.category.step"]
        previous = self.approver_ids.step_ids
        current = self._get_applicable_steps()
        arrived = current - previous
        departed = previous - current
        trace.STEPS.event(
            "steps_rerouted_live",
            request=self.id,
            arrived=arrived.ids,
            departed=departed.ids,
        )
        if not arrived and not departed:
            return self.env["approval.approver"]
        for row in self.approver_ids:
            vals = desired.staging.get(row.user_id.id)
            staged = Step.browse(vals["step_ids"]) if vals else Step
            steps = (row.step_ids & current) | (staged & arrived)
            decided = row.decided_step_ids & current
            if row.state == "approved" and not decided and row.decided_step_ids:
                decided = staged & arrived
            row.sudo().write(
                {
                    "step_ids": [Command.set(steps.ids)],
                    "decided_step_ids": [Command.set(decided.ids)],
                }
            )
        missing = {
            user_id: vals
            for user_id, vals in desired.to_create.items()
            if set(vals["step_ids"]) & set(arrived.ids)
        }
        created = self._create_live_approver_rows(missing)
        for row in created:
            row.write({"step_ids": [Command.set(missing[row.user_id.id]["step_ids"])]})
        self.sudo().write(
            {
                "approval_minimum": sum(current.mapped("minimum")),
                "applied_rule_ids": [
                    Command.link(rule.id) for rule in current.when_rule_ids
                ],
            }
        )
        self.invalidate_recordset()
        self._refresh_turn_states()
        self.approver_ids.filtered(
            lambda row: row.state == "pending"
        )._create_activity()
        self._retire_unasked_approval_activities()
        if created:
            self.message_post(
                body=self.env._(
                    "Approver(s) added because the request changed: %(names)s.\n\n"
                    "The steps of category '%(category)s' now ask for them. "
                    "Approvals already given stand.",
                    names=", ".join(sorted(created.user_id.mapped("name"))),
                    category=self.category_id.name,
                ),
                message_type="notification",
            )
            self._log_cycle("reroute", added=len(created))
        return created

    def _create_live_approver_rows(self, missing: dict[int, dict]):
        self.check_singleton()
        rows = [
            {
                "request_id": self.id,
                "user_id": user_id,
                "flow_state": "pending",
                "required": vals["required"],
                "sequence": vals["sequence"],
                "source_rule_id": vals.get("source_rule_id"),
                "source_synced": vals.get("source_synced", True),
            }
            for user_id, vals in sorted(
                missing.items(),
                key=lambda item: (item[1]["sequence"], item[0]),
            )
        ]
        trace.annotate(work=len(rows))
        trace.ROUTING.note("live_rows", request=self.id, users=sorted(missing))
        return (
            self.env["approval.approver"]
            .sudo()
            .with_context(approver_ids_computation=True)
            .create(rows)
        )

    _SYNC_LOG_PREFIX = "approver-sync"

    def _prepare_sync_plan(
        self,
        rows_to_delete: list[int],
        rows_to_create: list[dict[str, Any]],
        rows_to_update: dict[tuple, list[int]],
    ) -> list[tuple]:
        plan: list[tuple] = []
        if rows_to_delete:
            plan.append(("delete", rows_to_delete))
        if rows_to_create:
            plan.append(("create", rows_to_create))
        for update_vals, approver_ids in rows_to_update.items():
            plan.append(("update", (update_vals, approver_ids)))
        return plan

    def _execute_sync_plan(self, plan: list[tuple]) -> None:
        if not plan:
            return
        approver_model = (
            self.env["approval.approver"]
            .sudo()
            .with_context(approver_ids_computation=True)
        )
        for kind, payload in plan:
            if kind == "delete":
                approver_model.browse(payload).unlink()
            elif kind == "create":
                approver_model.create(payload)
            else:
                update_vals, approver_ids = payload
                vals = dict(update_vals)
                if "step_ids" in vals:
                    vals["step_ids"] = [Command.set(list(vals["step_ids"]))]
                approver_model.browse(approver_ids).write(vals)

    def _log_sync_plan(self, plan: list[tuple]) -> None:
        _logger.debug(
            "%s batch: %d request(s) %s",
            self._SYNC_LOG_PREFIX,
            len(self),
            self.ids,
        )
        for step, (kind, payload) in enumerate(plan, start=1):
            if kind == "delete":
                _logger.debug(
                    "%s   %d. delete %d row(s): %s",
                    self._SYNC_LOG_PREFIX,
                    step,
                    len(payload),
                    sorted(payload),
                )
            elif kind == "create":
                _logger.debug(
                    "%s   %d. create %d row(s)",
                    self._SYNC_LOG_PREFIX,
                    step,
                    len(payload),
                )
                for vals in payload:
                    _logger.debug(
                        "%s        req %s -> user %s (seq %s, %s%s)",
                        self._SYNC_LOG_PREFIX,
                        vals["request_id"],
                        vals["user_id"],
                        vals["sequence"],
                        "required" if vals["required"] else "optional",
                        f", rule {vals['source_rule_id']}"
                        if vals.get("source_rule_id")
                        else "",
                    )
            else:
                update_vals, approver_ids = payload
                _logger.debug(
                    "%s   %d. update %d row(s) %s -> %s",
                    self._SYNC_LOG_PREFIX,
                    step,
                    len(approver_ids),
                    sorted(approver_ids),
                    " ".join(f"{key}={value}" for key, value in update_vals),
                )

    def _retire_superseded_delegations(self, rows) -> None:
        self.check_singleton()
        for row in rows:
            delegate = row.delegate_id
            trace.DELEGATION.note(
                "superseded",
                request=self.id,
                approver=row.id,
                principal=row.user_id.id,
                delegate=delegate.id,
            )
            row.sudo().write(
                {
                    "delegate_id": False,
                    "delegate_start_date": False,
                    "delegate_end_date": False,
                },
            )
            self.message_post(
                body=self.env._(
                    "%(principal)s's delegation to %(delegate)s was ended: "
                    "%(delegate)s is now an approver of this request in "
                    "their own right, and one person cannot hold two "
                    "approvals.",
                    principal=row.user_id.name,
                    delegate=delegate.name,
                ),
                message_type="notification",
            )

    def _get_desired_approvers(self) -> DesiredApprovers:
        self.check_singleton()
        users_to_approver: dict[int, Any] = {}
        duplicate_approvers_to_delete: list[Any] = []
        for approver in self.approver_ids:
            user_id = approver.user_id.id
            if user_id in users_to_approver:
                duplicate_approvers_to_delete.append(approver)
            else:
                users_to_approver[user_id] = approver

        approver_staging: dict[int, dict] = {}

        steps = self._get_applicable_steps()
        step_ids_by_user: dict[int, set[int]] = {}
        document = self.get_source_document()
        for step in steps:
            member_order = {
                member.user_id.id: (member.sequence, member.id)
                for member in step.member_ids
            }
            required = set(step.member_ids.filtered("required").user_id.ids)
            named = step.sudo()._get_source_user_ids(document, self)
            if step.subject_user_required:
                required |= named
            pool = step._get_pool_user_ids(document, self.company_id, self)
            for user_id in sorted(
                pool,
                key=lambda user_id, order=member_order: (
                    user_id not in order,
                    order.get(user_id, (0, 0)),
                    user_id,
                ),
            ):
                if user_id in member_order:
                    sequence = member_order[user_id][0]
                elif user_id in named and step.in_order:
                    sequence = step.subject_user_sequence
                else:
                    sequence = step.sequence
                self._merge_approver_to_staging(
                    approver_staging, user_id, user_id in required, sequence
                )
                step_ids_by_user.setdefault(user_id, set()).add(step.id)
        for user_id, vals in approver_staging.items():
            vals["source_rule_id"] = None
            vals["step_ids"] = tuple(sorted(step_ids_by_user.get(user_id, ())))

        managed_user_ids = self._get_managed_approver_user_ids(steps)
        for user_id, existing_approver in users_to_approver.items():
            if user_id in approver_staging:
                continue
            is_injected_orphan = (
                existing_approver.source_synced
                or existing_approver.source_rule_id
                or user_id in managed_user_ids
            )
            if not is_injected_orphan:
                approver_staging[user_id] = {
                    "flow_state": existing_approver.flow_state,
                    "required": existing_approver.required,
                    "sequence": existing_approver.sequence,
                    "source_rule_id": None,
                    "source_synced": False,
                    "step_ids": tuple(
                        sorted(steps.filtered("counts_added_approvers").ids)
                    ),
                }

        owner_id = self.request_owner_id.id
        if owner_id in approver_staging and not self._allows_self_approval():
            del approver_staging[owner_id]
            trace.ROUTING.event("owner_not_staged", request=self.id, owner=owner_id)
        trace.ROUTING.items(
            "staged_user",
            lambda: [
                {
                    "request": self.id,
                    "user": user_id,
                    "seq": vals["sequence"],
                    "required": vals["required"],
                    "rule": vals.get("source_rule_id"),
                    "steps": list(vals.get("step_ids", ())),
                    "synced": vals.get("source_synced"),
                }
                for user_id, vals in sorted(approver_staging.items())
            ],
        )
        superseded_delegations = self.approver_ids.filtered(
            lambda a: (
                a.delegate_id
                and a.delegate_id.id in approver_staging
                and a.delegate_id.id != a.user_id.id
            ),
        )

        return DesiredApprovers(
            staging=approver_staging,
            existing_by_user=users_to_approver,
            duplicates=duplicate_approvers_to_delete,
            matched_rules=steps.when_rule_ids,
            superseded_delegations=superseded_delegations,
        )

    @api.model
    def _stage_approver_update(
        self,
        approver: models.BaseModel,
        rows_to_update: dict[tuple, list[int]],
        new_required: bool,
        new_sequence: int,
        new_source_rule_id: int | None = None,
        new_source_synced: bool = True,
        new_step_ids: tuple[int, ...] = (),
    ) -> None:
        if (
            approver.required != new_required
            or approver.sequence != new_sequence
            or approver.source_rule_id.id != (new_source_rule_id or False)
            or approver.source_synced != new_source_synced
            or tuple(sorted(approver.step_ids.ids)) != tuple(new_step_ids)
        ):
            key = (
                ("required", new_required),
                ("sequence", new_sequence),
                ("source_rule_id", new_source_rule_id),
                ("source_synced", new_source_synced),
                ("step_ids", tuple(new_step_ids)),
            )
            rows_to_update.setdefault(key, []).append(approver.id)
            trace.ROUTING.event(
                "row_needs_update",
                approver=approver.id,
                required=new_required,
                sequence=new_sequence,
                rule=new_source_rule_id,
                synced=new_source_synced,
                steps=list(new_step_ids),
            )
