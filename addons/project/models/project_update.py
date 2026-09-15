from collections import defaultdict
from typing import Any, Self

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.api import ValuesType
from odoo.fields import Domain
from odoo.tools import format_amount, formatLang

from ..tools import debug_log as dbg

STATUS_COLOR = {
    "on_track": 20,
    "at_risk": 22,
    "off_track": 23,
    "on_hold": 21,
    "done": 24,
    False: 0,
    "to_define": 0,
}


class ProjectUpdate(models.Model):
    _name = "project.update"
    _description = "Project Update"
    _order = "id desc"
    _inherit = ["mixin.mail.thread.cc", "mixin.mail.activity"]

    @dbg.timed
    @api.model
    def default_get(self, fields: list[str]) -> dict:
        result = super().default_get(fields)
        if "project_id" in fields and not result.get("project_id"):
            result["project_id"] = self.env.context.get("active_id")
        if result.get("project_id"):
            project = self.env["project.project"].browse(result["project_id"])
            dbg.logic.debug(
                "project.update.default_get [project:%s]: last status=%s progress=%s",
                project.id,
                project.last_update_status,
                project.last_update_id.progress,
            )
            if "progress" in fields and not result.get("progress"):
                result["progress"] = project.last_update_id.progress
            if "description" in fields and not result.get("description"):
                result["description"] = self._prepare_description(project)
            if "status" in fields and not result.get("status"):
                result["status"] = (
                    project.last_update_status
                    if project.last_update_status != "to_define"
                    else "on_track"
                )
        return result

    name = fields.Char(
        string="Title",
        required=True,
        tracking=True,
    )
    status = fields.Selection(
        selection=[
            ("on_track", "On Track"),
            ("at_risk", "At Risk"),
            ("off_track", "Off Track"),
            ("on_hold", "On Hold"),
            ("done", "Complete"),
        ],
        export_string_translation=False,
        required=True,
        tracking=True,
    )
    color = fields.Integer(
        export_string_translation=False,
        compute="_compute_color",
    )
    progress = fields.Integer(tracking=True)
    progress_percentage = fields.Float(
        export_string_translation=False,
        compute="_compute_progress_percentage",
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Author",
        default=lambda self: self.env.user,
        required=True,
    )
    description = fields.Html()
    date = fields.Date(
        default=fields.Date.context_today,
        tracking=True,
    )
    project_id = fields.Many2one(
        comodel_name="project.project",
        export_string_translation=False,
        index=True,
        required=True,
        domain=[("is_template", "=", False)],
    )
    name_cropped = fields.Char(
        export_string_translation=False,
        compute="_compute_name_cropped",
    )
    task_count = fields.Integer(
        export_string_translation=False,
        readonly=True,
    )
    closed_task_count = fields.Integer(
        export_string_translation=False,
        readonly=True,
    )
    closed_task_percentage = fields.Integer(
        export_string_translation=False,
        compute="_compute_closed_task_percentage",
    )
    label_tasks = fields.Char(related="project_id.label_tasks")

    @api.depends("status")
    def _compute_color(self) -> None:
        for update in self:
            update.color = STATUS_COLOR[update.status]

    @api.depends("progress")
    def _compute_progress_percentage(self) -> None:
        for update in self:
            update.progress_percentage = update.progress / 100

    @api.depends("name")
    def _compute_name_cropped(self) -> None:
        for update in self:
            update.name_cropped = (
                (update.name[:57] + "...")
                if update.name and len(update.name) > 60
                else update.name
            )

    @api.depends("closed_task_count", "task_count")
    def _compute_closed_task_percentage(self) -> None:
        for update in self:
            update.closed_task_percentage = update.task_count and round(
                update.closed_task_count * 100 / update.task_count
            )

    @dbg.timed
    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        dbg.lifecycle.debug(
            "project.update.create: %d vals, keys=%s",
            len(vals_list),
            dbg.vals_keys(vals_list),
        )
        updates = super().create(vals_list)
        per_snapshot = defaultdict(self.browse)
        for update in updates:
            project = update.project_id
            project.sudo().last_update_id = update
            per_snapshot[
                (project.task_count, project.task_count - project.open_task_count)
            ] |= update
        for (task_count, closed_task_count), group in per_snapshot.items():
            dbg.pipeline.debug(
                "[update:%s] create -> snapshot tasks=%d closed=%d",
                dbg.rec(group),
                task_count,
                closed_task_count,
            )
            group.write(
                {"task_count": task_count, "closed_task_count": closed_task_count}
            )
        return updates

    @dbg.timed
    def unlink(self) -> bool:
        projects = self.project_id
        dbg.lifecycle.debug(
            "project.update.unlink %s on projects %s", dbg.rec(self), dbg.rec(projects)
        )
        res = super().unlink()
        if not projects:
            return res
        latest_per_project = {}
        for update in self.search(
            [("project_id", "in", projects.ids)], order="date desc, id desc"
        ):
            latest_per_project.setdefault(update.project_id.id, update)
        for project in projects:
            latest = latest_per_project.get(project.id, False)
            dbg.logic.debug(
                "project.update.unlink [project:%s]: last_update_id -> %s",
                project.id,
                latest and latest.id,
            )
            project.last_update_id = latest
        return res

    @api.model
    def _prepare_description(self, project: Any) -> str:
        return self.env["ir.qweb"]._render(
            "project.project_update_default_description",
            self._prepare_update_rendering_context(project),
        )

    @dbg.timed
    @api.model
    def _prepare_update_rendering_context(self, project: Any) -> dict:
        milestones = self._get_milestone_values(project)
        profitability_values, show_profitability = project._get_profitability_values()
        dbg.logic.debug(
            "project.update._prepare_update_rendering_context [project:%s]: milestones=%s "
            "profitability=%s",
            project.id,
            milestones["show_section"],
            show_profitability,
        )
        return {
            "user": self.env.user,
            "project": project,
            "profitability": profitability_values,
            "show_profitability": show_profitability,
            "show_activities": milestones["show_section"],
            "milestones": milestones,
            "format_lang": lambda value, digits: formatLang(
                self.env, value, digits=digits
            ),
            "format_monetary": lambda value: format_amount(
                self.env, value, project.currency_id, trailing_zeroes=False
            ),
        }

    @api.model
    def _get_milestone_values(self, project: Any) -> dict:
        Milestone = self.env["project.milestone"]
        if not project.allow_milestones:
            return {
                "show_section": False,
                "list": [],
                "updated": [],
                "last_update_date": None,
                "created": [],
            }
        list_milestones = Milestone.search(
            [
                ("project_id", "=", project.id),
                "|",
                (
                    "date_deadline",
                    "<",
                    fields.Date.context_today(self) + relativedelta(years=1),
                ),
                ("date_deadline", "=", False),
            ]
        )._get_export_values_list()
        updated_milestones = self._get_last_updated_milestone(project)
        domain = Domain("project_id", "=", project.id)
        if project.last_update_id.create_date:
            domain &= Domain("create_date", ">", project.last_update_id.create_date)
        created_milestones = Milestone.search(domain)._get_export_values_list()
        return {
            "show_section": (
                (list_milestones or updated_milestones or created_milestones) and True
            )
            or False,
            "list": list_milestones,
            "updated": updated_milestones,
            "last_update_date": project.last_update_id.create_date or None,
            "created": created_milestones,
        }

    @dbg.timed
    @api.model
    def _get_last_updated_milestone(self, project: Any) -> list[dict]:
        query = """
            SELECT DISTINCT pm.id as milestone_id,
                            pm.date_deadline as date_deadline,
                            FIRST_VALUE(old_value_datetime::date) OVER w_partition as old_value,
                            pm.date_deadline as new_value
                       FROM mail_message mm
                 INNER JOIN mail_tracking_value mtv
                         ON mm.id = mtv.mail_message_id
                 INNER JOIN ir_model_fields imf
                         ON mtv.field_id = imf.id
                        AND imf.model = 'project.milestone'
                        AND imf.name = 'date_deadline'
                 INNER JOIN project_milestone pm
                         ON mm.res_id = pm.id
                      WHERE mm.model = 'project.milestone'
                        AND mm.message_type = 'notification'
                        AND pm.project_id = %(project_id)s
         """
        if project.last_update_id.create_date:
            query += "AND mm.date > %(last_update_date)s"
        query += """
                     WINDOW w_partition AS (
                             PARTITION BY pm.id
                             ORDER BY mm.date ASC
                            )
                   ORDER BY pm.date_deadline ASC;
        """
        query_params = {"project_id": project.id}
        if project.last_update_id.create_date:
            query_params["last_update_date"] = project.last_update_id.create_date
        self.env.cr.execute(query, query_params)
        results = self.env.cr.dictfetchall()
        mapped_result = {
            res["milestone_id"]: {
                "new_value": res["new_value"],
                "old_value": res["old_value"],
            }
            for res in results
        }
        milestones = self.env["project.milestone"].search(
            [("id", "in", list(mapped_result.keys()))]
        )
        return [
            {
                **milestone._get_export_values(),
                "new_value": mapped_result[milestone.id]["new_value"],
                "old_value": mapped_result[milestone.id]["old_value"],
            }
            for milestone in milestones
        ]
