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

from openerp.addons.crm import crm
from openerp.osv import fields, osv
from openerp import tools

class crm_lead_report(osv.Model):
    """ CRM Lead Analysis """
    _name = "crm.lead.report"
    _auto = False
    _description = "CRM Lead Analysis"
    _rec_name = 'date_deadline'
    _inherit = ["crm.tracking.mixin"]

    _columns = {
        'date_deadline': fields.date('Exp. Closing', readonly=True, help="Expected Closing"),
        'create_date': fields.datetime('Creation Date', readonly=True),
        'opening_date': fields.datetime('Assignation Date', readonly=True),
        'date_closed': fields.datetime('Close Date', readonly=True),
        'date_last_stage_update': fields.datetime('Last Stage Update', readonly=True),
        'nbr_cases': fields.integer("# of Cases", readonly=True),

        # durations
        'delay_open': fields.float('Delay to Assign',digits=(16,2),readonly=True, group_operator="avg",help="Number of Days to open the case"),
        'delay_close': fields.float('Delay to Close',digits=(16,2),readonly=True, group_operator="avg",help="Number of Days to close the case"),
        'delay_expected': fields.float('Overpassed Deadline',digits=(16,2),readonly=True, group_operator="avg"),

        'user_id':fields.many2one('res.users', 'User', readonly=True),
        'section_id':fields.many2one('crm.case.section', 'Sales Team', readonly=True),
        'country_id':fields.many2one('res.country', 'Country', readonly=True),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
        'probability': fields.float('Probability',digits=(16,2),readonly=True, group_operator="avg"),
        'planned_revenue': fields.float('Total Revenue',digits=(16,2),readonly=True),  # TDE FIXME master: rename into total_revenue
        'probable_revenue': fields.float('Expected Revenue', digits=(16,2),readonly=True),  # TDE FIXME master: rename into expected_revenue
        'stage_id': fields.many2one ('crm.case.stage', 'Stage', readonly=True, domain="[('section_ids', '=', section_id)]"),
        'partner_id': fields.many2one('res.partner', 'Partner' , readonly=True),
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
                    c.date_deadline,
                    count(id) as nbr_cases,

                    c.date_open as opening_date,
                    c.date_closed as date_closed,

                    c.date_last_stage_update as date_last_stage_update,

                    c.user_id,
                    c.probability,
                    c.stage_id,
                    c.type,
                    c.company_id,
                    c.priority,
                    c.section_id,
                    c.campaign_id,
                    c.source_id,
                    c.medium_id,
                    c.partner_id,
                    c.country_id,
                    c.planned_revenue as planned_revenue,
                    c.planned_revenue*(c.probability/100) as probable_revenue,
                    c.create_date as create_date,
                    extract('epoch' from (c.date_closed-c.create_date))/(3600*24) as  delay_close,
                    abs(extract('epoch' from (c.date_deadline - c.date_closed))/(3600*24)) as  delay_expected,
                    extract('epoch' from (c.date_open-c.create_date))/(3600*24) as  delay_open
                FROM
                    crm_lead c
                WHERE c.active = 'true'
                GROUP BY c.id
            )""")


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
