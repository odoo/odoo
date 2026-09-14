import logging

from odoo import models

from . import approval_trace as trace

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = "res.users"

    def _is_approval_manager(self) -> bool:
        self.check_singleton()
        return self.has_group("approval.group_approval_manager")

    def write(self, vals):
        archiving = self.browse()
        if "active" in vals and not vals["active"]:
            archiving = self.filtered("active")
        res = super().write(vals)
        if archiving:
            archiving._approval_handover_on_archive()
        return res

    def _approval_handover_on_archive(self) -> None:
        rows = (
            self.env["approval.approver"]
            .sudo()
            .search(
                [
                    ("user_id", "in", self.ids),
                    ("state", "in", ("pending", "waiting")),
                    ("request_id.state", "=", "pending"),
                ],
            )
        )
        admin_user = self.env.user
        trace.CRUD.note("archive_handover", users=self.ids, rows=rows.ids)
        for row in rows:
            request = row.request_id
            departed = row.user_id

            effective = row._get_effective_approver()
            if effective != departed and effective.active:
                continue

            successor = request._get_escalation_manager(row)
            others = request.approver_ids - row
            illegal_targets = (
                departed
                | request.request_owner_id
                | others.user_id
                | others.delegate_id
            )
            reassignable = (
                successor
                and successor.active
                and successor not in illegal_targets
                and request.company_id in successor.company_ids
            )

            request.sudo()._get_user_approval_activities(
                user=departed,
            ).unlink()

            trace.DELEGATION.note(
                "handover",
                request=request.id,
                approver=row.id,
                departed=departed.id,
                successor=successor.id if successor else None,
                reassigned=bool(reassignable),
            )
            if reassignable:
                row.sudo().write(
                    {
                        "user_id": successor.id,
                        "source_synced": False,
                        "delegate_id": False,
                        "delegate_start_date": False,
                        "delegate_end_date": False,
                    },
                )
                if row.state == "pending":
                    row._create_activity()
                request.sudo().message_post(
                    body=self.env._(
                        "Pending approval reassigned from %(old)s to "
                        "%(new)s: the original approver's user account "
                        "was archived.",
                        old=departed.name,
                        new=successor.name,
                    ),
                    message_type="notification",
                )
            else:
                request.sudo().activity_schedule(
                    "mail.mail_activity_data_todo",
                    user_id=admin_user.id,
                    summary=self.env._(
                        "Replace departed approver %(name)s",
                        name=departed.name,
                    ),
                    note=self.env._(
                        "%(name)s was archived while this request still "
                        "awaits their approval, and no successor could be "
                        "reassigned automatically. As an approval manager "
                        "you can delegate their approval to someone else, "
                        "or reset the request to draft.",
                        name=departed.name,
                    ),
                )
                _logger.info(
                    "Approval handover: no automatic successor for "
                    "approver %s on request %s; To-Do created for %s.",
                    departed.login,
                    request.id,
                    admin_user.login,
                )

        stale_config = (
            self.env["approval.category.step.member"]
            .sudo()
            .search([("user_id", "in", self.ids)])
        )
        for member in stale_config:
            member.step_id.category_id.message_post(
                body=self.env._(
                    "%(name)s is still a member of step '%(step)s' of this "
                    "category but their user account was archived — new "
                    "requests would stall on them. Please update the step.",
                    name=member.user_id.name,
                    step=member.step_id.name,
                ),
                message_type="notification",
            )
