# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools

from odoo.addons.rating.models.rating_data import RATING_LIMIT_MIN, RATING_TEXT

class ReportProjectTaskUser(models.Model):
    _name = "report.project.task.user"
    _description = "Tasks Analysis"
    _order = 'name desc, project_id'
    _auto = False

    name = fields.Char(string='Task', readonly=True)
    user_ids = fields.Many2many('res.users', relation='project_task_user_rel', column1='task_id', column2='user_id',
                                string='Assignees', readonly=True)
    create_date = fields.Datetime("Create Date", readonly=True)
    date_assign = fields.Datetime(string='Assignment Date', readonly=True)
    date_end = fields.Datetime(string='Ending Date', readonly=True)
    date_deadline = fields.Datetime(string='Deadline', readonly=True)
    date_last_stage_update = fields.Datetime(string='Last Stage Update', readonly=True)
    project_id = fields.Many2one('project.project', string='Project', readonly=True)
    working_days_close = fields.Float(string='Working Days to Close',
        digits=(16, 2), readonly=True, group_operator="avg")
    working_days_open = fields.Float(string='Working Days to Assign',
        digits=(16, 2), readonly=True, group_operator="avg")
    delay_endings_days = fields.Float(string='Days to Deadline', digits=(16, 2), group_operator="avg", readonly=True)
    nbr = fields.Integer('# of Tasks', readonly=True)  # TDE FIXME master: rename into nbr_tasks
    working_hours_open = fields.Float(string='Working Hours to Assign', digits=(16, 2), readonly=True, group_operator="avg")
    working_hours_close = fields.Float(string='Working Hours to Close', digits=(16, 2), readonly=True, group_operator="avg")
    rating_last_value = fields.Float('Rating (/5)', group_operator="avg", readonly=True, groups="project.group_project_rating")
    rating_avg = fields.Float('Average Rating', readonly=True, group_operator='avg', groups="project.group_project_rating")
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'High')
        ], readonly=True, string="Priority")

    state = fields.Selection([
        ('01_in_progress', 'In Progress'),
        ('1_done', 'Done'),
        ('04_waiting_normal', 'Waiting'),
        ('03_approved', 'Approved'),
        ('1_canceled', 'Canceled'),
        ('02_changes_requested', 'Changes Requested'),
    ], string='State', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True)
    stage_id = fields.Many2one('project.task.type', string='Stage', readonly=True)
    task_id = fields.Many2one('project.task', string='Tasks', readonly=True)
    active = fields.Boolean(readonly=True)
    tag_ids = fields.Many2many('project.tags', relation='project_tags_project_task_rel',
        column1='project_task_id', column2='project_tags_id',
        string='Tags', readonly=True)
    parent_id = fields.Many2one('project.task', string='Parent Task', readonly=True)
    personal_stage_type_ids = fields.Many2many('project.task.type', relation='project_task_user_rel',
        column1='task_id', column2='stage_id',
        string="Personal Stage", readonly=True)
    milestone_id = fields.Many2one('project.milestone', readonly=True)
    message_is_follower = fields.Boolean(related='task_id.message_is_follower')
    dependent_ids = fields.Many2many('project.task', relation='task_dependencies_rel', column1='depends_on_id',
        column2='task_id', string='Block', readonly=True,
        domain="[('allow_task_dependencies', '=', True), ('id', '!=', id)]")
    description = fields.Text(readonly=True)

    def _select(self):
        return """
                (select 1) AS nbr,
                t.id as id,
                t.id as task_id,
                t.active,
                t.create_date,
                t.date_assign,
                t.date_end,
                t.date_last_stage_update,
                t.date_deadline,
                t.project_id,
                t.priority,
                t.name as name,
                t.company_id,
                t.partner_id,
                t.parent_id,
                t.stage_id,
                t.state,
                t.milestone_id,
                CASE WHEN pm.id IS NOT NULL THEN true ELSE false END as has_late_and_unreached_milestone,
                t.description,
                NULLIF(t.rating_last_value, 0) as rating_last_value,
                AVG(rt.rating) as rating_avg,
                t.working_days_close,
                t.working_days_open,
                t.working_hours_open,
                t.working_hours_close,
                (extract('epoch' from (t.date_deadline-(now() at time zone 'UTC'))))/(3600*24) as delay_endings_days,
                COUNT(td.task_id) as dependent_ids_count
        """

    def _group_by(self):
        return """
                t.id,
                t.active,
                t.create_date,
                t.date_assign,
                t.date_end,
                t.date_last_stage_update,
                t.date_deadline,
                t.project_id,
                t.priority,
                t.name,
                t.company_id,
                t.partner_id,
                t.parent_id,
                t.stage_id,
                t.state,
                t.rating_last_value,
                t.working_days_close,
                t.working_days_open,
                t.working_hours_open,
                t.working_hours_close,
                t.milestone_id,
                pm.id,
                td.depends_on_id
        """

    def _from(self):
        return f"""
                project_task t
                    LEFT JOIN rating_rating rt ON rt.res_id = t.id
                          AND rt.res_model = 'project.task'
                          AND rt.consumed = True
                          AND rt.rating >= {RATING_LIMIT_MIN}
                    LEFT JOIN project_milestone pm ON pm.id = t.milestone_id
                          AND pm.is_reached = False
                          AND pm.deadline <= CAST(now() AS DATE)
                    LEFT JOIN task_dependencies_rel td ON td.depends_on_id = t.id
        """

    def _where(self):
        return """
                t.project_id IS NOT NULL
        """

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
    CREATE view %s as
         SELECT %s
           FROM %s
          WHERE %s
       GROUP BY %s
        """ % (self._table, self._select(), self._from(), self._where(), self._group_by()))
