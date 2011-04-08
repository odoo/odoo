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
from crm import crm

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
    _description = "CRM Lead Report"

    _columns = {
        'name': fields.char('Year', size=64, required=False, readonly=True),
        'user_id':fields.many2one('res.users', 'User', readonly=True),
        'country_id':fields.many2one('res.country', 'Country', readonly=True),
        'section_id':fields.many2one('crm.case.section', 'Sales Team', readonly=True),
        'channel_id':fields.many2one('res.partner.canal', 'Channel', readonly=True),
        'type_id':fields.many2one('crm.case.resource.type', 'Campaign', readonly=True),
        'state': fields.selection(AVAILABLE_STATES, 'State', size=16, readonly=True),
        'month':fields.selection([('01', 'January'), ('02', 'February'), \
                                  ('03', 'March'), ('04', 'April'),\
                                  ('05', 'May'), ('06', 'June'), \
                                  ('07', 'July'), ('08', 'August'),\
                                  ('09', 'September'), ('10', 'October'),\
                                  ('11', 'November'), ('12', 'December')], 'Month', readonly=True),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
        'create_date': fields.datetime('Create Date', readonly=True, select=True),
        'day': fields.char('Day', size=128, readonly=True),
        'email': fields.integer('# Emails', size=128, readonly=True),
        'delay_open': fields.float('Delay to Open',digits=(16,2),readonly=True, group_operator="avg",help="Number of Days to open the case"),
        'delay_close': fields.float('Delay to Close',digits=(16,2),readonly=True, group_operator="avg",help="Number of Days to close the case"),
        'delay_expected': fields.float('Overpassed Deadline',digits=(16,2),readonly=True, group_operator="avg"),
        'probability': fields.float('Probability',digits=(16,2),readonly=True, group_operator="avg"),
        'planned_revenue': fields.float('Planned Revenue',digits=(16,2),readonly=True),
        'probable_revenue': fields.float('Probable Revenue', digits=(16,2),readonly=True),
        'categ_id': fields.many2one('crm.case.categ', 'Category',\
                         domain="['|',('section_id','=',False),('section_id','=',section_id)]" , readonly=True),
        'stage_id': fields.many2one ('crm.case.stage', 'Stage', readonly=True, domain="('type', '=', 'lead')]"),
        'partner_id': fields.many2one('res.partner', 'Partner' , readonly=True),
        'opening_date': fields.date('Opening Date', readonly=True, select=True),
        'creation_date': fields.date('Creation Date', readonly=True, select=True),
        'date_closed': fields.date('Close Date', readonly=True, select=True),
        'nbr': fields.integer('# of Cases', readonly=True),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
        'priority': fields.selection(crm.AVAILABLE_PRIORITIES, 'Priority'),
        'type':fields.selection([
            ('lead','Lead'),
            ('opportunity','Opportunity'),
        ],'Type', help="Type is used to separate Leads and Opportunities"),
    }
    def init(self, cr):

        """
            CRM Lead Report
            @param cr: the current row, from the database cursor
        """
        tools.drop_view_if_exists(cr, 'crm_lead_report')
        cr.execute("""
            CREATE OR REPLACE VIEW crm_lead_report AS (
                SELECT
                    id,
                    to_char(c.date_deadline, 'YYYY') as name,
                    to_char(c.date_deadline, 'MM') as month,
                    to_char(c.date_deadline, 'YYYY-MM-DD') as day,
                    to_char(c.create_date, 'YYYY-MM-DD') as creation_date,
                    to_char(c.date_open, 'YYYY-MM-DD') as opening_date,
                    to_char(c.date_closed, 'YYYY-mm-dd') as date_closed,
                    c.state,
                    c.user_id,
                    c.probability,
                    c.stage_id,
                    c.type,
                    c.company_id,
                    c.priority,
                    c.section_id,
                    c.channel_id,
                    c.type_id,
                    c.categ_id,
                    c.partner_id,
                    c.country_id,
                    c.planned_revenue,
                    c.planned_revenue*(c.probability/100) as probable_revenue,
                    1 as nbr,
                    (SELECT count(id) FROM mailgate_message WHERE model='crm.lead' AND res_id=c.id AND history=True) AS email,
                    date_trunc('day',c.create_date) as create_date,
                    extract('epoch' from (c.date_closed-c.create_date))/(3600*24) as  delay_close,
                    abs(extract('epoch' from (c.date_deadline - c.date_closed))/(3600*24)) as  delay_expected,
                    extract('epoch' from (c.date_open-c.create_date))/(3600*24) as  delay_open
                FROM
                    crm_lead c
            )""")

crm_lead_report()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
