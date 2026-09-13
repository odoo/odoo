from datetime import UTC, datetime, time

from odoo import fields, models
from odoo.libs.datetime import timezone


class MailActivityTodoCreate(models.TransientModel):
    _name = "mail.activity.todo.create"
    _description = "Create activity and todo at the same time"

    summary = fields.Char()
    date_deadline = fields.Date(
        string="Due Date",
        default=fields.Date.context_today,
        required=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Assigned to",
        default=lambda self: self.env.user,
        readonly=True,
        required=True,
    )
    note = fields.Html(sanitize_style=True)

    def _deadline_as_datetime(self):
        self.check_singleton()
        tz = timezone(self.env.user.tz or "UTC")
        local_end_of_day = datetime.combine(self.date_deadline, time.max, tzinfo=tz)
        return local_end_of_day.astimezone(UTC).replace(tzinfo=None, microsecond=0)

    def create_todo_activity(self):
        self.check_singleton()
        todo = self.env["project.task"].create(
            {
                "name": self.summary,
                "description": self.note,
                "date_end": self._deadline_as_datetime(),
                "user_ids": self.user_id.ids,
            }
        )
        self.env["mail.activity"].create(
            {
                "res_model_id": self.env["ir.model"]._get("project.task").id,
                "res_id": todo.id,
                "summary": self.summary,
                "user_id": self.user_id.id,
                "date_deadline": self.date_deadline,
                "activity_type_id": self.env["mail.activity"]
                ._default_activity_type_for_model("project.task")
                .id,
            }
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "message": self.env._(
                    "Your to-do has been successfully added to your pipeline."
                ),
            },
        }
