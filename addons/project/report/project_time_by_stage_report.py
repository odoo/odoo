from odoo import fields, models, tools
from odoo.tools import SQL


class ReportProjectTaskStage(models.Model):
    _name = "project.task.stage.report"
    _description = "Task time spent per stage"
    _auto = False
    _order = "sequence desc"

    name = fields.Char(string="Task Title", readonly=True)
    user_ids = fields.Many2many("res.users", related="task_id.user_ids", string="Assignees", readonly=True)
    tag_ids = fields.Many2many("project.tags", related="task_id.tag_ids", string="Tags", readonly=True)
    milestone_id = fields.Many2one("project.milestone", readonly=True)
    company_id = fields.Many2one("res.company", string="Company", readonly=True)
    partner_id = fields.Many2one("res.partner", string="Customer", readonly=True)
    create_date = fields.Datetime("Create Date", readonly=True)
    date_deadline = fields.Datetime(string="Deadline", readonly=True)
    date_last_stage_update = fields.Datetime(string="Last Stage Update", readonly=True)
    is_closed = fields.Boolean(string="Closed state", readonly=True)
    priority = fields.Selection(
        [
            ("0", "Low priority"),
            ("1", "Medium priority"),
            ("2", "High priority"),
            ("3", "Urgent"),
        ],
        readonly=True,
        string="Priority",
    )
    task_id = fields.Many2one("project.task", string="Task", readonly=True)
    project_id = fields.Many2one("project.project", string="Project", readonly=True)
    stage_id = fields.Many2one("project.task.type", string="Stage", readonly=True)
    sequence = fields.Integer(string="Sequence", readonly=True)
    time_spent = fields.Float(string="Time Spent", readonly=True, aggregator="avg")
    task_properties = fields.Properties(
        "Properties",
        definition="project_id.task_properties_definition",
    )

    def _select(self) -> SQL:
        return SQL("""
            row_number() OVER () AS id,
            t.name,
            t.milestone_id,
            t.company_id,
            t.partner_id,
            t.create_date,
            t.date_deadline,
            t.date_last_stage_update,
            CASE WHEN t.state IN ('1_done', '1_canceled') THEN True ELSE False END AS is_closed,
            t.priority,
            t.id AS task_id,
            t.project_id,
            s.id AS stage_id,
            (step.duration::float / 60) AS time_spent,
            t.task_properties,
            s.sequence
        """)

    def _from(self) -> SQL:
        return SQL("""
            project_task t
            CROSS JOIN LATERAL jsonb_each(
                (t.duration_tracking - 'd' - 's') || jsonb_build_object(t.duration_tracking->>'s',
                    (EXTRACT(EPOCH FROM (timezone('UTC', now()) - (t.duration_tracking->>'d')::timestamp)) / 60)::int + coalesce(t.duration_tracking->>(t.duration_tracking->>'s'), '0')::int
                )
            ) AS step(stage_id, duration)
            LEFT JOIN project_task_type s ON s.id = step.stage_id::int
        """)

    def _where(self) -> SQL:
        return SQL("""
            t.project_id IS NOT NULL
        """)

    def _group_by(self) -> SQL:
        return SQL("""
            t.id,
            t.name,
            t.milestone_id,
            t.company_id,
            t.partner_id,
            t.create_date,
            t.date_deadline,
            t.date_last_stage_update,
            t.priority,
            s.id,
            step.duration
        """)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.execute_query(SQL(
            """
            CREATE VIEW %s AS
                 SELECT %s
                   FROM %s
                  WHERE %s
               GROUP BY %s
            """,
            SQL.identifier(self._table),
            self._select(),
            self._from(),
            self._where(),
            self._group_by(),
        ))
