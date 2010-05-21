from osv import fields,osv
import tools
from crm import crm

AVAILABLE_STATES = [
    ('draft','Draft'),
    ('open','Open'),
    ('cancel', 'Cancelled'),
    ('done', 'Closed'),
    ('pending','Pending')
]

class project_issue_report(osv.osv):
    _name = "project.issue.report"
    _auto = False

    def _get_data(self, cr, uid, ids, field_name, arg, context={}):
        """ @param cr: the current row, from the database cursor,
            @param uid: the current users ID for security checks,
            @param ids: List of case and section Datas IDs
            @param context: A standard dictionary for contextual values """

        res = {}
        state_perc = 0.0
        avg_ans = 0.0

        for case in self.browse(cr, uid, ids, context):
            if field_name != 'avg_answers':
                state = field_name[5:]
                cr.execute("select count(*) from crm_opportunity where \
                    section_id =%s and state='%s'"%(case.section_id.id, state))
                state_cases = cr.fetchone()[0]
                perc_state = (state_cases / float(case.nbr)) * 100

                res[case.id] = perc_state
            else:
                model_name = self._name.split('report.')
                if len(model_name) < 2:
                    res[case.id] = 0.0
                else:
                    model_name = model_name[1]

                    cr.execute("select count(*) from crm_case_log l, ir_model m \
                         where l.model_id=m.id and m.model = '%s'" , model_name)
                    logs = cr.fetchone()[0]

                    avg_ans = logs / case.nbr
                    res[case.id] = avg_ans

        return res

    _columns = {
        'name': fields.char('Year', size=64, required=False, readonly=True),
        'user_id':fields.many2one('res.users', 'User', readonly=True),
        'section_id':fields.many2one('crm.case.section', 'Section', readonly=True),
        'nbr': fields.integer('# of Cases', readonly=True),
        'state': fields.selection(AVAILABLE_STATES, 'State', size=16, readonly=True),
        'avg_answers': fields.function(_get_data, string='Avg. Answers', method=True, type="integer"),
        'perc_done': fields.function(_get_data, string='%Done', method=True, type="float"),
        'perc_cancel': fields.function(_get_data, string='%Cancel', method=True, type="float"),
        'month':fields.selection([('01', 'January'), ('02', 'February'), \
                                  ('03', 'March'), ('04', 'April'),\
                                  ('05', 'May'), ('06', 'June'), \
                                  ('07', 'July'), ('08', 'August'),\
                                  ('09', 'September'), ('10', 'October'),\
                                  ('11', 'November'), ('12', 'December')], 'Month', readonly=True),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
        'create_date': fields.datetime('Create Date', readonly=True),
        'day': fields.char('Day', size=128, readonly=True), 
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