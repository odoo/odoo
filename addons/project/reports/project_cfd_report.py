from typing import Any

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import SQL

from ..tools import debug_log as dbg
from odoo.addons.resource.models.utils import filter_domain_leaf


class ProjectCFDReport(models.AbstractModel):
    _name = "project.cfd.report"
    _description = "Cumulative Flow Diagram"
    _auto = False
    _order = "date"
    _search_visibility_fields = ()

    date = fields.Datetime(readonly=True)
    date_assign = fields.Datetime(
        string="Assignment Date",
        readonly=True,
    )
    date_end = fields.Date(
        string="Deadline",
        readonly=True,
    )
    date_last_status_change = fields.Date(
        string="Last Status Change",
        readonly=True,
    )
    state = fields.Selection(
        selection=[
            ("todo", "To Do"),
            ("in_progress", "In Progress"),
            ("changes_requested", "Changes Requested"),
            ("approved", "Approved"),
            ("done", "Done"),
            ("canceled", "Cancelled"),
            ("blocked", "Waiting"),
        ],
        readonly=True,
    )
    milestone_id = fields.Many2one(
        comodel_name="project.milestone",
        readonly=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Customer",
        readonly=True,
    )
    project_id = fields.Many2one(
        comodel_name="project.project",
        readonly=True,
    )
    step_id = fields.Many2one(
        comodel_name="project.workflow.step",
        readonly=True,
    )
    task_count = fields.Integer(readonly=True)
    tag_ids = fields.Many2many(
        comodel_name="project.tags",
        relation="project_tags_project_task_rel",
        column1="project_task_id",
        column2="project_tags_id",
        string="Tags",
        readonly=True,
    )
    user_ids = fields.Many2many(
        comodel_name="res.users",
        relation="project_task_user_rel",
        column1="task_id",
        column2="user_id",
        string="Assignees",
        readonly=True,
    )

    @property
    def task_specific_fields(self) -> list[str]:
        return [
            "date_assign",
            "date_end",
            "date_last_status_change",
            "state",
            "milestone_id",
            "partner_id",
            "project_id",
            "step_id",
            "tag_ids",
            "user_ids",
        ]

    @dbg.timed
    @api.model
    def _search(
        self,
        domain: list,
        offset: int = 0,
        limit: int | None = None,
        order: str | None = None,
        **kwargs: Any,
    ) -> Any:
        cfd_specific_domain, task_specific_domain = self._get_domains_report_and_task(
            domain
        )
        main_query = super()._search(
            cfd_specific_domain,
            offset=offset,
            limit=limit,
            order=order,
            **kwargs,
        )

        project_task_query = self.env["project.task"]._search(
            task_specific_domain, **kwargs
        )
        dbg.pipeline.debug(
            "[report:project_cfd_report] _search: report domain=%s task domain=%s",
            cfd_specific_domain,
            task_specific_domain,
        )
        self.env.flush_query(project_task_query.subselect())

        field_id = (
            self.sudo()
            .env["ir.model.fields"]
            .search([("name", "=", "step_id"), ("model", "=", "project.task")])
            .id
        )

        groupby = self.env.context.get(
            "project_cfd_report_groupby",
            ["date:month", "step_id"],
        )
        date_groupby = next(g for g in groupby if g.startswith("date"))

        interval = date_groupby.split(":")[1] if ":" in date_groupby else "month"
        sql_interval = "1 %s" % interval if interval != "quarter" else "3 month"
        dbg.logic.debug(
            "[report:project_cfd_report] groupby=%s -> interval %r (series step %r)",
            groupby,
            interval,
            sql_interval,
        )

        simple_date_groupby_sql = self._read_group_groupby(
            "project_cfd_report",
            f"date:{interval}",
            main_query,
        )
        simple_date_groupby_sql = simple_date_groupby_sql.render()
        simple_date_groupby_sql = simple_date_groupby_sql.replace(
            '"project_cfd_report".', ""
        )

        cfd_sql = SQL(
            """
            (
              WITH task_ids AS %(task_query_subselect)s,
              all_step_task_moves AS (
                 SELECT count(*) as __count,
                        project_id,
                        %(date_begin)s as date_begin,
                        %(date_end)s as date_end,
                        step_id
                   FROM (
                            SELECT DISTINCT task_id,
                                   project_id,
                                   %(date_begin)s as date_begin,
                                   %(date_end)s as date_end,
                                   first_value(step_id) OVER task_date_begin_window AS step_id
                              FROM (
                                     SELECT pt.id as task_id,
                                            pt.project_id,
                                            COALESCE(LAG(mm.date) OVER (PARTITION BY mm.res_id ORDER BY mm.id), pt.create_date) as date_begin,
                                            CASE WHEN mtv.id IS NOT NULL THEN mm.date
                                                ELSE (now() at time zone 'utc')::date + INTERVAL '%(interval)s'
                                            END as date_end,
                                            CASE WHEN mtv.id IS NOT NULL THEN mtv.old_value_integer
                                               ELSE pt.step_id
                                            END as step_id
                                       FROM project_task pt
                                                LEFT JOIN (
                                                    mail_message mm
                                                        JOIN mail_tracking_value mtv ON mm.id = mtv.mail_message_id
                                                                                     AND mtv.field_id = %(field_id)s
                                                                                     AND mm.model='project.task'
                                                                                     AND mm.message_type = 'notification'
                                                        JOIN project_workflow_step pws ON pws.id = mtv.old_value_integer
                                                ) ON mm.res_id = pt.id
                                      WHERE pt.active=true AND pt.id IN (SELECT id from task_ids)
                                   ) task_step_id_history
                          GROUP BY task_id,
                                   project_id,
                                   %(date_begin)s,
                                   %(date_end)s,
                                   step_id
                            WINDOW task_date_begin_window AS (PARTITION BY task_id, %(date_begin)s)
                          UNION ALL
                            SELECT pt.id as task_id,
                                   pt.project_id,
                                   last_step_id_change_mail_message.date as date_begin,
                                   (now() at time zone 'utc')::date + INTERVAL '%(interval)s' as date_end,
                                   pt.step_id as old_value_integer
                              FROM project_task pt
                                   JOIN LATERAL (
                                       SELECT mm.date
                                       FROM mail_message mm
                                       JOIN mail_tracking_value mtv ON mm.id = mtv.mail_message_id
                                       AND mtv.field_id = %(field_id)s
                                       AND mm.model='project.task'
                                       AND mm.message_type = 'notification'
                                       AND mm.res_id = pt.id
                                       ORDER BY mm.id DESC
                                       FETCH FIRST ROW ONLY
                                   ) AS last_step_id_change_mail_message ON TRUE
                             WHERE pt.active=true AND pt.id IN (SELECT id from task_ids)
                        ) AS project_task_cfd_chart
               GROUP BY project_id,
                        %(date_begin)s,
                        %(date_end)s,
                        step_id
              )
              -- row_number(), not arithmetic on the grouping keys. The old
              -- expression was not a key twice over: `^` is float8
              -- exponentiation in Postgres, so project_id*10^13 passes 2^53 at
              -- project_id 901 and consecutive days collapsed onto one id
              -- (measured: 7 distinct ids for 14 distinct dates at 950); and
              -- all_step_task_moves also groups by planned_hours and
              -- date_closed, so two tasks in one (project, step) already
              -- collided at any id. Nothing consumed the id -- both views are
              -- graph-only with disable_linking -- so nothing was broken, but a
              -- model whose id is not a key is a trap for whoever adds a list.
              SELECT row_number() OVER ()::bigint as id,
                     project_id,
                     step_id,
                     date,
                     __count as task_count
                FROM all_step_task_moves t
                         JOIN LATERAL generate_series(t.date_begin, t.date_end-INTERVAL '1 day', '%(interval)s')
                            AS date ON TRUE
            )
            """,
            task_query_subselect=project_task_query.subselect(),
            date_begin=SQL(simple_date_groupby_sql.replace('"date"', '"date_begin"')),
            date_end=SQL(simple_date_groupby_sql.replace('"date"', '"date_end"')),
            interval=SQL(sql_interval),
            field_id=field_id,
        )

        main_query._tables["project_cfd_report"] = cfd_sql
        return main_query

    @api.model
    def _check_group_by(self, groupby: list[str]) -> None:
        date_in_groupby = False
        step_in_groupby = False
        for gb in groupby:
            if gb.startswith("date"):
                date_in_groupby = True
            elif gb == "step_id":
                step_in_groupby = True

        if not date_in_groupby or not step_in_groupby:
            raise UserError(
                _(
                    "The Cumulative Flow Diagram must be grouped by date"
                    " and by Workflow Step."
                )
            )

    @api.model
    def _get_domains_report_and_task(self, domain: list) -> tuple[list, list]:
        cfd_specific_fields = list(set(self._fields) - set(self.task_specific_fields))
        task_specific_domain = filter_domain_leaf(
            domain, lambda field: field not in cfd_specific_fields
        )
        non_task_specific_domain = filter_domain_leaf(
            domain, lambda field: field not in self.task_specific_fields
        )
        return non_task_specific_domain, task_specific_domain

    def _read_group_select(self, aggregate_spec: str, query: Any) -> SQL:
        if aggregate_spec == "task_count:sum":
            return SQL("SUM(%s)", SQL.identifier(self._table, "task_count"))
        if aggregate_spec == "__count":
            return SQL("SUM(%s)", SQL.identifier(self._table, "task_count"))
        return super()._read_group_select(aggregate_spec, query)

    @dbg.timed
    def _read_group(
        self,
        domain: list,
        groupby: tuple | list = (),
        aggregates: tuple | list = (),
        having: tuple | list = (),
        offset: int = 0,
        limit: int | None = None,
        order: str | None = None,
    ) -> list:
        self._check_group_by(groupby)
        dbg.pipeline.debug(
            "[report:project_cfd_report] _read_group: domain=%s groupby=%s aggregates=%s",
            domain,
            list(groupby),
            list(aggregates),
        )
        self = self.with_context(project_cfd_report_groupby=groupby)

        return super()._read_group(
            domain=domain,
            groupby=groupby,
            aggregates=aggregates,
            having=having,
            offset=offset,
            limit=limit,
            order=order,
        )
