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
        'date': fields.datetime('Date', readonly=True),
        'user_id':fields.many2one('res.users', 'User', readonly=True),
        'section_id':fields.many2one('crm.case.section', 'Section', readonly=True),
        'nbr': fields.integer('# of Requests', readonly=True),  # TDE FIXME master: rename into nbr_requests
        'state': fields.selection(AVAILABLE_STATES, 'Status', readonly=True),
        'delay_close': fields.float('Delay to Close',digits=(16,2),readonly=True, group_operator="avg"),
        'partner_id': fields.many2one('res.partner', 'Partner' , readonly=True),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
        'date_deadline': fields.date('Deadline', select=True),
        'priority': fields.selection([('5', 'Lowest'), ('4', 'Low'), \
                    ('3', 'Normal'), ('2', 'High'), ('1', 'Highest')], 'Priority'),
        'channel_id': fields.many2one('crm.tracking.medium', 'Channel'),
        'categ_id': fields.many2one('crm.case.categ', 'Category', \
                            domain="[('section_id','=',section_id),\
                            ('object_id.model', '=', 'crm.helpdesk')]"),
        'planned_cost': fields.float('Planned Costs'),
        'create_date': fields.datetime('Creation Date' , readonly=True, select=True),
        'date_closed': fields.datetime('Close Date', readonly=True, select=True),
        'delay_expected': fields.float('Overpassed Deadline',digits=(16,2),readonly=True, group_operator="avg"),
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
                    c.date as date,
                    c.create_date,
                    c.date_closed,
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
                group by c.date,\
                     c.state, c.user_id,c.section_id,c.priority,\
                     c.partner_id,c.company_id,c.date_deadline,c.create_date,c.date,c.date_closed,\
                     c.categ_id,c.channel_id,c.planned_cost,c.id
            )""")


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
