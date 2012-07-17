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

from osv import fields,osv
import tools

AVAILABLE_STATES = [
    ('draft','Draft'),
    ('open','Open'),
    ('cancel', 'Cancelled'),
    ('done', 'Closed'),
    ('pending','Pending')
]

class crm_fundraising_report(osv.osv):
    """CRM Fundraising Report"""

    _name = "crm.fundraising.report"
    _auto = False
    _description = "CRM Fundraising Report"

    _columns = {
        'name': fields.char('Year', size=64, required=False, readonly=True),
        'user_id':fields.many2one('res.users', 'User', readonly=True),
        'section_id':fields.many2one('crm.case.section', 'Section', readonly=True),
        'nbr': fields.integer('# of Cases', readonly=True),
        'state': fields.selection(AVAILABLE_STATES, 'Status', size=16, readonly=True),
        'month':fields.selection([('01', 'January'), ('02', 'February'), \
                                  ('03', 'March'), ('04', 'April'),\
                                  ('05', 'May'), ('06', 'June'), \
                                  ('07', 'July'), ('08', 'August'),\
                                  ('09', 'September'), ('10', 'October'),\
                                  ('11', 'November'), ('12', 'December')], 'Month', readonly=True),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
        'create_date': fields.datetime('Create Date', readonly=True, select=True),
        'day': fields.char('Day', size=128, readonly=True), 
        'categ_id': fields.many2one('crm.case.categ', 'Category', \
                    domain="[('section_id','=',section_id),\
                    ('object_id.model', '=', 'crm.fundraising')]"),
        'probability': fields.float('Avg. Probability',digits=(16,2),readonly=True, group_operator="avg"),
        'amount_revenue': fields.float('Est.Revenue',readonly=True,digits=(16,2)),
        'amount_revenue_prob': fields.float('Est. Rev*Prob.',digits=(16,2),readonly=True),
        'delay_close': fields.float('Delay to close', digits=(16,2),readonly=True, group_operator="avg",help="Number of Days to close the case"),
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'company_id': fields.many2one('res.company', 'Company'),
        'type_id': fields.many2one('crm.case.resource.type', 'Fundraising Type', \
                             domain="[('section_id','=',section_id),\
                             ('object_id.model', '=', 'crm.fundraising')]"),
         'planned_cost': fields.float('Planned Costs',readonly=True,digits=(16,2)),
    }

    def init(self, cr):

        """  Display Number of cases and Average Probability
            @param cr: the current row, from the database cursor
        """

        tools.drop_view_if_exists(cr, 'crm_fundraising_report')
        cr.execute("""
            create or replace view crm_fundraising_report as (
                select
                    min(c.id) as id,
                    to_char(c.date, 'YYYY') as name,
                    to_char(c.date, 'MM') as month,
                    to_char(c.date, 'YYYY-MM-DD') as day,
                    c.state,
                    c.user_id,
                    c.section_id,
                    c.categ_id,
                    c.type_id,
                    c.company_id,
                    c.partner_id,
                    count(*) as nbr,
                    date_trunc('day',c.create_date) as create_date,
                    sum(planned_revenue) as amount_revenue,
                    sum(planned_cost) as planned_cost,
                    sum(planned_revenue*probability)::decimal(16,2) as amount_revenue_prob,
                    avg(probability)::decimal(16,2) as probability,
                    avg(extract('epoch' from (c.date_closed-c.create_date)))/(3600*24) as  delay_close
                from
                    crm_fundraising c
                where c.active = 'true'
                group by to_char(c.date, 'YYYY'), to_char(c.date, 'MM'),\
                     c.state, c.user_id,c.section_id,c.categ_id,type_id,c.partner_id,c.company_id,
                     c.create_date,to_char(c.date, 'YYYY-MM-DD')
            )""")

crm_fundraising_report()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
