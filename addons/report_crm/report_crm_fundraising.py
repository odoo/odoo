from osv import fields,osv
import tools

class report_crm_fundraising_user(osv.osv):
    _name = "report.crm.fundraising.user"
    _description = "Fundraising by user and section"
    _auto = False
    _inherit = "report.crm.case.user"
    _columns = {
        'probability': fields.float('Avg. Probability', readonly=True),
        'amount_revenue': fields.float('Est.Revenue', readonly=True),
        'amount_costs': fields.float('Est.Cost', readonly=True),
        'amount_revenue_prob': fields.float('Est. Rev*Prob.', readonly=True),
        'delay_close': fields.char('Delay to close', size=20, readonly=True),
    }
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_crm_fundraising_user')
        cr.execute("""
            create or replace view report_crm_fundraising_user as (
                select
                    min(c.id) as id,
                    to_char(c.create_date, 'YYYY') as name,
                    to_char(c.create_date, 'MM') as month,
                    c.state,
                    c.user_id,
                    c.section_id,
                    count(*) as nbr,
                    sum(planned_revenue) as amount_revenue,
                    sum(planned_cost) as amount_costs,
                    sum(planned_revenue*probability)::decimal(16,2) as amount_revenue_prob,
                    avg(probability)::decimal(16,2) as probability,
                    to_char(avg(date_closed-c.create_date), 'DD"d" HH24:MI:SS') as delay_close
                from
                    crm_fundraising c
                group by to_char(c.create_date, 'YYYY'), to_char(c.create_date, 'MM'), c.state, c.user_id,c.section_id
            )""")
report_crm_fundraising_user()

class report_crm_fundraising_categ(osv.osv):
    _name = "report.crm.fundraising.categ"
    _description = "Fundraising by section and category"
    _auto = False
    _inherit = "report.crm.case.categ"
    _columns = {
        'categ_id': fields.many2one('crm.case.categ', 'Category', domain="[('section_id','=',section_id),('object_id.model', '=', 'crm.fundraising')]"),
        'amount_revenue': fields.float('Est.Revenue', readonly=True),
        'amount_costs': fields.float('Est.Cost', readonly=True),
        'amount_revenue_prob': fields.float('Est. Rev*Prob.', readonly=True),
        'probability': fields.float('Avg. Probability', readonly=True),
        'delay_close': fields.char('Delay Close', size=20, readonly=True),
    }
    
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_crm_fundraising_categ')
        cr.execute("""
            create or replace view report_crm_fundraising_categ as (
                select
                    min(c.id) as id,
                    to_char(c.create_date, 'YYYY') as name,
                    to_char(c.create_date, 'MM') as month,
                    c.categ_id,
                    c.state,
                    c.section_id,
                    count(*) as nbr,
                    sum(planned_revenue) as amount_revenue,
                    sum(planned_cost) as amount_costs,
                    sum(planned_revenue*probability)::decimal(16,2) as amount_revenue_prob,
                    avg(probability)::decimal(16,2) as probability,
                    to_char(avg(date_closed-c.create_date), 'DD"d" HH24:MI:SS') as delay_close
                from
                    crm_fundraising c
                group by c.categ_id,to_char(c.create_date, 'YYYY'), to_char(c.create_date, 'MM'), c.state,c.section_id
            )""")
report_crm_fundraising_categ()

class report_crm_fundraising_section(osv.osv):
    _name = "report.crm.fundraising.section"
    _description = "Fundraising by Section"
    _auto = False
    _inherit = "report.crm.case.section"
    
    def _get_data(self, cr, uid, ids, field_name, arg, context={}):
        res = {}
        state_perc = 0.0
        avg_ans = 0.0
        
        for case in self.browse(cr, uid, ids, context):
            if field_name != 'avg_answers':
                state = field_name[5:]
                cr.execute("select count(*) from crm_fundraising where section_id =%s and state='%s'"%(case.section_id.id,state))
                state_cases = cr.fetchone()[0]
                perc_state = (state_cases / float(case.nbr_cases) ) * 100
                
                res[case.id] = perc_state
            else:
                cr.execute('select count(*) from crm_case_log l  where l.section_id=%s'%(case.section_id.id))
                logs = cr.fetchone()[0]
                
                avg_ans = logs / case.nbr_cases
                res[case.id] = avg_ans       
        
        return res
    
    _columns = {
        'avg_answers': fields.function(_get_data,string='Avg. Answers', method=True,type="integer"),
        'perc_done': fields.function(_get_data,string='%Done', method=True,type="float"),
        'perc_cancel': fields.function(_get_data,string='%Cancel', method=True,type="float"),
        'delay_close': fields.char('Delay to close', size=20, readonly=True),
    }
    _order = 'name desc, section_id'
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_crm_fundraising_section')
        cr.execute("""
            create or replace view report_crm_fundraising_section as (
                select
                    min(c.id) as id,
                    to_char(c.create_date, 'YYYY') as name,
                    to_char(c.create_date, 'MM') as month,
                    count(*) as nbr_cases,
                    c.section_id as section_id,
                    0 as avg_answers,
                    0.0 as perc_done,
                    0.0 as perc_cancel,
                    to_char(avg(date_closed-c.create_date), 'DD"d" HH24:MI:SS') as delay_close
                from
                    crm_fundraising c
                group by to_char(c.create_date, 'YYYY'),to_char(c.create_date, 'MM'),c.section_id
            )""")
