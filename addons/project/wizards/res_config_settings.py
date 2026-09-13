from odoo import fields, models

from ..tools import debug_log as dbg


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    module_hr_timesheet = fields.Boolean(string="Task Logs")
    group_project_stages = fields.Boolean(
        string="Project Stages",
        implied_group="project.group_project_stages",
    )

    def set_values(self) -> None:
        project_stage_change_mail_type = self.env.ref("project.mt_project_stage_change")
        if project_stage_change_mail_type.hidden == self["group_project_stages"]:
            dbg.lifecycle.debug(
                "res.config.settings.set_values: project stages=%s -> "
                "mt_project_stage_change hidden=%s",
                self["group_project_stages"],
                not self["group_project_stages"],
            )
            project_stage_change_mail_type.hidden = not self["group_project_stages"]
        super().set_values()
