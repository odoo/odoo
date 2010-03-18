from osv import fields,osv
import tools

AVAILABLE_STATES = [
    ('draft','Draft'),
    ('open','Open'),
    ('cancel', 'Cancelled'),
    ('done', 'Closed'),
    ('pending','Pending')
]

class crm_lead_report(osv.osv):
    _name = "crm.lead.report"
    _auto = False
    _inherit = "crm.case.report"
    _columns = {
        'delay_close': fields.char('Delay to close', size=20, readonly=True),
        'categ_id': fields.many2one('crm.case.categ', 'Category', domain="[('section_id','=',section_id),('object_id.model', '=', 'crm.lead')]" ,readonly=True),
        'stage_id': fields.many2one ('crm.case.stage', 'Stage', domain="[('section_id','=',section_id),('object_id.model', '=', 'crm.lead')]", readonly=True),
        'partner_id': fields.many2one('res.partner', 'Partner' ,readonly=True),
#        'company_id': fields.many2one('res.company','Company',readonly=True),
#        'state': fields.selection(AVAILABLE_STATES, 'State', size=16, readonly=True),
#        'user_id': fields.many2one('res.user', 'Company',readonly=True),
    }
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'crm_lead_report')
        cr.execute("""
            create or replace view crm_lead_report as (
                select
                    min(c.id) as id,
                    to_char(c.create_date, 'YYYY') as name,
                    to_char(c.create_date, 'MM') as month,
                    c.state as state,
                    c.user_id,
                    c.stage_id,
                    c.company_id,
                    c.section_id,
                    c.categ_id,
                    c.partner_id,
                    count(*) as nbr,
                    0 as avg_answers,
                    0.0 as perc_done,
                    0.0 as perc_cancel,
                    to_char(avg(date_closed-c.create_date), 'DD"d" HH24:MI:SS') as delay_close
                from
                    crm_lead c
                group by to_char(c.create_date, 'YYYY'), to_char(c.create_date, 'MM'), c.state, c.user_id,c.section_id,c.stage_id,categ_id,c.partner_id,c.company_id
            )""")
crm_lead_report()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
