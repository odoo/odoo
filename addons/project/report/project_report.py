# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools


class ReportProjectTaskUser(models.Model):
    _name = "report.project.task.user"
    _description = "Tasks by user and project"
    _order = 'name desc, project_id'
    _auto = False

    name = fields.Char(string='Task Title', readonly=True)
    user_id = fields.Many2one('res.users', string='Assigned To', readonly=True)
    date_start = fields.Datetime(string='Assignation Date', readonly=True)
    date_end = fields.Datetime(string='Ending Date', readonly=True)
    date_deadline = fields.Date(string='Deadline', readonly=True)
    date_last_stage_update = fields.Datetime(string='Last Stage Update', readonly=True)
    project_id = fields.Many2one('project.project', string='Project', readonly=True)
    working_days_close = fields.Float(string='# Working Days to Close',
        digits=(16,2), readonly=True, group_operator="avg",
        help="Number of Working Days to close the task")
    working_days_open = fields.Float(string='# Working Days to Assign',
        digits=(16,2), readonly=True, group_operator="avg",
        help="Number of Working Days to Open the task")
    delay_endings_days = fields.Float(string='# Days to Deadline', digits=(16,2), readonly=True)
    nbr = fields.Integer('# of Tasks', readonly=True)  # TDE FIXME master: rename into nbr_tasks
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High')
        ], size=1, readonly=True, string="Priority")
    state = fields.Selection([
            ('normal', 'In Progress'),
            ('blocked', 'Blocked'),
            ('done', 'Ready for next stage')
        ], string='Kanban State', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True)
    stage_id = fields.Many2one('project.task.type', string='Stage', readonly=True)

    def _select(self):
        select_str = """
             SELECT
                    (select 1 ) AS nbr,
                    t.id as id,
                    t.date_start as date_start,
                    t.date_end as date_end,
                    t.date_last_stage_update as date_last_stage_update,
                    t.date_deadline as date_deadline,
                    t.user_id,
                    t.project_id,
                    t.priority,
                    t.name as name,
                    t.company_id,
                    t.partner_id,
                    t.stage_id as stage_id,
                    t.kanban_state as state,
                    t.working_days_close as working_days_close,
                    t.working_days_open  as working_days_open,
                    (extract('epoch' from (t.date_deadline-(now() at time zone 'UTC'))))/(3600*24)  as delay_endings_days
        """
        return select_str

    def _group_by(self):
        group_by_str = """
                GROUP BY
                    t.id,
                    create_date,
                    write_date,
                    date_start,
                    date_end,
                    date_deadline,
                    date_last_stage_update,
                    t.user_id,
                    t.project_id,
                    t.priority,
                    name,
                    t.company_id,
                    t.partner_id,
                    stage_id
        """
        return group_by_str

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
            CREATE view %s as
              %s
              FROM project_task t
                WHERE t.active = 'true'
                %s
        """ % (self._table, self._select(), self._group_by()))
