from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ProjectTaskTriage(models.Model):
    _name = "project.task.triage"
    _description = "Task Triage Assignment"
    _rec_name = "triage_id"

    task_id = fields.Many2one(
        comodel_name="project.task",
        export_string_translation=False,
        index=True,
        required=True,
        ondelete="cascade",
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        export_string_translation=False,
        index=True,
        required=True,
        ondelete="cascade",
    )
    triage_id = fields.Many2one(
        comodel_name="project.triage",
        export_string_translation=False,
        domain="[('user_id', '=', user_id)]",
        ondelete="set null",
    )

    _project_task_triage_unique = models.Constraint(
        "UNIQUE (task_id, user_id)",
        "A task can only have one triage bucket per user.",
    )

    @api.constrains("user_id", "triage_id")
    def _check_triage_owner(self) -> None:
        for rec in self:
            if rec.triage_id and rec.triage_id.user_id != rec.user_id:
                raise ValidationError(
                    self.env._(
                        "A personal triage bucket must belong to the same user "
                        "as the task-triage entry."
                    )
                )
