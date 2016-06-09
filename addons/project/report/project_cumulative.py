# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools


class ProjectTaskHistoryCumulative(models.Model):
    _name = 'project.task.history.cumulative'
    _inherit = 'project.task.history'
    _auto = False

    end_date = fields.Date(string='End Date')
    nbr_tasks = fields.Integer(string='# of Tasks', readonly=True)
    project_id = fields.Many2one('project.project', string='Project')

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)

        self._cr.execute(""" CREATE VIEW %s AS (
            SELECT
                history.date::varchar||'-'||history.history_id::varchar AS id,
                history.date AS end_date,
                *
            FROM (
                SELECT
                    h.id AS history_id,
                    h.date+generate_series(0, CAST((coalesce(h.end_date, DATE 'tomorrow')::date - h.date) AS integer)-1) AS date,
                    h.task_id, h.type_id, h.user_id, h.kanban_state,
                    count(h.task_id) as nbr_tasks,
                    greatest(h.remaining_hours, 1) AS remaining_hours, greatest(h.planned_hours, 1) AS planned_hours,
                    t.project_id
                FROM
                    project_task_history AS h
                    JOIN project_task AS t ON (h.task_id = t.id)
                GROUP BY
                  h.id,
                  h.task_id,
                  t.project_id

            ) AS history
        )
        """ % (self._table,))
