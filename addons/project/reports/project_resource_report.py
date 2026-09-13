from odoo import fields, models
from odoo.db.schema import drop_view_if_exists

from ..tools import debug_log as dbg
from odoo.addons.project.models.project_task import CLOSED_STATES


class ProjectResourceReport(models.Model):
    _name = "project.resource.report"
    _description = "Resource Utilization"
    _auto = False
    _order = "allocated_hours desc"

    user_id = fields.Many2one(
        comodel_name="res.users",
        readonly=True,
    )
    project_id = fields.Many2one(
        comodel_name="project.project",
        readonly=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        readonly=True,
    )
    allocated_hours = fields.Float(
        readonly=True,
        aggregator="sum",
    )
    task_count = fields.Integer(
        string="Open Tasks",
        readonly=True,
        aggregator="sum",
    )
    project_count = fields.Integer(
        string="Projects",
        readonly=True,
        aggregator="max",
    )
    is_overallocated = fields.Boolean(
        string="Overallocated",
        readonly=True,
        help="True when the user's busiest single week exceeds their working "
        "calendar's weekly capacity across all active projects "
        "(reservations are bucketed by ISO week on their start date). "
        "Falls back to 40h for a resource with no calendar.",
    )

    @dbg.timed
    def init(self) -> None:
        dbg.lifecycle.debug("project.resource.report: rebuilding view %s", self._table)
        drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                WITH reservations AS (
                    SELECT
                        res.user_id,
                        t.project_id,
                        t.company_id,
                        t.id AS task_id,
                        rr.allocated_hours,
                        COALESCE(cal.hours_per_week, 40) AS weekly_capacity,
                        DATE_TRUNC('week', rr.date_start) AS week_start
                    FROM resource_reservation rr
                    JOIN resource_resource res ON res.id = rr.resource_id
                    LEFT JOIN resource_calendar cal ON cal.id = res.calendar_id
                    JOIN project_task t
                         ON t.id = rr.res_id
                        AND rr.res_model = 'project.task'
                    WHERE t.state <> ALL(%s)
                      AND t.project_id IS NOT NULL
                      AND t.is_template IS NOT TRUE
                      AND t.active = TRUE
                      AND res.user_id IS NOT NULL
                ),
                user_project AS (
                    SELECT
                        user_id,
                        project_id,
                        company_id,
                        SUM(allocated_hours) AS allocated_hours,
                        COUNT(DISTINCT task_id) AS task_count
                    FROM reservations
                    GROUP BY user_id, project_id, company_id
                ),
                -- Peak weekly load per user: sum hours within each ISO week
                -- (by reservation start date), then take the busiest week.
                user_peak AS (
                    SELECT user_id,
                           MAX(week_hours) AS peak_week_hours,
                           MAX(weekly_capacity) AS weekly_capacity
                    FROM (
                        SELECT user_id, week_start,
                               SUM(allocated_hours) AS week_hours,
                               MAX(weekly_capacity) AS weekly_capacity
                        FROM reservations
                        WHERE week_start IS NOT NULL
                        GROUP BY user_id, week_start
                    ) w
                    GROUP BY user_id
                ),
                user_totals AS (
                    SELECT user_id, COUNT(DISTINCT project_id) AS project_count
                    FROM user_project
                    GROUP BY user_id
                )
                SELECT
                    ROW_NUMBER() OVER (ORDER BY up.user_id, up.project_id) AS id,
                    up.user_id,
                    up.project_id,
                    up.company_id,
                    up.allocated_hours,
                    up.task_count,
                    ut.project_count,
                    COALESCE(pk.peak_week_hours, 0)
                        > COALESCE(pk.weekly_capacity, 40) AS is_overallocated
                FROM user_project up
                JOIN user_totals ut ON ut.user_id = up.user_id
                LEFT JOIN user_peak pk ON pk.user_id = up.user_id
            )
            """,
            (list(CLOSED_STATES),),
        )
