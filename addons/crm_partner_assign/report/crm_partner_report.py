# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
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
        'section_id':fields.many2one('crm.case.section', 'Sales Team', readonly=True),
        'opp': fields.integer('# of Opportunity', readonly=True),  # TDE FIXME master: rename into nbr_opportunities
        'turnover': fields.float('Turnover', readonly=True),
        'period_id': fields.many2one('account.period', 'Invoice Period', readonly=True),
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
                    p.section_id,
                    (SELECT count(id) FROM crm_lead WHERE partner_assigned_id=p.id) AS opp,
                    i.price_total as turnover,
                    i.period_id
                FROM
                    res_partner p
                    left join account_invoice_report i
                        on (i.partner_id=p.id and i.type in ('out_invoice','out_refund') and i.state in ('open','paid'))
            )""")


class account_invoice_report(osv.osv):
    _inherit = 'account.invoice.report'

    def init(self, cr):
        super(account_invoice_report, self).init(cr)
        self.pool['crm.partner.report.assign'].init(cr)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
