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
from openerp.addons.crm import crm


class crm_lead_report_assign(osv.osv):
    """ CRM Lead Report """
    _name = "crm.lead.report.assign"
    _auto = False
    _description = "CRM Lead Report"
    _columns = {
        'partner_assigned_id':fields.many2one('res.partner', 'Partner', readonly=True),
        'grade_id':fields.many2one('res.partner.grade', 'Grade', readonly=True),
        'user_id':fields.many2one('res.users', 'User', readonly=True),
        'country_id':fields.many2one('res.country', 'Country', readonly=True),
        'section_id':fields.many2one('crm.case.section', 'Sales Team', readonly=True),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
        'date_assign': fields.date('Assign Date', readonly=True),
        'create_date': fields.datetime('Create Date', readonly=True),
        'delay_open': fields.float('Delay to Assign',digits=(16,2),readonly=True, group_operator="avg",help="Number of Days to open the case"),
        'delay_close': fields.float('Delay to Close',digits=(16,2),readonly=True, group_operator="avg",help="Number of Days to close the case"),
        'delay_expected': fields.float('Overpassed Deadline',digits=(16,2),readonly=True, group_operator="avg"),
        'probability': fields.float('Avg Probability',digits=(16,2),readonly=True, group_operator="avg"),
        'probability_max': fields.float('Max Probability',digits=(16,2),readonly=True, group_operator="max"),
        'planned_revenue': fields.float('Planned Revenue',digits=(16,2),readonly=True),
        'probable_revenue': fields.float('Probable Revenue', digits=(16,2),readonly=True),
        'stage_id': fields.many2one ('crm.case.stage', 'Stage', domain="[('section_ids', '=', section_id)]"),
        'partner_id': fields.many2one('res.partner', 'Customer' , readonly=True),
        'opening_date': fields.date('Opening Date', readonly=True),
        'creation_date': fields.date('Creation Date', readonly=True),
        'date_closed': fields.date('Close Date', readonly=True),
        'nbr': fields.integer('# of Cases', readonly=True),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
        'priority': fields.selection(crm.AVAILABLE_PRIORITIES, 'Priority'),
        'type':fields.selection([
            ('lead','Lead'),
            ('opportunity','Opportunity') 
        ],'Type', help="Type is used to separate Leads and Opportunities"),
    }
    def init(self, cr):

        """
            CRM Lead Report
            @param cr: the current row, from the database cursor
        """
        tools.drop_view_if_exists(cr, 'crm_lead_report_assign')
        cr.execute("""
            CREATE OR REPLACE VIEW crm_lead_report_assign AS (
                SELECT
                    c.id,
                    to_char(c.create_date, 'YYYY-MM-DD') as creation_date,
                    to_char(c.date_open, 'YYYY-MM-DD') as opening_date,
                    to_char(c.date_closed, 'YYYY-mm-dd') as date_closed,
                    c.date_assign,
                    c.user_id,
                    c.probability,
                    c.probability as probability_max,
                    c.stage_id,
                    c.type,
                    c.company_id,
                    c.priority,
                    c.section_id,
                    c.partner_id,
                    c.country_id,
                    c.planned_revenue,
                    c.partner_assigned_id,
                    p.grade_id,
                    p.date as partner_date,
                    c.planned_revenue*(c.probability/100) as probable_revenue, 
                    1 as nbr,
                    date_trunc('day',c.create_date) as create_date,
                    extract('epoch' from (c.write_date-c.create_date))/(3600*24) as  delay_close,
                    extract('epoch' from (c.date_deadline - c.date_closed))/(3600*24) as  delay_expected,
                    extract('epoch' from (c.date_open-c.create_date))/(3600*24) as  delay_open
                FROM
                    crm_lead c
                    left join res_partner p on (c.partner_assigned_id=p.id)
            )""")


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
