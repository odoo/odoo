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

class crm_helpdesk_report(osv.osv):
    """ Helpdesk report after Sales Services """

    _name = "crm.helpdesk.report"
    _description = "Helpdesk report after Sales Services"
    _auto = False

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
        'delay_close': fields.float('Delay to Close',digits=(16,2),readonly=True, group_operator="avg"),
        'partner_id': fields.many2one('res.partner', 'Partner' , readonly=True),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
        'date_deadline': fields.date('Deadline', select=True),
        'priority': fields.selection([('5', 'Lowest'), ('4', 'Low'), \
                    ('3', 'Normal'), ('2', 'High'), ('1', 'Highest')], 'Priority'),
        'channel_id': fields.many2one('crm.case.channel', 'Channel'),
        'categ_id': fields.many2one('crm.case.categ', 'Category', \
                            domain="[('section_id','=',section_id),\
                            ('object_id.model', '=', 'crm.helpdesk')]"),
        'planned_cost': fields.float('Planned Costs'),
        'create_date': fields.date('Creation Date' , readonly=True, select=True),
        'date_closed': fields.date('Close Date', readonly=True, select=True),
        'delay_expected': fields.float('Overpassed Deadline',digits=(16,2),readonly=True, group_operator="avg"),
        'day': fields.char('Day', size=128, readonly=True),
        'email': fields.integer('# Emails', size=128, readonly=True),
    }

    def init(self, cr):

        """
            Display Deadline ,Responsible user, partner ,Department
            @param cr: the current row, from the database cursor
        """

        tools.drop_view_if_exists(cr, 'crm_helpdesk_report')
        cr.execute("""
            create or replace view crm_helpdesk_report as (
                select
                    min(c.id) as id,
                    to_char(c.date, 'YYYY') as name,
                    to_char(c.date, 'MM') as month,
                    to_char(c.date, 'YYYY-MM-DD') as day,
                    to_char(c.create_date, 'YYYY-MM-DD') as create_date,
                    to_char(c.date_closed, 'YYYY-mm-dd') as date_closed,
                    c.state,
                    c.user_id,
                    c.section_id,
                    c.partner_id,
                    c.company_id,
                    c.priority,
                    c.date_deadline,
                    c.categ_id,
                    c.channel_id,
                    c.planned_cost,
                    count(*) as nbr,
                    extract('epoch' from (c.date_closed-c.create_date))/(3600*24) as  delay_close,
                    (SELECT count(id) FROM mail_message WHERE model='crm.helpdesk' AND res_id=c.id AND type = 'email') AS email,
                    abs(avg(extract('epoch' from (c.date_deadline - c.date_closed)))/(3600*24)) as delay_expected
                from
                    crm_helpdesk c
                where c.active = 'true'
                group by to_char(c.date, 'YYYY'), to_char(c.date, 'MM'),to_char(c.date, 'YYYY-MM-DD'),\
                     c.state, c.user_id,c.section_id,c.priority,\
                     c.partner_id,c.company_id,c.date_deadline,c.create_date,c.date,c.date_closed,\
                     c.categ_id,c.channel_id,c.planned_cost,c.id
            )""")

crm_helpdesk_report()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
