# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
from openerp import tools


class report_project_task_user(osv.osv):
    _name = "report.project.task.user"
    _description = "Tasks by user and project"
    _auto = False
    _columns = {
        'name': fields.char('Task Title', readonly=True),
        'user_id': fields.many2one('res.users', 'Assigned To', readonly=True),
        'date_start': fields.datetime('Assignation Date', readonly=True),
        'no_of_days': fields.integer('# of Days', size=128, readonly=True),
        'date_end': fields.datetime('Ending Date', readonly=True),
        'date_deadline': fields.date('Deadline', readonly=True),
        'date_last_stage_update': fields.datetime('Last Stage Update', readonly=True),
        'project_id': fields.many2one('project.project', 'Project', readonly=True),
        'closing_days': fields.float('Days to Close', digits=(16,2), readonly=True, group_operator="avg",
                                       help="Number of Days to close the task"),
        'opening_days': fields.float('Days to Assign', digits=(16,2), readonly=True, group_operator="avg",
                                       help="Number of Days to Open the task"),
        'delay_endings_days': fields.float('Overpassed Deadline', digits=(16,2), readonly=True),
        'nbr': fields.integer('# of Tasks', readonly=True),  # TDE FIXME master: rename into nbr_tasks
        'priority': fields.selection([('0','Low'), ('1','Normal'), ('2','High')],
            string='Priority', size=1, readonly=True),
        'state': fields.selection([('normal', 'In Progress'),('blocked', 'Blocked'),('done', 'Ready for next stage')],'Status', readonly=True),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
        'partner_id': fields.many2one('res.partner', 'Contact', readonly=True),
        'stage_id': fields.many2one('project.task.type', 'Stage'),
    }
    _order = 'name desc, project_id'

    def _select(self):
        select_str = """
             SELECT
                    (select 1 ) AS nbr,
                    t.id as id,
                    t.date_start as date_start,
                    t.date_end as date_end,
                    t.date_last_stage_update as date_last_stage_update,
                    t.date_deadline as date_deadline,
                    abs((extract('epoch' from (t.write_date-t.date_start)))/(3600*24))  as no_of_days,
                    t.user_id,
                    t.project_id,
                    t.priority,
                    t.name as name,
                    t.company_id,
                    t.partner_id,
                    t.stage_id as stage_id,
                    t.kanban_state as state,
                    (extract('epoch' from (t.write_date-t.create_date)))/(3600*24)  as closing_days,
                    (extract('epoch' from (t.date_start-t.create_date)))/(3600*24)  as opening_days,
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

    def init(self, cr):
        tools.sql.drop_view_if_exists(cr, 'report_project_task_user')
        cr.execute("""
            CREATE view report_project_task_user as
              %s
              FROM project_task t
                WHERE t.active = 'true'
                %s
        """% (self._select(), self._group_by()))
