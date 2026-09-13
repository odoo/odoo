from odoo import fields, models

from ..tools import debug_log as dbg


class ProjectTaskLostReason(models.Model):
    _name = "project.task.lost.reason"
    _description = "Project Task Lost Reason"
    _inherit = ["mixin.catalog"]

    name = fields.Char(string="Description")
    task_count = fields.Integer(
        string="Tasks count",
        compute="_compute_task_count",
    )

    @dbg.timed
    def _compute_task_count(self) -> None:
        task_data = (
            self.env["project.task"]
            .with_context(active_test=False)
            ._read_group(
                [("lost_reason_id", "in", self.ids)],
                ["lost_reason_id"],
                ["__count"],
            )
        )
        mapped_data = {lost_reason.id: count for lost_reason, count in task_data}
        for reason in self:
            reason.task_count = mapped_data.get(reason.id, 0)

    def action_tasks_lost(self) -> dict:
        return {
            "name": self.env._("Tasks"),
            "view_mode": "list,form",
            "domain": [("lost_reason_id", "in", self.ids)],
            "res_model": "project.task",
            "type": "ir.actions.act_window",
            "context": {"create": False, "active_test": False},
        }
