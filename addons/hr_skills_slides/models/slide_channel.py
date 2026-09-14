from markupsafe import Markup

from odoo import _, fields, models
from odoo.libs.debug_log import DebugLog
from odoo.tools import html2plaintext

_debug = DebugLog(__name__)


class SlideChannelPartner(models.Model):
    _inherit = "slide.channel.partner"

    def _post_completion_update_hook(self, completed=True):
        res = super()._post_completion_update_hook(completed)
        if not completed:
            return res
        completed_memberships = self.filtered(
            lambda membership: membership.member_status == "completed"
        )
        if not completed_memberships:
            return res
        employees_by_partner = (
            self.env["hr.employee"]
            .sudo()
            .search(
                [("user_id.partner_id", "in", completed_memberships.partner_id.ids)]
            )
            .grouped(lambda employee: employee.user_id.partner_id)
        )
        if not employees_by_partner:
            _debug.logic(
                "course_completion_no_employee", memberships=completed_memberships
            )
            return res
        resume_lines = self.env["hr.resume.line"].sudo()
        line_type = self.env.ref(
            "hr_skills.resume_type_training", raise_if_not_found=False
        )
        recorded = {
            (line.employee_id, line.channel_id)
            for line in resume_lines.search(
                [
                    (
                        "employee_id",
                        "in",
                        [
                            employee.id
                            for employees in employees_by_partner.values()
                            for employee in employees
                        ],
                    ),
                    ("channel_id", "in", completed_memberships.channel_id.ids),
                    ("line_type_id", "=", line_type.id if line_type else False),
                ]
            )
        }
        lines_to_create = []
        for membership in completed_memberships:
            channel = membership.channel_id
            for employee in employees_by_partner.get(membership.partner_id, ()):
                if (employee, channel) in recorded:
                    continue
                recorded.add((employee, channel))
                lines_to_create.append(
                    {
                        "employee_id": employee.id,
                        "name": channel.name,
                        "date_start": fields.Date.today(),
                        "description": html2plaintext(channel.description),
                        "line_type_id": line_type.id if line_type else False,
                        "course_type": "elearning",
                        "channel_id": channel.id,
                    }
                )
        if lines_to_create:
            _debug.lifecycle(
                "course_resume_lines_created",
                memberships=completed_memberships,
                created=len(lines_to_create),
            )
            resume_lines.create(lines_to_create)
        return res

    def _send_completed_mail(self):
        super()._send_completed_mail()
        for membership in self:
            membership.channel_id._message_employee_chatter(
                _(
                    "The employee has completed the course %s",
                    Markup('<a href="%(link)s">%(course)s</a>')
                    % {
                        "link": membership.channel_id.website_absolute_url,
                        "course": membership.channel_id.name,
                    },
                ),
                membership.partner_id,
            )


class SlideChannel(models.Model):
    _inherit = "slide.channel"

    def _action_add_members(
        self, target_partners, member_status="joined", raise_on_access=False
    ):
        res = super()._action_add_members(
            target_partners,
            member_status=member_status,
            raise_on_access=raise_on_access,
        )
        if member_status == "joined":
            for channel in self:
                channel._message_employee_chatter(
                    _(
                        "The employee subscribed to the course %s",
                        Markup('<a href="%(link)s">%(course)s</a>')
                        % {
                            "link": channel.website_absolute_url,
                            "course": channel.name,
                        },
                    ),
                    target_partners,
                )
        return res

    def _remove_membership(self, partner_ids):
        res = super()._remove_membership(partner_ids)

        partners = self.env["res.partner"].browse(partner_ids)

        for channel in self:
            channel._message_employee_chatter(
                _(
                    "The employee left the course %s",
                    Markup('<a href="%(link)s">%(course)s</a>')
                    % {
                        "link": channel.website_absolute_url,
                        "course": channel.name,
                    },
                ),
                partners,
            )
        return res

    def _message_employee_chatter(self, msg, partners):
        for partner in partners:
            employee = (
                partner.user_ids.sudo()
                .filtered(
                    lambda u, partner=partner: (
                        u.employee_id
                        and (
                            not partner.company_id
                            or u.employee_id.company_id == partner.company_id
                        )
                    )
                )
                .employee_id
            )

            if employee:
                employee.sudo().message_post(body=msg)
