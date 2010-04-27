from osv import fields,osv
import tools
from crm import crm

class project_issue_report(osv.osv):
    _name = "project.issue.report"
    _auto = False
    _inherit = "crm.case.report"
    _columns = {
        'categ_id': fields.many2one('crm.case.categ', 'Category', domain="[('section_id','=',section_id),('object_id.model', '=', 'project.issue')]"),
        'stage_id': fields.many2one ('crm.case.stage', 'Stage', domain="[('object_id.model', '=', 'project.issue')]"),
        'nbr': fields.integer('# of Issues', readonly=True),
        'delay_close': fields.float('Avg Closing Delay', digits=(16,2), readonly=True, group_operator="avg",
                                       help="Number of Days to close the project issue"),
        'company_id' : fields.many2one('res.company', 'Company'),
        'priority': fields.selection(crm.AVAILABLE_PRIORITIES, 'Priority'),
        'project_id':fields.many2one('project.project', 'Project',readonly=True),
        'type_id': fields.many2one('crm.case.resource.type', 'Type', domain="[('object_id.model', '=', 'project.issue')]"),
        'date_closed': fields.datetime('Close Date', readonly=True),
        'assigned_to' : fields.many2one('res.users', 'Assigned to',readonly=True),
        'partner_id': fields.many2one('res.partner','Partner',domain="[('object_id.model', '=', 'project.issue')]"),
        'canal_id': fields.many2one('res.partner.canal', 'Channel',readonly=True),
        'task_id': fields.many2one('project.task', 'Task',domain="[('object_id.model', '=', 'project.issue')]" )
    }
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'project_issue_report')
        cr.execute("""
            create or replace view project_issue_report as (
                select
                    min(c.id) as id,
                    to_char(c.create_date, 'YYYY') as name,
                    to_char(c.create_date, 'MM') as month,
                    to_char(c.create_date, 'YYYY-MM-DD') as day,
                    c.state,
                    c.user_id,
                    c.section_id,
                    c.categ_id,
                    c.stage_id,
                    to_char(c.date_closed, 'YYYY/mm/dd') as date_closed,
                    u.company_id as company_id,
                    c.priority as priority,
                    c.project_id as project_id,
                    c.type_id as type_id,
                    count(*) as nbr,
                    c.assigned_to,
                    c.partner_id,
                    c.canal_id,
                    c.task_id,
                    date_trunc('day',c.create_date) as create_date,
                    avg(extract('epoch' from (c.date_closed-c.create_date)))/(3600*24) as  delay_close
                from
                    project_issue c
                left join
                    res_users u on (c.id = u.id)
                group by
                    to_char(c.create_date, 'YYYY'),
                    to_char(c.create_date, 'MM'),
                    to_char(c.create_date, 'YYYY-MM-DD'),
                    c.state,
                    c.user_id,
                    c.section_id,
                    c.categ_id,
                    c.stage_id,
                    c.date_closed,
                    u.company_id,
                    c.priority,
                    c.project_id,
                    c.type_id,
                    date_trunc('day',c.create_date),
                    c.assigned_to,
                    c.partner_id,
                    c.canal_id,
                    c.task_id
            )""")


project_issue_report()



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: