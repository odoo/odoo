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

class crm_lead_report(osv.osv):
    """ CRM Lead Report """
    _name = "crm.lead.report"
    _auto = False
#    _inherit = "crm.case.report"
    _description = "CRM Lead Report"

    _columns = {
        'delay_close': fields.float('Delay to close',digits=(16,2),readonly=True, group_operator="avg",help="Number of Days to close the case"),
        'categ_id': fields.many2one('crm.case.categ', 'Category',\
                         domain="[('section_id','=',section_id),\
                        ('object_id.model', '=', 'crm.lead')]" , readonly=True),
        'stage_id': fields.many2one ('crm.case.stage', 'Stage', \
                         domain="[('section_id','=',section_id),\
                        ('object_id.model', '=', 'crm.lead')]", readonly=True),
        'partner_id': fields.many2one('res.partner', 'Partner' , readonly=True),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
    }
    def init(self, cr):

        """
            CRM Lead Report
            @param cr: the current row, from the database cursor
        """

        tools.drop_view_if_exists(cr, 'crm_lead_report')
        cr.execute("""
            create or replace view crm_lead_report as (
                select
                    min(c.id) as id,
                    to_char(c.create_date, 'YYYY') as name,
                    to_char(c.create_date, 'MM') as month,
                    to_char(c.create_date, 'YYYY-MM-DD') as day,
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
                    date_trunc('day',c.create_date) as create_date,
                    avg(extract('epoch' from (c.date_closed-c.create_date)))/(3600*24) as  delay_close
                from
                    crm_lead c
                group by to_char(c.create_date, 'YYYY'), to_char(c.create_date, 'MM'),\
                     c.state, c.user_id,c.section_id,c.stage_id,categ_id,c.partner_id,c.company_id
                     ,c.create_date,to_char(c.create_date, 'YYYY-MM-DD')
            )""")

crm_lead_report()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
