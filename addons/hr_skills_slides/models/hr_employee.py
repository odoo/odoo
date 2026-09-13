from odoo import _, api, fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    subscribed_courses = fields.Many2many(
        comodel_name="slide.channel",
        related="partner_id.slide_channel_ids",
    )
    has_subscribed_courses = fields.Boolean(
        compute="_compute_courses_completion_text",
        compute_sudo=True,
    )
    courses_completion_text = fields.Char(
        compute="_compute_courses_completion_text",
        compute_sudo=True,
    )

    @api.depends_context("lang")
    @api.depends("subscribed_courses", "partner_id.slide_channel_completed_ids")
    def _compute_courses_completion_text(self):
        for employee in self:
            if not employee.user_id:
                employee.courses_completion_text = False
                employee.has_subscribed_courses = False
                continue
            total_completed_courses = len(
                employee.partner_id.slide_channel_completed_ids
            )
            total = len(employee.subscribed_courses)
            employee.courses_completion_text = _(
                "%(completed)s / %(total)s",
                completed=total_completed_courses,
                total=total,
            )
            employee.has_subscribed_courses = total > 0

    def action_view_courses(self):
        self.check_singleton()
        return {
            "type": "ir.actions.act_url",
            "target": "self",
            "url": "/profile/user/%s" % self.user_id.id,
        }
