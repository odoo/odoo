# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import SQL

from odoo.addons.resource.models.utils import filter_map_domain


class ProjectTaskBurndownChartReport(models.AbstractModel):
    _name = 'project.task.burndown.chart.report'
    _description = 'Burndown Chart'
    _auto = False
    _order = 'date'

    allocated_hours = fields.Float(string='Allocated Time', readonly=True)
    date = fields.Datetime('Date', readonly=True)
    date_assign = fields.Datetime(string='Assignment Date', readonly=True)
    date_deadline = fields.Date(string='Deadline', readonly=True)
    date_last_stage_update = fields.Date(string='Last Stage Update', readonly=True)
    state = fields.Selection([
        ('01_in_progress', 'In Progress'),
        ('1_done', 'Done'),
        ('04_waiting_normal', 'Waiting'),
        ('03_approved', 'Approved'),
        ('1_canceled', 'Cancelled'),
        ('02_changes_requested', 'Changes Requested'),
    ], string='State', readonly=True)
    is_open = fields.Boolean(string='Open', readonly=True)
    is_done = fields.Boolean(string='Done', readonly=True)
    is_canceled = fields.Boolean(string='Cancelled', readonly=True)
    milestone_id = fields.Many2one('project.milestone', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True)
    project_id = fields.Many2one('project.project', readonly=True)
    stage_id = fields.Many2one('project.task.type', readonly=True)
    tag_ids = fields.Many2many('project.tags', relation='project_tags_project_task_rel',
                               column1='project_task_id', column2='project_tags_id',
                               string='Tags', readonly=True)
    user_ids = fields.Many2many('res.users', relation='project_task_user_rel', column1='task_id', column2='user_id',
                                string='Assignees', readonly=True)

    # This variable is used in order to distinguish conditions that can be set on `project.task` and thus being used
    # at a lower level than the "usual" query made by the `read_group_raw`. Indeed, the domain applied on those fields
    # will be performed on a `CTE` that will be later use in the `SQL` in order to limit the subset of data that is used
    # in the successive `GROUP BY` statements.
    @property
    def task_specific_fields(self):
        return [
            'date_assign',
            'date_deadline',
            'date_last_stage_update',
            'state',
            'milestone_id',
            'partner_id',
            'project_id',
            'stage_id',
            'tag_ids',
            'user_ids',
        ]

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, **kwargs):
        burndown_specific_domain, task_specific_domain = self._determine_domains(domain)
        main_query = super()._search(
            burndown_specific_domain, offset=offset, limit=limit, order=order, **kwargs)

        # Build the query on `project.task` with the domain fields that are linked to that model. This is done in order
        # to be able to reduce the number of treated records in the query by limiting them to the one corresponding to
        # the ids that are returned from this sub query.
        project_task_query = self.env['project.task']._search(task_specific_domain, **kwargs)

        burndown_chart_sql = SQL("""
        (
         WITH task_ids AS %(task_query_subselect)s,
             project_task_tracking AS (
                SELECT
                       t.id,
                       now() - (SUM(step.duration::int) OVER (PARTITION BY t.id ORDER BY s.sequence desc)) * interval '1 second' as date,
                       s.id as stage_id,
                       t.allocated_hours as hours,
                       s.sequence
                  FROM project_task t
            CROSS JOIN lateral jsonb_each(
                       (t.duration_tracking - 'd' - 's') || jsonb_build_object(t.duration_tracking->>'s',
                        EXTRACT(EPOCH FROM (now() - (t.duration_tracking->>'d')::timestamptz))::int + coalesce(t.duration_tracking->>(t.duration_tracking->>'s'), '0')::int
                       )) AS step(stage_id, duration)
             LEFT JOIN project_task_type s ON s.id=step.stage_id::int
                 WHERE t.active=true AND t.id IN (SELECT id from task_ids)
        ), project_task_tracking_by_end AS (
                SELECT
                       id,
                       date,
                       stage_id,
                       1 as count,
                       hours
                  FROM project_task_tracking
            UNION
                SELECT
                       id,
                       date,
                       LAG(stage_id) OVER (PARTITION BY id ORDER BY sequence) AS stage_id,
                       -1 as count,
                       hours * -1
                FROM project_task_tracking
        )
        SELECT ptt.id,
               ptt.date,
               ptt.stage_id,
               ptt.count as __count,
               ptt.hours as allocated_hours,
               CASE WHEN t.state = '1_done' THEN true ELSE false END as is_done,
               CASE WHEN t.state = '1_canceled' THEN true ELSE false END as is_canceled,
               CASE WHEN t.state NOT IN ('1_done', '1_canceled') THEN true ELSE false END as is_open,
               t.project_id
        FROM project_task_tracking_by_end ptt
        JOIN project_task t ON t.id = ptt.id
         WHERE ptt.stage_id IS NOT NULL
      ORDER BY ptt.id, ptt.stage_id, ptt.date
      )""", task_query_subselect=project_task_query.subselect())

        # hardcode 'project_task_burndown_chart_report' as the query above
        # (with its own parameters)
        main_query._joins['project_task_burndown_chart_report'] = (SQL(), burndown_chart_sql, SQL())

        return main_query

    @api.model
    def _validate_group_by(self, groupby):
        """ Check that the both `date` and `stage_id` are part of `group_by`, otherwise raise a `UserError`.

        :param groupby: List of group by fields.
        """

        stage_in_groupby = False
        date_in_groupby = False
        for gb in groupby:
            if gb.startswith('date'):
                date_in_groupby = True
            elif gb == 'stage_id':
                stage_in_groupby = True

        if not date_in_groupby or not stage_in_groupby:
            raise UserError(_('The view must be grouped by date and by Stage - Burndown chart'))

    @api.model
    def _determine_domains(self, domain):
        """ Compute two separated domain from the provided one:
        * A domain that only contains fields that are specific to `project.task.burndown.chart.report`
        * A domain that only contains fields that are specific to `project.task`

        See `filter_map_domain` for more details on the new domains.

        :param domain: The domain that has been passed to the read_group.
        :return: A tuple containing the non `project.task` specific domain and the `project.task` specific domain.
        """
        burndown_chart_specific_fields = list(set(self._fields) - set(self.task_specific_fields))
        task_specific_domain = filter_map_domain(
            domain,
            lambda condition: (
                None
                if condition.field_expr in burndown_chart_specific_fields
                else condition
            ),
        )
        non_task_specific_domain = filter_map_domain(
            domain,
            lambda condition: (
                None
                if condition.field_expr in self.task_specific_fields
                else condition
            ),
        )
        return non_task_specific_domain, task_specific_domain

    def _read_group_select(self, table, aggregate_spec):
        if aggregate_spec == '__count':
            return SQL("SUM(%s)", SQL.identifier(self._table, '__count'))
        return super()._read_group_select(table, aggregate_spec)

    def _read_group(self, domain, groupby=(), aggregates=(), having=(), offset=0, limit=None, order=None):
        self._validate_group_by(groupby)

        return super()._read_group(
            domain=domain, groupby=groupby, aggregates=aggregates,
            having=having, offset=offset, limit=limit, order=order,
        )
