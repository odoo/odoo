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
    replacement: Any
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
        replacement = self._find_matching_replacement()
        document = self.get_source_document()
        snapshot: dict[str, Any] = {
            "category_name": cat.name,
            "approval_minimum": cat.approval_minimum,
            "approval_type": cat.approval_type,
            "approve_sequentially": cat.approve_sequentially,
            "group_approval": cat.group_approval,
            "allow_self_approval": cat.allow_self_approval,
            "notify_pool_members": cat.notify_pool_members,
            "approval_deadline_hours": cat.approval_deadline_hours,
            "sla_target_hours": cat.sla_target_hours,
            "sla_warning_pct": cat.sla_warning_pct,
            "approvers": [
                {
                    "user_id": a.user_id.id,
                    "user_name": a.user_id.name,
                    "required": a.required,
                    "sequence": a.sequence,
                }
                for a in cat.approver_ids
            ],
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
            approvers=len(snapshot["approvers"]),
            rules=len(snapshot["rules"]),
            steps=len(snapshot["steps"]),
            effective=len(snapshot["effective_approvers"]),
            minimum=snapshot["effective_approval_minimum"],
            replacement=replacement.id if replacement else None,
        )
        if replacement:
            snapshot["replacement_rule"] = {
                "id": replacement.id,
                "name": replacement.name,
                "condition_field": replacement.condition_field,
                "operator": replacement.operator,
                "threshold": replacement.threshold,
                "threshold_max": replacement.threshold_max,
                "approval_minimum": replacement.approval_minimum,
            }
        return snapshot

    def _matched_add_approver_rules(self):
        self.check_singleton()
        candidates = self.category_id.rule_ids.filtered(
            lambda r: (
                r.active
                and r.action_type == "add_approver"
                and self._rule_applies_to_company(r)
            ),
        )
        matched = candidates.filtered(lambda r: r._evaluate(self))
        trace.RULES.event(
            "add_approver_rules",
            request=self.id,
            candidates=candidates.ids,
            matched=matched.ids,
        )
        return matched

    def _get_applicable_steps(self):
        """The category's steps whose condition this request meets, in order."""
        self.check_singleton()
        if self.state != "new" and self.approver_ids and not self.approver_ids.step_ids:
            # Confirmed on the flat approver list before its category gained steps
            # (by conversion, or by hand): it finishes routing as it started, so a
            # later edit extends its approvers from the list, not from the steps.
            trace.STEPS.event("confirmed_flat", request=self.id, state=self.state)
            return self.env["approval.category.step"]
        applicable = self.category_id.step_ids.filtered(
            lambda step: step._is_applicable_to_request(self),
        ).sorted(lambda step: (step.sequence, step.id))
        trace.STEPS.event(
            "applicable",
            request=self.id,
            declared=len(self.category_id.step_ids),
            applicable=applicable.ids,
        )
        return applicable

    def _get_additional_approvers(self) -> list[tuple[int, bool, int]]:
        self.check_singleton()
        return []

    def _applied_rule_ids_after_sync(self, matched_rules):
        self.check_singleton()
        preserved = self.applied_rule_ids.filtered(
            lambda r: r.action_type != "add_approver",
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

    def _matched_add_approver_rule_by_user(self, matched_rules=None) -> dict[int, int]:
        self.check_singleton()
        if matched_rules is None:
            matched_rules = self._matched_add_approver_rules()
        mapping: dict[int, int] = {}
        contested: dict[int, list[int]] = {}
        for rule in matched_rules:
            for user in rule.approver_ids:
                if user.id in mapping:
                    contested.setdefault(user.id, [mapping[user.id]]).append(rule.id)
                mapping.setdefault(user.id, rule.id)
        if contested:
            trace.RULES.event(
                "rule_by_user_contested",
                request=self.id,
                users=sorted(contested),
                rules=contested,
                won=[mapping[user_id] for user_id in sorted(contested)],
            )
        return mapping

    def _get_managed_approver_user_ids(
        self,
        replacement=None,
        matched_rules=None,
    ) -> set[int]:
        self.check_singleton()
        managed = set(self.category_id.approver_ids.user_id.ids)
        document = self.get_source_document()
        for step in self._get_applicable_steps():
            managed.update(step._get_candidate_user_ids(document, self))
        if replacement:
            managed.update(replacement.approver_ids.ids)
        for rule in matched_rules or ():
            managed.update(rule.approver_ids.ids)
        if self.group_approval != "no" and self.approver_group_id:
            managed.update(self.approver_group_id.all_user_ids.ids)
        trace.ROUTING.event(
            "managed_users",
            request=self.id,
            managed=sorted(managed),
            replacement=replacement.id if replacement else None,
            rules=[rule.id for rule in matched_rules or ()],
            group=self.approver_group_id.id or None,
        )
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

    def _find_matching_replacement(self):
        self.check_singleton()
        candidates = self.category_id.rule_ids.filtered(
            lambda r: (
                r.active
                and r.action_type == "set_approvers"
                and self._rule_applies_to_company(r)
            ),
        )
        if not candidates:
            return False

        negative_fields = set()
        for rule in candidates.sorted(lambda r: (r.sequence, r.id)):
            if rule._evaluate(self):
                trace.RULES.event(
                    "replacement_matched",
                    request=self.id,
                    rule=rule.id,
                    field=rule.condition_field,
                    minimum=rule.approval_minimum,
                )
                return rule
            if rule.condition_type != "threshold":
                continue
            value = rule._get_field_value(self)
            if value is not None and value < 0:
                negative_fields.add(rule.condition_field)

        trace.RULES.event(
            "replacement_unmatched",
            request=self.id,
            candidates=candidates.ids,
            negative=sorted(negative_fields),
        )
        if negative_fields:
            _logger.warning(
                "Request %s: no approver-replacing rule matched (negative "
                "%s) — falling back to category '%s' default approvers.",
                self.id or "(new)",
                ", ".join(sorted(negative_fields)),
                self.category_id.name,
            )
        return False

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
                self.approver_ids.sudo()._approve_for_every_step()
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

    def _get_sequence_group(self) -> int:
        return self._get_sequence_param("group", 500)

    def _get_sequence_manager(self) -> int:
        return self._get_sequence_param("manager", 9)

    def _get_sequence_replacement(self) -> int:
        return self._get_sequence_param("tier", 10)

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
                "state": "new",
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

        self.category_id.fetch(["rule_ids", "approver_ids"])

        group_sequence = self._get_sequence_group()

        for request in self:
            desired = request._compute_desired_approvers(group_sequence)
            approver_staging = desired.staging
            users_to_approver = desired.existing_by_user
            replacement = desired.replacement

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
                            "state": vals["state"],
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
            elif replacement:
                effective_minimum = replacement.approval_minimum
            else:
                effective_minimum = request.category_id.approval_minimum
            trace.ROUTING.event(
                "desired",
                request=request.id,
                staged=len(approver_staging),
                existing=len(desired.existing_by_user),
                duplicates=len(desired.duplicates),
                replacement=replacement.id if replacement else None,
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

        live.category_id.fetch(["rule_ids", "approver_ids"])
        group_sequence = self._get_sequence_group()

        added = self.env["approval.approver"]
        for request in live:
            request._lock_and_reload()
            if request.state != "pending" or request.pending_change_field:
                continue
            added |= request._extend_approvers_live_one(group_sequence)
        return added

    def _extend_approvers_live_one(self, group_sequence: int) -> models.BaseModel:
        self.check_singleton()
        desired = self._compute_desired_approvers(group_sequence)
        replacement = desired.replacement
        matched_rules = desired.matched_rules
        superseded_delegations = desired.superseded_delegations

        missing = {
            user_id: vals
            for user_id, vals in desired.to_create.items()
            if vals.get("source_rule_id")
        }
        kept_orphans = [
            approver
            for user_id, approver in desired.existing_by_user.items()
            if user_id not in desired.staging
        ]
        trace.ROUTING.event(
            "live_extension",
            request=self.id,
            missing=sorted(missing),
            kept_orphans=[approver.id for approver in kept_orphans],
            replacement=replacement.id if replacement else None,
            rules=matched_rules.ids,
            superseded=superseded_delegations.ids,
        )
        if kept_orphans:
            _logger.info(
                "%s live: request %s keeps %d approver row(s) whose source "
                "no longer matches (%s) -- an approver already asked is never "
                "un-asked.",
                self._SYNC_LOG_PREFIX,
                self.id,
                len(kept_orphans),
                ", ".join(sorted(a.user_id.login for a in kept_orphans)),
            )

        self._raise_approval_minimum_live(replacement)

        if not missing:
            return self.env["approval.approver"]

        if superseded_delegations:
            self._retire_superseded_delegations(superseded_delegations)

        created = self._create_live_approver_rows(missing)
        created.filtered(lambda a: a.state == "pending")._create_activity()
        if matched_rules:
            self.sudo().applied_rule_ids |= matched_rules

        self.message_post(
            body=self.env._(
                "Approver(s) added because the request changed: %(names)s.\n\n"
                "The routing configured on category '%(category)s' now asks "
                "for them. Approvals already given stand.",
                names=", ".join(sorted(created.user_id.mapped("name"))),
                category=self.category_id.name,
            ),
            message_type="notification",
        )
        self._log_cycle("reroute", added=len(created))
        return created

    def _create_live_approver_rows(self, missing: dict[int, dict]):
        self.check_singleton()
        sequential = self.approve_sequentially
        anchor_sequence = min(
            (
                approver.sequence
                for approver in self.approver_ids
                if approver.state == "pending"
            ),
            default=0,
        )
        rows = [
            {
                "request_id": self.id,
                "user_id": user_id,
                "state": "waiting" if sequential else "pending",
                "required": vals["required"],
                "sequence": (
                    max(vals["sequence"], anchor_sequence)
                    if sequential
                    else vals["sequence"]
                ),
                "source_rule_id": vals.get("source_rule_id"),
                "source_synced": vals.get("source_synced", True),
            }
            for user_id, vals in sorted(
                missing.items(),
                key=lambda item: (item[1]["sequence"], item[0]),
            )
        ]
        trace.annotate(work=len(rows))
        trace.ROUTING.note(
            "live_rows",
            request=self.id,
            users=sorted(missing),
            sequential=sequential,
            anchor=anchor_sequence,
        )
        return (
            self.env["approval.approver"]
            .sudo()
            .with_context(approver_ids_computation=True)
            .create(rows)
        )

    def _raise_approval_minimum_live(self, replacement) -> None:
        self.check_singleton()
        if not replacement:
            return
        if replacement.approval_minimum > self.approval_minimum:
            trace.ROUTING.note(
                "minimum_raised_live",
                request=self.id,
                rule=replacement.id,
                was=self.approval_minimum,
                now=replacement.approval_minimum,
            )
            self.sudo().write({"approval_minimum": replacement.approval_minimum})

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

    def _compute_desired_approvers(self, group_sequence: int) -> DesiredApprovers:
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
        if steps:
            matched_rules = self.env["approval.rule"]
            additional = []
        else:
            matched_rules = self._matched_add_approver_rules()
            additional = self._get_additional_approvers()

        for rule in matched_rules:
            for user_id, required, sequence in rule._get_approver_tuples():
                self._merge_approver_to_staging(
                    approver_staging, user_id, required, sequence
                )

        trace.ROUTING.event(
            "additional_approvers",
            request=self.id,
            added=len(additional),
            routed_by_steps=bool(steps),
        )
        for user_id, required, sequence in additional:
            self._merge_approver_to_staging(
                approver_staging, user_id, required, sequence
            )

        step_ids_by_user: dict[int, set[int]] = {}
        replacement = False
        if steps:
            document = self.get_source_document()
            for step in steps:
                for user_id in step._get_pool_user_ids(document, self.company_id, self):
                    self._merge_approver_to_staging(
                        approver_staging, user_id, False, step.sequence
                    )
                    step_ids_by_user.setdefault(user_id, set()).add(step.id)
        elif self.group_approval != "exclusive":
            replacement = self._find_matching_replacement()
            if replacement:
                replacement_sequence = self._get_sequence_replacement()
                for user in replacement.approver_ids:
                    self._merge_approver_to_staging(
                        approver_staging,
                        user.id,
                        replacement.approver_required,
                        replacement_sequence,
                    )
            else:
                for cat_approver in self.category_id.approver_ids:
                    self._merge_approver_to_staging(
                        approver_staging,
                        cat_approver.user_id.id,
                        cat_approver.required,
                        cat_approver.sequence,
                    )

        if not steps and self.group_approval != "no" and self.approver_group_id:
            group_user_ids = self.env[
                "approval.category.step"
            ]._filter_company_user_ids(
                set(self.approver_group_id.all_user_ids.ids), self.company_id
            )
            for user_id in sorted(group_user_ids):
                self._merge_approver_to_staging(
                    approver_staging,
                    user_id,
                    False,
                    group_sequence,
                )

        rule_user_to_rule_id = self._matched_add_approver_rule_by_user(matched_rules)
        replacement_user_ids = (
            set(replacement.approver_ids.ids) if replacement else set()
        )
        for user_id, vals in approver_staging.items():
            if user_id in replacement_user_ids:
                vals["source_rule_id"] = replacement.id
            else:
                vals["source_rule_id"] = rule_user_to_rule_id.get(user_id)
            vals["step_ids"] = tuple(sorted(step_ids_by_user.get(user_id, ())))

        managed_user_ids = self._get_managed_approver_user_ids(
            replacement=replacement,
            matched_rules=matched_rules,
        )
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
                    "state": existing_approver.state,
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
            replacement=replacement,
            matched_rules=matched_rules,
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
