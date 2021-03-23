# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from psycopg2 import sql

from odoo import api, fields, models, tools
from odoo.osv import expression
from odoo.tools import OrderedSet


class ReportProjectTaskBurndownChart(models.Model):
    _name = 'project.task.burndown.chart.report'
    _description = 'Burndown Chart'
    _auto = False
    _order = 'date'

    project_id = fields.Many2one('project.project', readonly=True)
    display_project_id = fields.Many2one('project.project', readonly=True)
    stage_id = fields.Many2one('project.task.type', readonly=True)
    date = fields.Datetime('Date', readonly=True)
    user_id = fields.Many2one('res.users', string='Assigned to', readonly=True)
    date_assign = fields.Datetime(string='Assignment Date', readonly=True)
    date_deadline = fields.Date(string='Deadline', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True)
    nb_tasks = fields.Integer('# of Tasks', readonly=True, group_operator="sum")
    date_group_by = fields.Selection(
        (
            ('day', 'By Day'),
            ('month', 'By Month'),
            ('quarter', 'By quarter'),
            ('year', 'By Year')
        ), string="Date Group By", readonly=True)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        date_group_bys = []
        groupby = [groupby] if isinstance(groupby, str) else list(OrderedSet(groupby))
        for gb in groupby:
            if gb.startswith('date:'):
                date_group_bys.append(gb.split(':')[-1])

        date_domains = []
        for gb in date_group_bys:
            date_domains = expression.OR([date_domains, [('date_group_by', '=', gb)]])
        domain = expression.AND([domain, date_domains])

        res = super().read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        return res

    def init(self):
        query = """
            WITH change_stage_tracking AS (
                SELECT mm.id as id,
                       pt.id as task_id,
                       pt.project_id,
                       pt.display_project_id,
                       pt.create_date as date_begin,
                       mm.date as date_end,
                       current_stage.id as stage_id,
                       next_stage.id as next_stage_id,
                       pt.user_id,
                       pt.date_assign,
                       pt.date_deadline,
                       pt.partner_id
                  FROM mail_message mm
            INNER JOIN mail_tracking_value mtv
                    ON mm.id = mtv.mail_message_id
            INNER JOIN ir_model_fields imf
                    ON mtv.field = imf.id
                   AND imf.model = 'project.task'
            INNER JOIN project_task_type current_stage
                    ON mtv.old_value_integer = current_stage.id
            INNER JOIN project_task_type next_stage
                    ON mtv.new_value_integer = next_stage.id
            INNER JOIN project_task pt
                    ON mm.res_id = pt.id
                 WHERE mm.model = 'project.task'
                   AND mm.message_type = 'notification'
                   AND pt.active
            ),
            all_stage_changes AS (
                SELECT current_change.id,
                        current_change.task_id,
                        current_change.project_id,
                        current_change.display_project_id,
                        CASE WHEN previous_change.id IS NULL THEN current_change.date_begin ELSE previous_change.date_end END as date_begin,
                        current_change.date_end,
                        current_change.stage_id,
                        current_change.next_stage_id,
                        current_change.user_id,
                        current_change.date_assign,
                        current_change.date_deadline,
                        current_change.partner_id
                   FROM change_stage_tracking current_change
              LEFT JOIN change_stage_tracking previous_change
                     ON previous_change.next_stage_id = current_change.stage_id
                    AND previous_change.task_id = current_change.task_id
            ),
            all_moves_stage_task AS (
                SELECT pt.id AS task_id,
                       pt.project_id,
                       pt.display_project_id,
                       pt.stage_id,
                       CASE WHEN last_change.id IS NULL THEN pt.create_date ELSE last_change.date_end END AS date_begin,
                       (CURRENT_DATE + interval '1 year')::date AS date_end,
                       pt.user_id,
                       pt.date_assign,
                       pt.date_deadline,
                       pt.partner_id
                  FROM project_task pt
             LEFT JOIN all_stage_changes last_change
                    ON pt.id = last_change.task_id
                   AND pt.stage_id = last_change.next_stage_id
                 UNION
                    SELECT task_id,
                           project_id,
                           display_project_id,
                           stage_id,
                           date_begin,
                           date_end,
                           user_id,
                           date_assign,
                           date_deadline,
                           partner_id
                      FROM all_stage_changes
            ),
            all_moves_by_day AS (
                SELECT project_id,
                       display_project_id,
                       stage_id,
                       date_begin,
                       date_end,
                       d as date,
                       date_trunc('month', d) AS date_month,
                       date_trunc('week', d) AS date_week,
                       date_trunc('year', d) + CAST((extract(quarter from d) - 1) * 3 || ' months' AS interval) AS date_quarter,
                       date_trunc('year', d) AS date_year,
                       task_id,
                       user_id,
                       date_assign,
                       date_deadline,
                       partner_id
                  FROM all_moves_stage_task
            CROSS JOIN generate_series(
                    (
                        SELECT date_trunc('day', min(create_date))
                          FROM project_task
                         WHERE active
                    ),
                    (CURRENT_DATE + interval '1 day')::date,
                    '1 day'
                ) d
                WHERE date_begin <= d
                  AND date_end > d
            ),
            burndown_chart AS (
                SELECT DISTINCT project_id,
                       display_project_id,
                       stage_id,
                       date,
                       user_id,
                       date_assign,
                       date_deadline,
                       partner_id,
                       'day' AS group_by,
                       task_id
                  FROM all_moves_by_day
                 WHERE date_begin <= date
                   AND date_end > date
             UNION ALL
                    SELECT DISTINCT project_id,
                           display_project_id,
                           stage_id,
                           date_week AS date,
                           user_id,
                           date_assign,
                           date_deadline,
                           partner_id,
                           'week' AS group_by,
                           task_id
                      FROM all_moves_by_day
                     WHERE date_trunc('week', date_begin) <= date_week
                       AND date_trunc('week', date_end) > date_week
                 UNION ALL
                    SELECT DISTINCT project_id,
                           display_project_id,
                           stage_id,
                           date_month AS date,
                           user_id,
                           date_assign,
                           date_deadline,
                           partner_id,
                           'month' AS group_by,
                           task_id
                      FROM all_moves_by_day
                     WHERE date_trunc('month', date_begin) <= date_month
                       AND date_trunc('month', date_end) > date_month
                 UNION ALL
                    SELECT DISTINCT project_id,
                           display_project_id,
                           stage_id,
                           date_quarter AS date,
                           user_id,
                           date_assign,
                           date_deadline,
                           partner_id,
                           'quarter' AS group_by,
                           task_id
                      FROM all_moves_by_day
                     WHERE date_trunc('month', date_begin) <= date_quarter
                       AND date_trunc('month', date_end) > date_quarter
                 UNION ALL
                    SELECT DISTINCT project_id,
                           display_project_id,
                           stage_id,
                           date_year AS date,
                           user_id,
                           date_assign,
                           date_deadline,
                           partner_id,
                           'year' AS group_by,
                           task_id
                      FROM all_moves_by_day
                     WHERE date_trunc('year', date_begin) <= date_year
                       AND date_trunc('year', date_end) > date_year
            )
            SELECT row_number() OVER  (
                    ORDER BY project_id,
                             display_project_id,
                             stage_id,
                             date,
                             user_id,
                             date_assign,
                             date_deadline,
                             partner_id,
                             group_by
                   ) AS id,
                   project_id,
                   display_project_id,
                   stage_id,
                   date,
                   user_id,
                   date_assign,
                   date_deadline,
                   partner_id,
                   group_by AS date_group_by,
                   1 AS nb_tasks
              FROM burndown_chart
        """

        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            sql.SQL("CREATE or REPLACE VIEW {} as ({})").format(
                sql.Identifier(self._table),
                sql.SQL(query)
            )
        )
