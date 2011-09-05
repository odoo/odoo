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

AVAILABLE_PRIORITIES = [
    ('5', 'Lowest'),
    ('4', 'Low'),
    ('3', 'Normal'),
    ('2', 'High'),
    ('1', 'Highest')
]


class crm_claim_report(osv.osv):
    """ CRM Claim Report"""

    _name = "crm.claim.report"
    _auto = False
    _description = "CRM Claim Report"

    _columns = {
        'name': fields.char('Year', size=64, required=False, readonly=True),
        'user_id':fields.many2one('res.users', 'User', readonly=True),
        'section_id':fields.many2one('crm.case.section', 'Section', readonly=True),
        'nbr': fields.integer('# of Cases', readonly=True),
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
        'delay_close': fields.float('Delay to close', digits=(16,2),readonly=True, group_operator="avg",help="Number of Days to close the case"),
        'stage_id': fields.many2one ('crm.case.stage', 'Stage', readonly=True,domain="[('section_ids','=',section_id)]"),
        'categ_id': fields.many2one('crm.case.categ', 'Category',\
                         domain="[('section_id','=',section_id),\
                        ('object_id.model', '=', 'crm.claim')]", readonly=True),
        'probability': fields.float('Probability',digits=(16,2),readonly=True, group_operator="avg"),
        'partner_id': fields.many2one('res.partner', 'Partner', readonly=True),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
        'priority': fields.selection(AVAILABLE_PRIORITIES, 'Priority'),
        'type_action': fields.selection([('correction','Corrective Action'),('prevention','Preventive Action')], 'Action Type'),
        'date_closed': fields.date('Close Date', readonly=True, select=True), 
        'date_deadline': fields.date('Deadline', readonly=True, select=True), 
        'delay_expected': fields.float('Overpassed Deadline',digits=(16,2),readonly=True, group_operator="avg"),
        'email': fields.integer('# Emails', size=128, readonly=True)
    }

    def init(self, cr):

        """ Display Number of cases And Section Name
        @param cr: the current row, from the database cursor,
         """

        tools.drop_view_if_exists(cr, 'crm_claim_report')
        cr.execute("""
            create or replace view crm_claim_report as (
                select
                    min(c.id) as id,
                    to_char(c.date, 'YYYY') as name,
                    to_char(c.date, 'MM') as month,
                    to_char(c.date, 'YYYY-MM-DD') as day,
                    to_char(c.date_closed, 'YYYY-MM-DD') as date_closed,
                    to_char(c.date_deadline, 'YYYY-MM-DD') as date_deadline,
                    c.state,
                    c.user_id,
                    c.stage_id,
                    c.section_id,
                    c.partner_id,
                    c.company_id,
                    c.categ_id,
                    count(*) as nbr,
                    c.priority as priority,
                    c.type_action as type_action,
                    date_trunc('day',c.create_date) as create_date,
                    avg(extract('epoch' from (c.date_closed-c.create_date)))/(3600*24) as  delay_close,
                    (SELECT count(id) FROM mailgate_message WHERE model='crm.claim' AND res_id=c.id AND history=True) AS email,
                    (SELECT avg(probability) FROM crm_case_stage WHERE id=c.stage_id) AS probability,
                    extract('epoch' from (c.date_deadline - c.date_closed))/(3600*24) as  delay_expected
                from
                    crm_claim c
                group by to_char(c.date, 'YYYY'), to_char(c.date, 'MM'),to_char(c.date, 'YYYY-MM-DD'),\
                        c.state, c.user_id,c.section_id, c.stage_id,\
                        c.categ_id,c.partner_id,c.company_id,c.create_date,
                        c.priority,c.type_action,c.date_deadline,c.date_closed,c.id
            )""")

crm_claim_report()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
