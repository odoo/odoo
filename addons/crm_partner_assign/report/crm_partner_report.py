# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp.osv import fields,osv
from openerp import tools


class crm_partner_report_assign(osv.osv):
    """ CRM Lead Report """
    _name = "crm.partner.report.assign"
    _auto = False
    _description = "CRM Partner Report"
    _columns = {
        'partner_id': fields.many2one('res.partner', 'Partner', required=False, readonly=True),
        'grade_id':fields.many2one('res.partner.grade', 'Grade', readonly=True),
        'activation' : fields.many2one('res.partner.activation', 'Activation', select=1),
        'user_id':fields.many2one('res.users', 'User', readonly=True),
        'date_review' : fields.date('Latest Partner Review'),
        'date_partnership' : fields.date('Partnership Date'),
        'country_id':fields.many2one('res.country', 'Country', readonly=True),
        'team_id':fields.many2one('crm.team', 'Sales Team', oldname='section_id', readonly=True),
        'opp': fields.integer('# of Opportunity', readonly=True),  # TDE FIXME master: rename into nbr_opportunities
        'turnover': fields.float('Turnover', readonly=True),
        'date': fields.date('Invoice Account Date', readonly=True),
    }
    def init(self, cr):
        """
            CRM Lead Report
            @param cr: the current row, from the database cursor
        """
        tools.drop_view_if_exists(cr, 'crm_partner_report_assign')
        cr.execute("""
            CREATE OR REPLACE VIEW crm_partner_report_assign AS (
                SELECT
                    coalesce(i.id, p.id - 1000000000) as id,
                    p.id as partner_id,
                    (SELECT country_id FROM res_partner a WHERE a.parent_id=p.id AND country_id is not null limit 1) as country_id,
                    p.grade_id,
                    p.activation,
                    p.date_review,
                    p.date_partnership,
                    p.user_id,
                    p.team_id,
                    (SELECT count(id) FROM crm_lead WHERE partner_assigned_id=p.id) AS opp,
                    i.price_total as turnover,
                    i.date
                FROM
                    res_partner p
                    left join account_invoice_report i
                        on (i.partner_id=p.id and i.type in ('out_invoice','out_refund') and i.state in ('open','paid'))
            )""")
