# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import SQL
from odoo.addons.resource.models.utils import filter_domain_leaf


class ReportProjectTaskBurndownChart(models.AbstractModel):
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
    is_closed = fields.Selection([('closed', 'Closed tasks'), ('open', 'Open tasks')], string="Closing Stage", readonly=True)
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

    def _where_calc(self, domain, active_test=True):
        burndown_specific_domain, task_specific_domain = self._determine_domains(domain)

        main_query = super()._where_calc(burndown_specific_domain, active_test)

        # Build the query on `project.task` with the domain fields that are linked to that model. This is done in order
        # to be able to reduce the number of treated records in the query by limiting them to the one corresponding to
        # the ids that are returned from this sub query.
        project_task_query = self.env['project.task']._where_calc(task_specific_domain)
        self.env.flush_query(project_task_query.subselect())

        # Get the stage_id `ir.model.fields`'s id in order to inject it directly in the query and avoid having to join
        # on `ir_model_fields` table.
        IrModelFieldsSudo = self.env['ir.model.fields'].sudo()
        field_id = IrModelFieldsSudo.search([('name', '=', 'stage_id'), ('model', '=', 'project.task')]).id

        groupby = self.env.context['project_task_burndown_chart_report_groupby']
        date_groupby = [g for g in groupby if g.startswith('date')][0]

        # Computes the interval which needs to be used in the `SQL` depending on the date group by interval.
        interval = date_groupby.split(':')[1]
        sql_interval = '1 %s' % interval if interval != 'quarter' else '3 month'

        simple_date_groupby_sql = self._read_group_groupby(f"date:{interval}", main_query)
        # Removing unexistant table name from the expression
        simple_date_groupby_sql = self.env.cr.mogrify(simple_date_groupby_sql).decode()
        simple_date_groupby_sql = simple_date_groupby_sql.replace('"project_task_burndown_chart_report".', '')

        burndown_chart_sql = SQL("""
            (
              WITH task_ids AS %(task_query_subselect)s,
              all_stage_task_moves AS (
                 SELECT count(*) as __count,
                        sum(allocated_hours) as allocated_hours,
                        project_id,
                        %(date_begin)s as date_begin,
                        %(date_end)s as date_end,
                        stage_id,
                        is_closed
                   FROM (
                            -- Gathers the stage_ids history per task_id. This query gets:
                            -- * All changes except the last one for those for which we have at least a mail
                            --   message and a mail tracking value on project.task stage_id.
                            -- * The stage at creation for those for which we do not have any mail message and a
                            --   mail tracking value on project.task stage_id.
                            SELECT DISTINCT task_id,
                                   allocated_hours,
                                   project_id,
                                   %(date_begin)s as date_begin,
                                   %(date_end)s as date_end,
                                   first_value(stage_id) OVER task_date_begin_window AS stage_id,
                                   is_closed
                              FROM (
                                     SELECT pt.id as task_id,
                                            pt.allocated_hours,
                                            pt.project_id,
                                            COALESCE(LAG(mm.date) OVER (PARTITION BY mm.res_id ORDER BY mm.id), pt.create_date) as date_begin,
                                            CASE WHEN mtv.id IS NOT NULL THEN mm.date
                                                ELSE (now() at time zone 'utc')::date + INTERVAL '%(interval)s'
                                            END as date_end,
                                            CASE WHEN mtv.id IS NOT NULL THEN mtv.old_value_integer
                                               ELSE pt.stage_id
                                            END as stage_id,
                                            CASE
                                                WHEN mtv.id IS NOT NULL AND mtv.old_value_char IN ('1_done', '1_canceled') THEN 'closed'
                                                WHEN mtv.id IS NOT NULL AND mtv.old_value_char NOT IN ('1_done', '1_canceled') THEN 'open'
                                                WHEN mtv.id IS NULL AND pt.state IN ('1_done', '1_canceled') THEN 'closed'
                                                ELSE 'open'
                                            END as is_closed
                                       FROM project_task pt
                                                LEFT JOIN (
                                                    mail_message mm
                                                        JOIN mail_tracking_value mtv ON mm.id = mtv.mail_message_id
                                                                                     AND mtv.field_id = %(field_id)s
                                                                                     AND mm.model='project.task'
                                                                                     AND mm.message_type = 'notification'
                                                        JOIN project_task_type ptt ON ptt.id = mtv.old_value_integer
                                                ) ON mm.res_id = pt.id
                                      WHERE pt.active=true AND pt.id IN (SELECT id from task_ids)
                                   ) task_stage_id_history
                          GROUP BY task_id,
                                   allocated_hours,
                                   project_id,
                                   %(date_begin)s,
                                   %(date_end)s,
                                   stage_id,
                                   is_closed
                            WINDOW task_date_begin_window AS (PARTITION BY task_id, %(date_begin)s)
                          UNION ALL
                            -- Gathers the current stage_ids per task_id for those which values changed at least
                            -- once (=those for which we have at least a mail message and a mail tracking value
                            -- on project.task stage_id).
                            SELECT pt.id as task_id,
                                   pt.allocated_hours,
                                   pt.project_id,
                                   last_stage_id_change_mail_message.date as date_begin,
                                   (now() at time zone 'utc')::date + INTERVAL '%(interval)s' as date_end,
                                   pt.stage_id as old_value_integer,
                                   CASE WHEN pt.state IN ('1_done', '1_canceled') THEN 'closed'
                                       ELSE 'open'
                                   END as is_closed
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
                                   ) AS last_stage_id_change_mail_message ON TRUE
                             WHERE pt.active=true AND pt.id IN (SELECT id from task_ids)
                        ) AS project_task_burndown_chart
               GROUP BY allocated_hours,
                        project_id,
                        %(date_begin)s,
                        %(date_end)s,
                        stage_id,
                        is_closed
              )
              SELECT (project_id*10^13 + stage_id*10^7 + to_char(date, 'YYMMDD')::integer)::bigint as id,
                     allocated_hours,
                     project_id,
                     stage_id,
                     is_closed,
                     date,
                     __count
                FROM all_stage_task_moves t
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

        # hardcode 'project_task_burndown_chart_report' as the query above
        # (with its own parameters)
        main_query._tables['project_task_burndown_chart_report'] = burndown_chart_sql

        return main_query

    @api.model
    def _validate_group_by(self, groupby):
        """ Check that the both `date` and `stage_id` are part of `group_by`, otherwise raise a `UserError`.

        :param groupby: List of group by fields.
        """

        is_closed_or_stage_in_groupby = False
        date_in_groupby = False
        for gb in groupby:
            if gb.startswith('date'):
                date_in_groupby = True
            elif gb in ['stage_id', 'is_closed']:
                is_closed_or_stage_in_groupby = True

        if not date_in_groupby or not is_closed_or_stage_in_groupby:
            raise UserError(_('The view must be grouped by date and by Stage - Burndown chart or Is Closed - Burnup chart'))

    @api.model
    def _determine_domains(self, domain):
        """ Compute two separated domain from the provided one:
        * A domain that only contains fields that are specific to `project.task.burndown.chart.report`
        * A domain that only contains fields that are specific to `project.task`

        See `filter_domain_leaf` for more details on the new domains.

        :param domain: The domain that has been passed to the read_group.
        :return: A tuple containing the non `project.task` specific domain and the `project.task` specific domain.
        """
        burndown_chart_specific_fields = list(set(self._fields) - set(self.task_specific_fields))
        task_specific_domain = filter_domain_leaf(domain, lambda field: field not in burndown_chart_specific_fields)
        non_task_specific_domain = filter_domain_leaf(domain, lambda field: field not in self.task_specific_fields)
        return non_task_specific_domain, task_specific_domain

    def _read_group_select(self, aggregate_spec, query):
        if aggregate_spec == '__count':
            return SQL("SUM(%s)", SQL.identifier(self._table, '__count'))
        return super()._read_group_select(aggregate_spec, query)

    def _read_group(self, domain, groupby=(), aggregates=(), having=(), offset=0, limit=None, order=None):
        self._validate_group_by(groupby)
        self = self.with_context(project_task_burndown_chart_report_groupby=groupby)

        return super()._read_group(
            domain=domain, groupby=groupby, aggregates=aggregates,
            having=having, offset=offset, limit=limit, order=order,
        )
