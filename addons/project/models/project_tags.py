from odoo import api, fields, models
from odoo.api import DomainType
from odoo.fields import Domain
from odoo.tools import SQL

from ..tools import debug_log as dbg


class ProjectTags(models.Model):
    _name = "project.tags"
    _description = "Project Tags"
    _inherit = ["mixin.tag"]

    is_strategic = fields.Boolean(
        string="Strategic Objective",
        help="Mark this tag as representing a strategic objective for portfolio alignment.",
    )
    project_ids = fields.Many2many(
        comodel_name="project.project",
        relation="project_project_project_tags_rel",
        string="Projects",
        export_string_translation=False,
    )
    task_ids = fields.Many2many(
        comodel_name="project.task",
        string="Tasks",
        export_string_translation=False,
    )

    @api.model
    def sort_tags_by_ids(self, tag_list: list[dict], id_order: list[int]) -> list[dict]:
        tags_by_id = {tag["id"]: tag for tag in tag_list}
        return [tags_by_id[id] for id in id_order if id in tags_by_id]

    @dbg.timed
    @api.model
    def name_search(
        self,
        name: str = "",
        domain: DomainType | None = None,
        operator: str = "ilike",
        limit: int = 100,
    ) -> list[tuple[int, str]]:
        if limit is None:
            return super().name_search(name, domain, operator, limit)
        tags = self.browse()
        domain = Domain.AND(
            [self._search_display_name(operator, name), domain or Domain.TRUE]
        )
        if self.env.context.get("project_id"):
            tag_sql = SQL(
                """
                (SELECT DISTINCT project_tasks_tags.id
                FROM (
                    SELECT rel.project_tags_id AS id
                    FROM project_tags_project_task_rel AS rel
                    JOIN project_task AS task
                        ON task.id=rel.project_task_id
                        AND task.project_id=%(project_id)s
                    ORDER BY task.id DESC
                    LIMIT 1000
                ) AS project_tasks_tags
            )""",
                project_id=self.env.context["project_id"],
            )
            tags += self.search_fetch(
                Domain("id", "in", tag_sql) & domain,
                ["display_name"],
                limit=limit,
            )
        project_tag_count = len(tags)
        if len(tags) < limit:
            tags += self.search_fetch(
                Domain("id", "not in", tags.ids) & domain,
                ["display_name"],
                limit=limit - len(tags),
            )
        dbg.logic.debug(
            "project.tags.name_search %r project=%s: %d project tags first, %d total",
            name,
            self.env.context.get("project_id"),
            project_tag_count,
            len(tags),
        )
        return [(tag.id, tag.display_name) for tag in tags.sudo()]

    @api.model
    def name_create(self, name: str) -> tuple[int, str]:
        existing_tag = self.search([("name", "=ilike", name.strip())], limit=1)
        if existing_tag:
            dbg.logic.debug(
                "project.tags.name_create %r: reusing existing tag %s",
                name,
                existing_tag.id,
            )
            return existing_tag.id, existing_tag.display_name
        dbg.lifecycle.debug("project.tags.name_create %r: creating", name)
        return super().name_create(name)