report_crm_fundraising_section()

class report_crm_fundraising_section_type(osv.osv):
    _name = "report.crm.fundraising.section.type"
    _inherit = "report.crm.case.section.type"
    _description = "Fundraising by section and type"
    _auto = False
    _columns = {
        'type_id': fields.many2one('crm.case.resource.type', 'Fundraising Type', domain="[('section_id','=',section_id),('object_id.model', '=', 'crm.fundraising')]", readonly=True),
        'stage_id': fields.many2one ('crm.case.stage', 'Stage', domain="[('section_id','=',section_id),('object_id.model', '=', 'crm.fundraising')]", readonly=True),
        'amount_revenue': fields.float('Est.Revenue', readonly=True),
        'delay_close': fields.char('Delay Close', size=20, readonly=True),
    }
    _order = 'type_id'

    def init(self, cr):
        tools.sql.drop_view_if_exists(cr, "report_crm_fundraising_section_type")
        cr.execute("""
              create view report_crm_fundraising_section_type as (
                select
                    min(c.id) as id,
                    to_char(c.create_date,'YYYY') as name,
                    to_char(c.create_date, 'MM') as month,
                    c.user_id,
                    c.state,
                    c.type_id,
                    c.stage_id,
                    c.section_id,
                    count(*) as nbr,
                    sum(planned_revenue) as amount_revenue,
                    to_char(avg(date_closed-c.create_date), 'DD"d" HH24:MI:SS') as delay_close
                from
                    crm_fundraising c
                where c.type_id is not null
                group by to_char(c.create_date, 'YYYY'), to_char(c.create_date, 'MM'), c.user_id, c.state, c.stage_id, c.type_id, c.section_id)""")

report_crm_fundraising_section_type()

class report_crm_fundraising_section_categ_stage(osv.osv):
    _name = "report.crm.fundraising.section.categ.stage"
    _inherit = "report.crm.case.section.categ.stage"
    _description = "Fundraising by Section, Category and Stage"
    _auto = False
    _columns = {
        'categ_id': fields.many2one('crm.case.categ','Category', domain="[('section_id','=',section_id),('object_id.model', '=', 'crm.fundraising')]", readonly=True),
        'stage_id':fields.many2one('crm.case.stage', 'Stage', domain="[('section_id','=',section_id),('object_id.model', '=', 'crm.fundraising')]", readonly=True),
        'delay_close': fields.char('Delay Close', size=20, readonly=True),
    }
    _order = 'stage_id, categ_id'

    def init(self, cr):
        tools.sql.drop_view_if_exists(cr, "report_crm_fundraising_section_categ_stage")
        cr.execute("""
              create view report_crm_fundraising_section_categ_stage as (
                select
                    min(c.id) as id,
                    to_char(c.create_date,'YYYY') as name,
                    to_char(c.create_date, 'MM') as month,
                    c.user_id,
                    c.categ_id,
                    c.state,
                    c.stage_id,
                    c.section_id,
                    count(*) as nbr,
                    to_char(avg(date_closed-c.create_date), 'DD"d" HH24:MI:SS') as delay_close
                from
                    crm_fundraising c
                where c.categ_id is not null AND c.stage_id is not null
                group by to_char(c.create_date, 'YYYY'), to_char(c.create_date, 'MM'),c.user_id, c.categ_id, c.state, c.stage_id, c.section_id)""")

report_crm_fundraising_section_categ_stage()

class report_crm_fundraising_section_categ_type(osv.osv):
    _name = "report.crm.fundraising.section.categ.type"
    _inherit = "report.crm.case.section.categ.type"
    _description = "Fundraising by Section, Category and Type"
    _auto = False
    _columns = {
        'categ_id':fields.many2one('crm.case.categ', 'Category', domain="[('section_id','=',section_id),('object_id.model', '=', 'crm.fundraising')]", readonly=True),
        'type_id': fields.many2one('crm.case.resource.type', 'Fundraising Type', domain="[('section_id','=',section_id),('object_id.model', '=', 'crm.fundraising')]", readonly=True),
        'stage_id':fields.many2one('crm.case.stage', 'Stage', domain="[('section_id','=',section_id),('object_id.model', '=', 'crm.fundraising')]", readonly=True),
        'delay_close': fields.char('Delay Close', size=20, readonly=True),
    }
    _order = 'categ_id, type_id'

    def init(self, cr):
        tools.sql.drop_view_if_exists(cr, "report_crm_fundraising_section_categ_type")
        cr.execute("""
              create view report_crm_fundraising_section_categ_type as (
                select
                    min(c.id) as id,
                    to_char(c.create_date, 'YYYY') as name,
                    to_char(c.create_date, 'MM') as month,
                    c.user_id,
                    c.categ_id,
                    c.type_id,
                    c.state,
                    c.stage_id,
                    c.section_id,
                    count(*) as nbr,
                    to_char(avg(date_closed-c.create_date), 'DD"d" HH24:MI:SS') as delay_close
                from
                    crm_fundraising c
                where c.categ_id is not null AND c.type_id is not null
                group by to_char(c.create_date, 'YYYY'), to_char(c.create_date, 'MM'),c.user_id, c.categ_id, c.type_id, c.state, c.stage_id, c.section_id)""")

report_crm_fundraising_section_categ_type()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: