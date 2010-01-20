from osv import fields,osv
import tools

class report_crm_lead_user(osv.osv):
    _name = "report.crm.lead.user"
    _description = "Leads by user and section"
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
        tools.drop_view_if_exists(cr, 'report_crm_lead_user')
        cr.execute("""
            create or replace view report_crm_lead_user as (
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
                    crm_lead c
                group by to_char(c.create_date, 'YYYY'), to_char(c.create_date, 'MM'), c.state, c.user_id,c.section_id
            )""")
report_crm_lead_user()

class report_crm_lead_categ(osv.osv):
    _name = "report.crm.lead.categ"
    _description = "Leads by section and category"
    _auto = False
    _inherit = "report.crm.case.categ"
    _columns = {
        'categ_id': fields.many2one('crm.case.categ', 'Category', domain="[('section_id','=',section_id),('object_id.model', '=', 'crm.lead')]"),
        'amount_revenue': fields.float('Est.Revenue', readonly=True),
        'amount_costs': fields.float('Est.Cost', readonly=True),
        'amount_revenue_prob': fields.float('Est. Rev*Prob.', readonly=True),
        'probability': fields.float('Avg. Probability', readonly=True),
        'delay_close': fields.char('Delay Close', size=20, readonly=True),
    }
    
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_crm_lead_categ')
        cr.execute("""
            create or replace view report_crm_lead_categ as (
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
                    crm_lead c
                group by c.categ_id,to_char(c.create_date, 'YYYY'), to_char(c.create_date, 'MM'), c.state,c.section_id
            )""")
report_crm_lead_categ()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: