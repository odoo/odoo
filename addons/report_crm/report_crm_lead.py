from osv import fields,osv
import tools

class report_crm_lead(osv.osv):
    _name = "report.crm.lead"
    _description = "Leads by user and section"
    _auto = False
    _inherit = "report.crm.case"
    _columns = {
        'delay_close': fields.char('Delay to close', size=20, readonly=True),
        'categ_id': fields.many2one('crm.case.categ', 'Category', domain="[('section_id','=',section_id),('object_id.model', '=', 'crm.lead')]"),
        'stage_id': fields.many2one ('crm.case.stage', 'Stage', domain="[('section_id','=',section_id),('object_id.model', '=', 'crm.lead')]", readonly=True),
    }
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_crm_lead')
        cr.execute("""
            create or replace view report_crm_lead as (
                select
                    min(c.id) as id,
                    to_char(c.create_date, 'YYYY') as name,
                    to_char(c.create_date, 'MM') as month,
                    c.state,
                    c.user_id,
                    c.stage_id,
                    c.section_id,
                    c.categ_id,
                    count(*) as nbr,
                    to_char(avg(date_closed-c.create_date), 'DD"d" HH24:MI:SS') as delay_close
                from
                    crm_lead c
                group by to_char(c.create_date, 'YYYY'), to_char(c.create_date, 'MM'), c.state, c.user_id,c.section_id,c.stage_id,categ_id
            )""")
report_crm_lead()

#
#class report_crm_lead_section(osv.osv):
#    _name = "report.crm.lead.section"
#    _description = "Leads by Section"
#    _auto = False
#    _inherit = "report.crm.case.section"
#    
#    def _get_data(self, cr, uid, ids, field_name, arg, context={}):
#        res = {}
#        state_perc = 0.0
#        avg_ans = 0.0
#        
#        for case in self.browse(cr, uid, ids, context):
#            if field_name != 'avg_answers':
#                state = field_name[5:]
#                cr.execute("select count(*) from crm_lead where section_id =%s and state='%s'"%(case.section_id.id,state))
#                state_cases = cr.fetchone()[0]
#                perc_state = (state_cases / float(case.nbr_cases) ) * 100
#                
#                res[case.id] = perc_state
#            else:
#                cr.execute('select count(*) from crm_case_log l  where l.section_id=%s'%(case.section_id.id))
#                logs = cr.fetchone()[0]
#                
#                avg_ans = logs / case.nbr_cases
#                res[case.id] = avg_ans       
#        
#        return res
#    
#    _columns = {
#        'avg_answers': fields.function(_get_data,string='Avg. Answers', method=True,type="integer"),
#        'perc_done': fields.function(_get_data,string='%Done', method=True,type="float"),
#        'perc_cancel': fields.function(_get_data,string='%Cancel', method=True,type="float"),
#        'delay_close': fields.char('Delay to close', size=20, readonly=True),
#    }
#    _order = 'name desc, section_id'
#    def init(self, cr):
#        tools.drop_view_if_exists(cr, 'report_crm_lead_section')
#        cr.execute("""
#            create or replace view report_crm_lead_section as (
#                select
#                    min(c.id) as id,
#                    to_char(c.create_date, 'YYYY') as name,
#                    to_char(c.create_date, 'MM') as month,
#                    count(*) as nbr_cases,
#                    c.section_id as section_id,
#                    0 as avg_answers,
#                    0.0 as perc_done,
#                    0.0 as perc_cancel,
#                    to_char(avg(date_closed-c.create_date), 'DD"d" HH24:MI:SS') as delay_close
#                from
#                    crm_lead c
#                group by to_char(c.create_date, 'YYYY'),to_char(c.create_date, 'MM'),c.section_id
#            )""")
#report_crm_lead_section()
#

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: