# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools


class ProjectTaskHistoryCumulative(models.Model):
    _name = 'project.task.history.cumulative'
    _auto = False

    end_date = fields.Date(string='End Date', compute=None, readonly=True)
    nbr_tasks = fields.Integer(string='# of Tasks', readonly=True)
    project_id = fields.Many2one('project.project', string='Project')
    task_id = fields.Many2one('project.task', string='Task', ondelete='cascade', required=True, index=True)
    type_id = fields.Many2one('project.task.type', string='Stage')
    kanban_state = fields.Selection([
        ('normal', 'Normal'),
        ('blocked', 'Blocked'),
        ('done', 'Ready for next stage')
        ], string='Kanban State')
    date = fields.Date(string='Date', index=True, default=fields.Date.context_today)
    remaining_hours = fields.Float(string='Remaining Time', digits=(16, 2))
    planned_hours = fields.Float(string='Planned Time', digits=(16, 2))
    user_id = fields.Many2one('res.users', string='Responsible')

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
