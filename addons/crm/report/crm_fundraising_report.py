from osv import fields,osv
import tools

class crm_fundraising_report(osv.osv):
    _name = "crm.fundraising.report"
    _auto = False
    _inherit = "crm.case.report"
    _columns = {
        'categ_id': fields.many2one('crm.case.categ', 'Category', domain="[('section_id','=',section_id),('object_id.model', '=', 'crm.fundraising')]"),
        'probability': fields.float('Avg. Probability', readonly=True ,group_operator='avg'),
        'amount_revenue': fields.float('Est.Revenue', readonly=True),
        'amount_revenue_prob': fields.float('Est. Rev*Prob.', readonly=True),
        'delay_close': fields.char('Delay to close', size=20, readonly=True),
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'company_id': fields.many2one('res.company','Company'),
    }
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'crm_fundraising_report')
        cr.execute("""
            create or replace view crm_fundraising_report as (
                select
                    min(c.id) as id,
                    to_char(c.create_date, 'YYYY') as name,
                    to_char(c.create_date, 'MM') as month,
                    c.state,
                    c.user_id,
                    c.section_id,
                    c.categ_id,
                    c.company_id,
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
                group by to_char(c.create_date, 'YYYY'), to_char(c.create_date, 'MM'), c.state, c.user_id,c.section_id,c.categ_id,c.partner_id,c.company_id
            )""")
crm_fundraising_report()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
