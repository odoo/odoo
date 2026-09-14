import logging
from datetime import timedelta
from typing import Any

from markupsafe import Markup

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.tools import TransactionMemo

from . import approval_trace as trace
from .approval_utils import boolean_search_domain

DEFAULT_ESCALATION_MANAGER = TransactionMemo(
    "approval_default_escalation_manager",
    invalidated_by={
        "res.users": ("group_ids", "active"),
        "res.groups": ("user_ids", "implied_ids", "all_user_ids"),
    },
)

_logger = logging.getLogger(__name__)

CRON_BATCH_LIMIT = 500


class ApprovalRequestEscalation(models.Model):
    _inherit = "approval.request"

    ESCALATION_RULES = {
        "3": {
            "first_reminder": 4,
            "escalation": 8,
        },
        "2": {
            "first_reminder": 24,
            "escalation": 48,
        },
        "1": {
            "first_reminder": 48,
            "escalation": 96,
        },
        "0": {
            "first_reminder": 72,
            "escalation": 168,
        },
    }

    @api.model
    def _get_domain_overdue(self) -> list:
        return [
            ("state", "=", "pending"),
            ("approval_deadline", "!=", False),
            ("approval_deadline", "<", fields.Datetime.now()),
        ]

    @api.model
    def _search_is_overdue(
        self,
        operator: str,
        value: Any,
    ) -> list[tuple[str, str, Any]]:
        now = fields.Datetime.now()
        return boolean_search_domain(
            operator,
            value,
            true_domain=self._get_domain_overdue(),
            false_domain=[
                "|",
                "|",
                ("approval_deadline", "=", False),
                ("approval_deadline", ">=", now),
                ("state", "!=", "pending"),
            ],
        )

    @api.depends("date_confirmed", "category_snapshot")
    def _compute_approval_deadline(self) -> None:
        for request in self:
            hours = request._get_snapshot_config("approval_deadline_hours")
            if request.date_confirmed and hours:
                request.approval_deadline = request.date_confirmed + timedelta(
                    hours=hours,
                )
            else:
                request.approval_deadline = False

    @api.depends("approval_deadline", "state")
    def _compute_is_overdue(self) -> None:
        now = fields.Datetime.now()
        for request in self:
            request.is_overdue = (
                request.approval_deadline
                and request.approval_deadline < now
                and request.state == "pending"
            )

    @api.depends(
        "date_confirmed",
        "state",
        "date_approval_granted",
        "date_refused",
        "date_cancelled",
        "category_id.sla_target_hours",
        "category_id.sla_warning_pct",
        "category_snapshot",
    )
    def _compute_sla_status(self) -> None:
        now = fields.Datetime.now()
        for request in self:
            sla_hours = request._get_snapshot_config("sla_target_hours")
            if not sla_hours or not request.date_confirmed:
                request.sla_status = "no_sla"
                continue

            if request.state in self._TERMINAL_STATES:
                resolved_date = {
                    "approved": request.date_approval_granted,
                    "refused": request.date_refused,
                    "cancelled": request.date_cancelled,
                }.get(request.state) or now
                elapsed = (
                    resolved_date - request.date_confirmed
                ).total_seconds() / 3600
                request.sla_status = "met" if elapsed <= sla_hours else "breached"
                continue

            elapsed = (now - request.date_confirmed).total_seconds() / 3600
            request.sla_status = self._sla_status_for(
                elapsed,
                sla_hours,
                request._get_snapshot_config("sla_warning_pct"),
            )

    _SLA_DEFAULT_WARNING_PCT = 80

    _SLA_TARGET_SQL = (
        "COALESCE((ar.category_snapshot ->> 'sla_target_hours')::numeric, "
        "ac.sla_target_hours, 0)"
    )

    _SLA_WARNING_SQL = (
        "COALESCE((ar.category_snapshot ->> 'sla_warning_pct')::numeric, "
        "ac.sla_warning_pct)"
    )

    @api.model
    def _sla_status_for(
        self,
        elapsed_hours: float,
        sla_hours: float,
        warning_pct: float | None,
    ) -> str:
        warning_hours = sla_hours * (
            (warning_pct or self._SLA_DEFAULT_WARNING_PCT) / 100
        )
        if elapsed_hours > sla_hours:
            status = "breached"
        elif elapsed_hours > warning_hours:
            status = "at_risk"
        else:
            status = "on_track"
        trace.ESCALATION.event(
            "sla_status",
            elapsed_hours=elapsed_hours,
            sla_hours=sla_hours,
            warning_hours=warning_hours,
            status=status,
        )
        return status

    @api.model
    def _search_sla_status(self, operator: str, value: str | list | None) -> list:
        if operator not in ("=", "!=", "in", "not in"):
            raise NotImplementedError(
                f"Unsupported operator {operator!r} for sla_status"
            )
        wanted = {value} if isinstance(value, str) else set(value or ())
        all_statuses = {s[0] for s in self._fields["sla_status"].selection}
        if operator in ("!=", "not in"):
            wanted = all_statuses - wanted
        self.env["approval.request"].flush_model()
        self.env["approval.category"].flush_model()
        where_sql = ""
        if "no_sla" not in wanted:
            where_sql = (
                f"WHERE {self._SLA_TARGET_SQL} > 0 AND ar.date_confirmed IS NOT NULL"
            )
        default_warning_pct = self._SLA_DEFAULT_WARNING_PCT
        sla_target = self._SLA_TARGET_SQL
        sla_warning = self._SLA_WARNING_SQL
        self.env.cr.execute(
            f"""
            SELECT id FROM (
            SELECT ar.id,
                   CASE
                       WHEN {sla_target} = 0
                            OR ar.date_confirmed IS NULL
                           THEN 'no_sla'
                       WHEN ar.state IN ('approved', 'refused', 'cancelled')
                           THEN CASE
                               -- Keyed on the CURRENT state's date
                               -- (mirrors _compute_sla_status). Since
                               -- 19.0.1.0.22 the stamps are cleared when
                               -- the request leaves the state they
                               -- record, so only one is ever set; the
                               -- COALESCE stays as a guard for rows
                               -- written before that.
                               WHEN COALESCE(
                                       CASE ar.state
                                           WHEN 'approved' THEN ar.date_approval_granted
                                           WHEN 'refused' THEN ar.date_refused
                                           WHEN 'cancelled' THEN ar.date_cancelled
                                       END,
                                       NOW() AT TIME ZONE 'UTC')
                                    <= ar.date_confirmed
                                       + {sla_target} * INTERVAL '1 hour'
                                   THEN 'met'
                               ELSE 'breached'
                           END
                       WHEN NOW() AT TIME ZONE 'UTC'
                            > ar.date_confirmed
                              + {sla_target} * INTERVAL '1 hour'
                           THEN 'breached'
                       WHEN NOW() AT TIME ZONE 'UTC'
                            > ar.date_confirmed
                              + {sla_target}
                                * COALESCE(
                                      NULLIF({sla_warning}, 0),
                                      {default_warning_pct}
                                  )
                                / 100.0 * INTERVAL '1 hour'
                           THEN 'at_risk'
                       ELSE 'on_track'
                   END AS status
            FROM approval_request ar
            JOIN approval_category ac ON ac.id = ar.category_id
            {where_sql}
            ) AS classified
            WHERE status = ANY(%s)
            """,
            [sorted(wanted)],
        )
        return [("id", "in", [rid for (rid,) in self.env.cr.fetchall()])]

    @api.depends("date_confirmed")
    def _compute_sla_elapsed_hours(self) -> None:
        now = fields.Datetime.now()
        for request in self:
            if request.date_confirmed:
                delta = now - request.date_confirmed
                request.sla_elapsed_hours = delta.total_seconds() / 3600
            else:
                request.sla_elapsed_hours = 0.0

    @api.depends("date_confirmed", "category_id.sla_target_hours", "category_snapshot")
    def _compute_sla_remaining_hours(self) -> None:
        now = fields.Datetime.now()
        for request in self:
            sla_hours = request._get_snapshot_config("sla_target_hours")
            if not sla_hours or not request.date_confirmed:
                request.sla_remaining_hours = 0.0
                continue
            elapsed = (now - request.date_confirmed).total_seconds() / 3600
            request.sla_remaining_hours = sla_hours - elapsed

    @api.model
    def cron_smart_escalation(self) -> int:
        now = fields.Datetime.now()
        reminders_sent = 0

        self._reconcile_delegation_activities()

        for priority, rules in self._get_escalation_rules().items():
            reminder_threshold = now - timedelta(hours=rules["first_reminder"])
            escalation_threshold = now - timedelta(hours=rules["escalation"])

            domain = [
                ("state", "=", "pending"),
                ("priority", "=", priority),
                ("pending_change_field", "=", False),
                "|",
                ("last_reminder_date", "=", False),
                ("last_reminder_date", "<", reminder_threshold),
                ("date_confirmed", "<", reminder_threshold),
            ]

            # One query per ESCALATION_RULES entry, not per record: the loop is
            # over the priority selection, so the count is fixed and independent
            # of the data. Each priority carries its own reminder threshold and
            # its own CRON_BATCH_LIMIT, which one merged query cannot preserve.
            requests_to_remind = self.search(  # pylint: disable=n-plus-one-query
                domain,
                order="date_confirmed asc",
                limit=CRON_BATCH_LIMIT,
            )

            trace.CRON.event(
                "escalation_batch",
                priority=priority,
                first_reminder_h=rules["first_reminder"],
                escalation_h=rules["escalation"],
                requests=requests_to_remind.ids,
                limit=CRON_BATCH_LIMIT,
            )
            acknowledged_by_count: dict[int, list[int]] = {}

            for request in requests_to_remind:
                try:
                    with self.env.cr.savepoint():
                        did_work = self._escalate_or_remind_one(
                            request, escalation_threshold
                        )
                except Exception:
                    _logger.exception(
                        "Smart escalation failed for request %s; skipping.",
                        request.id,
                    )
                    continue

                if not did_work:
                    continue

                acknowledged_by_count.setdefault(
                    request.reminder_count,
                    [],
                ).append(request.id)
                reminders_sent += 1

            for prior_count, ids in acknowledged_by_count.items():
                self.browse(ids).sudo().write(
                    {
                        "last_reminder_date": now,
                        "reminder_count": prior_count + 1,
                    }
                )

        trace.annotate(work=reminders_sent)
        trace.CRON.note("escalation_done", reminded=reminders_sent)
        if reminders_sent:
            _logger.info("Smart escalation: Sent %s reminders", reminders_sent)

        return reminders_sent

    def _escalate_or_remind_one(self, request, escalation_threshold) -> int:
        has_stalled_approver = any(
            not a._get_effective_approver().active
            for a in request.approver_ids
            if a.state == "pending"
        )
        # escalated_to_manager gates both triggers. A stalled approver is a
        # reason to escalate ahead of the age threshold, not a reason to
        # escalate again on every run: it does not clear itself, so binding it
        # to the flag alone re-sent the same notice daily for the life of the
        # request. Reset to draft clears the flag and re-opens escalation.
        needs_escalation = not request.escalated_to_manager and (
            has_stalled_approver or request.date_confirmed < escalation_threshold
        )
        trace.ESCALATION.event(
            "triage",
            request=request.id,
            stalled_approver=has_stalled_approver,
            already_escalated=request.escalated_to_manager,
            confirmed=request.date_confirmed,
            escalates=needs_escalation,
            reminders=request.reminder_count,
        )
        if not needs_escalation:
            return request._send_reminder()
        did_work = request._escalate_to_manager()
        _by_manager, not_escalated = request._resolve_escalation_targets()
        if not_escalated:
            did_work = request._send_reminder(not_escalated) or did_work
        return did_work

    @api.model
    def _reconcile_delegation_activities(self) -> None:
        pending_approvers = self.env["approval.approver"].search(
            [
                ("state", "=", "pending"),
                ("request_id.state", "=", "pending"),
                ("delegate_id", "!=", False),
            ],
            order="id",
            limit=CRON_BATCH_LIMIT,
        )
        for approver in pending_approvers:
            request = approver.request_id
            effective = approver._get_effective_approver()
            asked = request._get_approval_activities()
            correct = asked.filtered(lambda a, u=effective: a.user_id == u)
            stale = asked.filtered(
                lambda a, u=effective, ap=approver: (
                    a.user_id != u and a.user_id in (ap.user_id | ap.delegate_id)
                ),
            )
            if not stale:
                continue
            trace.ESCALATION.event(
                "delegation_activities",
                approver=approver.id,
                request=request.id,
                effective=effective.id,
                correct=correct.ids,
                stale=stale.ids,
            )
            try:
                with self.env.cr.savepoint():
                    if correct:
                        stale.action_feedback()
                    else:
                        stale[:1].sudo().write({"user_id": effective.id})
                        stale[1:].action_feedback()
            except Exception:
                _logger.exception(
                    "Delegation activity reconciliation failed for "
                    "approver %s; skipping.",
                    approver.id,
                )

    @api.model
    def cron_auto_expire(self) -> None:
        expired_requests, hours_by_category = self._eligible_by_category_domain(
            "auto_expire_hours",
        )
        if not expired_requests:
            return

        expired_count = 0
        for request in expired_requests:
            body = self.env._(
                "This request was automatically cancelled after exceeding "
                "the %(hours)d-hour expiration window.",
                hours=hours_by_category[request.category_id.id],
            )
            try:
                with self.env.cr.savepoint():
                    request._force_terminal(
                        "cancelled",
                        body=body,
                        subtype_xmlid="mail.mt_note",
                    )
                expired_count += 1
            except Exception:
                _logger.exception(
                    "Auto-expire failed for request %s; skipping.",
                    request.id,
                )

        trace.annotate(work=len(expired_requests))
        trace.CRON.note(
            "auto_expire_done",
            eligible=len(expired_requests),
            cancelled=expired_count,
        )
        if expired_count:
            _logger.info("Auto-expire: Cancelled %d expired requests", expired_count)

    @api.model
    def _eligible_by_category_domain(
        self,
        hours_field: str,
        extra_domain=None,
    ):
        categories = self.env["approval.category"].search([(hours_field, ">", 0)])
        if not categories:
            return self.browse(), {}

        now = fields.Datetime.now()
        hours_by_category = {c.id: c[hours_field] for c in categories}
        windows = Domain.FALSE
        for category in categories:
            windows |= Domain(
                [
                    ("category_id", "=", category.id),
                    (
                        "date_confirmed",
                        "<=",
                        now - timedelta(hours=hours_by_category[category.id]),
                    ),
                ],
            )
        domain = Domain([("state", "=", "pending")]) & windows
        if extra_domain:
            domain &= Domain(extra_domain)
        requests = self.search(
            domain,
            order="date_confirmed asc",
            limit=CRON_BATCH_LIMIT,
        )
        trace.CRON.event(
            "eligible_by_window",
            window=hours_field,
            categories=len(categories),
            requests=requests.ids,
            capped=len(requests) == CRON_BATCH_LIMIT,
        )
        return requests, hours_by_category

    @api.model
    def cron_consent_approval(self) -> None:
        eligible, _hours = self._eligible_by_category_domain(
            "consent_approval_hours",
            extra_domain=[("pending_change_field", "=", False)],
        )
        consent_count = 0
        for request in eligible:
            try:
                with self.env.cr.savepoint():
                    if self._consent_approve_one(request, request.category_id):
                        consent_count += 1
            except Exception:
                _logger.exception(
                    "Consent approval failed for request %s; skipping.",
                    request.id,
                )

        trace.annotate(work=len(eligible))
        trace.CRON.note("consent_done", eligible=len(eligible), approved=consent_count)
        if consent_count:
            _logger.info(
                "Consent approval: Auto-approved %d requests",
                consent_count,
            )

    def _consent_approve_one(self, request, category) -> bool:
        if not request._can_consent_approve():
            return False

        request._lock_and_reload(with_approvers=True)
        if request.state != "pending":
            return False

        pending = request.approver_ids.filtered(lambda a: a.state == "pending")
        if not pending:
            return False

        old_state = request.state
        trace.ESCALATION.note(
            "consent_approve",
            request=request.id,
            rows=pending.ids,
            hours=category.consent_approval_hours,
        )
        pending.sudo()._approve_for_every_step(
            note=self.env._(
                "No objection within the %(hours)d-hour consent window.",
                hours=category.consent_approval_hours,
            )
        )
        request._cancel_activities()
        request._notify_if_terminal_transition(old_state)
        request.message_post(
            body=self.env._(
                "Auto-approved by consent: no objection received "
                "within %(hours)d-hour window.",
                hours=category.consent_approval_hours,
            ),
            message_type="notification",
            subtype_xmlid="mail.mt_note",
        )
        return True

    def _can_consent_approve(self) -> bool:
        self.check_singleton()
        return True

    def _get_escalation_manager(self, approver) -> Any:
        category = self.category_id
        if (
            category.escalate_overdue
            and category.escalation_user_id
            and category.escalation_user_id.active
        ):
            return category.escalation_user_id
        return self._get_default_escalation_manager()

    def _get_default_escalation_manager(self) -> Any:
        cache = DEFAULT_ESCALATION_MANAGER(self.env)
        company_id = self.company_id.id
        if company_id not in cache:
            group = self.env.ref(
                "approval.group_approval_manager", raise_if_not_found=False
            )
            cache[company_id] = (
                self.env["res.users"]
                .search(
                    [
                        ("all_group_ids", "in", group.id),
                        ("company_ids", "in", company_id),
                        ("active", "=", True),
                    ],
                    order="id",
                    limit=1,
                )
                .id
                if group
                else False
            )
        manager = self.env["res.users"].browse(cache[company_id] or ())
        trace.ESCALATION.event(
            "default_manager",
            request=self.id,
            company=company_id,
            manager=manager.id or None,
            memo_size=len(cache),
        )
        return manager

    @api.model
    def _invalidate_escalation_manager_cache(self) -> None:
        DEFAULT_ESCALATION_MANAGER.discard(self.env)

    def _resolve_escalation_targets(self) -> tuple[dict, models.BaseModel]:
        self.check_singleton()
        by_manager: dict = {}
        unescalated = self.env["approval.approver"]
        for approver in self.approver_ids.filtered(lambda a: a.state == "pending"):
            manager = self._get_escalation_manager(approver)
            if manager:
                by_manager.setdefault(manager, self.env["approval.approver"])
                by_manager[manager] |= approver
            else:
                unescalated |= approver
        trace.ESCALATION.event(
            "targets",
            request=self.id,
            managers=[manager.id for manager in by_manager],
            unescalated=unescalated.ids,
        )
        return by_manager, unescalated

    def _escalate_to_manager(self) -> int:
        self.check_singleton()
        by_manager, _unescalated = self._resolve_escalation_targets()
        if not by_manager:
            return 0

        priority_label = dict(self._fields["priority"].selection)[self.priority]
        for manager, approvers in by_manager.items():
            self.message_post(
                # The markup is the template and the values are its arguments:
                # a translated str carrying tags is escaped by message_post and
                # reaches the reader as visible source.
                body=Markup(
                    self.env._(
                        "<p><strong>Escalation Notice</strong></p>"
                        "<p>Approval request <strong>%(name)s</strong> has been pending for %(duration)s.</p>"
                        "<ul>"
                        "<li><strong>Priority:</strong> %(priority)s</li>"
                        "<li><strong>Assigned approver(s):</strong> %(approver)s</li>"
                        "<li><strong>Reminders sent:</strong> %(count)d</li>"
                        "</ul>"
                        "<p>Please follow up.</p>"
                    )
                )
                % {
                    "name": self.name,
                    "duration": self._get_pending_duration(),
                    "priority": priority_label,
                    "approver": ", ".join(sorted(approvers.user_id.mapped("name"))),
                    "count": self.reminder_count,
                },
                subject=self.env._(
                    "Escalation: Overdue Approval - %(name)s", name=self.name
                ),
                partner_ids=manager.partner_id.ids,
                subtype_xmlid="mail.mt_note",
            )

        trace.ESCALATION.note(
            "escalated",
            request=self.id,
            managers=[manager.id for manager in by_manager],
            reminders=self.reminder_count,
        )
        self.sudo().escalated_to_manager = True
        return len(by_manager)

    def _get_pending_duration(self) -> str:
        self.check_singleton()
        if not self.date_confirmed:
            return self.env._("Unknown")

        delta = fields.Datetime.now() - self.date_confirmed
        days = delta.days
        hours = delta.seconds // 3600

        if days > 0:
            return self.env._("%(count)d day(s)", count=days)
        return self.env._("%(count)d hour(s)", count=hours)

    @api.model
    def _get_escalation_rules(self) -> dict[str, dict[str, int]]:
        icp = self.env["ir.config_parameter"].sudo()
        rules = {p: dict(kinds) for p, kinds in self.ESCALATION_RULES.items()}
        for priority, kinds in rules.items():
            for kind in kinds:
                param = icp.get_param(f"approval.escalation.{priority}.{kind}")
                if not param:
                    continue
                try:
                    kinds[kind] = int(param)
                except ValueError:
                    _logger.warning(
                        "Ignoring invalid approval.escalation.%s.%s = %r",
                        priority,
                        kind,
                        param,
                    )
        trace.ESCALATION.event("escalation_rules", rules=rules)
        return rules

    def _send_reminder(self, approvers: models.BaseModel | None = None) -> int:
        self.check_singleton()
        pending_approvers = (
            approvers
            if approvers is not None
            else self.approver_ids.filtered(lambda a: a.state == "pending")
        )

        priority_label = dict(self._fields["priority"].selection)[self.priority]
        activity_type = self.env.ref("approval.mail_activity_data_approval")
        reminded = 0

        for approver in pending_approvers:
            effective_user = approver._get_effective_approver()

            if not effective_user.active:
                trace.ESCALATION.event(
                    "reminder_skipped",
                    request=self.id,
                    approver=approver.id,
                    user=effective_user.id,
                    reason="inactive_user",
                )
                continue

            existing_activity = self._get_approval_activities(user=effective_user)

            reminder_note = self.env._(
                "<p><strong>Priority:</strong> %(priority)s</p>"
                "<p>This approval has been pending for %(duration)s.</p>"
                "<p><strong>Reminders sent:</strong> %(count)d</p>",
                priority=priority_label,
                duration=self._get_pending_duration(),
                count=self.reminder_count,
            )

            if existing_activity:
                existing_activity[:1].write(
                    {
                        "summary": self.env._(
                            "Approval Reminder: %(name)s", name=self.name
                        ),
                        "note": reminder_note,
                        "date_deadline": fields.Date.today(),
                    },
                )
            else:
                approver._get_activity_target().activity_schedule(
                    activity_type_id=(
                        approver._get_activity_type() or activity_type
                    ).id,
                    user_id=effective_user.id,
                    approver_id=approver.id,
                    summary=self.env._("Approval Reminder: %(name)s", name=self.name),
                    note=reminder_note,
                )
            reminded += 1

        trace.annotate(work=len(pending_approvers))
        trace.ESCALATION.event(
            "reminded",
            request=self.id,
            asked=pending_approvers.ids,
            reminded=reminded,
            count=self.reminder_count,
        )
        return reminded
