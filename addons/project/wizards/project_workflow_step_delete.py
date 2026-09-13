from typing import Any

from odoo import _, api, fields, models

from ..tools import debug_log as dbg


class ProjectWorkflowStepDeleteWizard(models.TransientModel):
    _name = "project.workflow.step.delete.wizard"
    _description = "Workflow Step Delete Wizard"

    project_ids = fields.Many2many(
        comodel_name="project.project",
        string="Projects",
        export_string_translation=False,
        domain="['|', ('active', '=', False), ('active', '=', True)]",
        ondelete="cascade",
    )
    step_ids = fields.Many2many(
        comodel_name="project.workflow.step",
        string="Steps To Delete",
        export_string_translation=False,
        ondelete="cascade",
    )
    tasks_count = fields.Integer(
        string="Number of Tasks",
        export_string_translation=False,
        compute="_compute_tasks_count",
    )
    steps_active = fields.Boolean(
        export_string_translation=False,
        compute="_compute_steps_active",
    )

    @api.depends("step_ids")
    def _compute_tasks_count(self) -> None:
        counts = dict(
            self.env["project.task"]
            .with_context(active_test=False)
            ._read_group(
                [("step_id", "in", self.step_ids.ids)],
                ["step_id"],
                ["__count"],
            )
        )
        for wizard in self:
            wizard.tasks_count = sum(
                counts.get(record, 0) for record in wizard.step_ids
            )

    @api.depends("step_ids")
    def _compute_steps_active(self) -> None:
        for wizard in self:
            wizard.steps_active = all(wizard.step_ids.mapped("active"))

    def action_archive(self) -> dict[str, Any]:
        dbg.logic.debug(
            "project.workflow.step.delete.wizard.action_archive: steps %s shared by "
            "%d projects -> %s",
            dbg.rec(self.step_ids),
            len(self.project_ids),
            "confirm" if len(self.project_ids) <= 1 else "ask",
        )
        if len(self.project_ids) <= 1:
            return self.action_confirm()

        return {
            "name": _("Confirmation"),
            "view_mode": "form",
            "res_model": "project.workflow.step.delete.wizard",
            "views": [
                (
                    self.env.ref(
                        "project.view_project_workflow_step_delete_confirmation_wizard"
                    ).id,
                    "form",
                )
            ],
            "type": "ir.actions.act_window",
            "res_id": self.id,
            "target": "new",
            "context": self.env.context,
        }

    def action_unarchive_task(self) -> None:
        inactive_tasks = (
            self.env["project.task"]
            .with_context(active_test=False)
            .search([("active", "=", False), ("step_id", "in", self.step_ids.ids)])
        )
        dbg.lifecycle.debug(
            "project.workflow.step.delete.wizard.action_unarchive_task: %s",
            dbg.rec(inactive_tasks),
        )
        inactive_tasks.action_unarchive()

    def action_confirm(self) -> dict[str, Any]:
        tasks = (
            self.with_context(active_test=False)
            .env["project.task"]
            .search([("step_id", "in", self.step_ids.ids)])
        )
        dbg.lifecycle.debug(
            "project.workflow.step.delete.wizard.action_confirm: archiving steps %s "
            "and tasks %s",
            dbg.rec(self.step_ids),
            dbg.rec(tasks),
        )
        tasks.write({"active": False})
        self.step_ids.write({"active": False})
        return self._prepare_action_close()

    def action_unlink(self) -> dict[str, Any]:
        dbg.lifecycle.debug(
            "project.workflow.step.delete.wizard.action_unlink: %s",
            dbg.rec(self.step_ids),
        )
        self.step_ids.unlink()
        return self._prepare_action_close()

    def _prepare_action_close(self) -> dict[str, Any]:
        return {
            "type": "ir.actions.act_window_close",
            "infos": {
                "success": True,
            },
        }
