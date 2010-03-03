from osv import fields,osv
import tools

class report_crm_project_bug(osv.osv):
    _name = "report.crm.project.bug"
    _description = "Project Bug by user and section"
    _auto = False
    _inherit = "report.crm.case"
    _columns = {
        'categ_id': fields.many2one('crm.case.categ', 'Category', domain="[('section_id','=',section_id),('object_id.model', '=', 'crm.project.bug')]"),
        'stage_id': fields.many2one ('crm.case.stage', 'Stage', domain="[('object_id.model', '=', 'crm.project.bug')]"),                
        'probability': fields.float('Avg. Probability', readonly=True),
        'amount_revenue': fields.float('Est.Revenue', readonly=True),
        'amount_costs': fields.float('Est.Cost', readonly=True),
        'amount_revenue_prob': fields.float('Est. Rev*Prob.', readonly=True),
        'delay_close': fields.char('Delay to close', size=20, readonly=True),
    }
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_crm_project_bug')
        cr.execute("""
            create or replace view report_crm_project_bug as (
                select
                    min(c.id) as id,
                    to_char(c.create_date, 'YYYY') as name,
                    to_char(c.create_date, 'MM') as month,
                    c.state,
                    c.user_id,
                    c.section_id,
                    c.categ_id,
                    c.stage_id,
                    count(*) as nbr,
                    sum(planned_revenue) as amount_revenue,
                    sum(planned_cost) as amount_costs,
                    sum(planned_revenue*probability)::decimal(16,2) as amount_revenue_prob,
                    avg(probability)::decimal(16,2) as probability,
                    to_char(avg(date_closed-c.create_date), 'DD"d" HH24:MI:SS') as delay_close
                from
                    crm_project_bug c
                group by to_char(c.create_date, 'YYYY'), to_char(c.create_date, 'MM'), c.state, c.user_id,c.section_id,c.categ_id,c.stage_id
            )""")
report_crm_project_bug()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: