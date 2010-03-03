from osv import fields,osv
import tools

class report_crm_lead(osv.osv):
    _name = "report.crm.lead"
    _auto = False
    _inherit = "report.crm.case.user"
    _columns = {
        'delay_close': fields.char('Delay to close', size=20, readonly=True),
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
                    count(*) as nbr,
                    to_char(avg(date_closed-c.create_date), 'DD"d" HH24:MI:SS') as delay_close
                from
                    crm_lead c
                group by to_char(c.create_date, 'YYYY'), to_char(c.create_date, 'MM'), c.state, c.user_id,c.section_id,c.stage_id
            )""")
report_crm_lead()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
