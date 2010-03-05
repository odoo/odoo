from osv import fields,osv
import tools

class report_crm_fundraising(osv.osv):
    _name = "report.crm.fundraising"
    _auto = False
    _inherit = "report.crm.case"
    _columns = {
        'categ_id': fields.many2one('crm.case.categ', 'Category', domain="[('section_id','=',section_id),('object_id.model', '=', 'crm.fundraising')]"),
        'probability': fields.float('Avg. Probability', readonly=True),
        'amount_revenue': fields.float('Est.Revenue', readonly=True),
        'amount_revenue_prob': fields.float('Est. Rev*Prob.', readonly=True),
        'delay_close': fields.char('Delay to close', size=20, readonly=True),
        'partner_id': fields.many2one('res.partner', 'Partner'),       
    }
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_crm_fundraising')
        cr.execute("""
            create or replace view report_crm_fundraising as (
                select
                    min(c.id) as id,
                    to_char(c.create_date, 'YYYY') as name,
                    to_char(c.create_date, 'MM') as month,
                    c.state,
                    c.user_id,
                    c.section_id,
                    c.categ_id,
                    c.partner_id,
                    count(*) as nbr,
                    0 as avg_answers,
                    0.0 as perc_done,
                    0.0 as perc_cancel,
                    sum(planned_revenue) as amount_revenue,                    
                    sum(planned_revenue*probability)::decimal(16,2) as amount_revenue_prob,
                    avg(probability)::decimal(16,2) as probability,
                    to_char(avg(date_closed-c.create_date), 'DD"d" HH24:MI:SS') as delay_close
                from
                    crm_fundraising c
                group by to_char(c.create_date, 'YYYY'), to_char(c.create_date, 'MM'), c.state, c.user_id,c.section_id,c.categ_id,c.partner_id
            )""")
report_crm_fundraising()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
