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
from openerp import models, fields, api
from openerp import tools


class crm_opportunity_report(models.Model):
    """ CRM Opportunity Analysis """
    _name = "crm.opportunity.report"
    _auto = False
    _description = "CRM Opportunity Analysis"
    _rec_name = 'date_deadline'
    _inherit = ["crm.tracking.mixin"]

    date_deadline = fields.Date('Exp. Closing', readonly=True, help="Expected Closing")
    create_date = fields.Datetime('Creation Date', readonly=True)
    opening_date = fields.Datetime('Assignation Date', readonly=True)
    date_closed = fields.Datetime('Close Date', readonly=True)
    date_last_stage_update = fields.Datetime('Last Stage Update', readonly=True)
    nbr_cases = fields.Integer("# of Cases", readonly=True)

    # durations
    delay_open = fields.Float('Delay to Assign',digits=(16,2),readonly=True, group_operator="avg",help="Number of Days to open the case")
    delay_close = fields.Float('Delay to Close',digits=(16,2),readonly=True, group_operator="avg",help="Number of Days to close the case")
    delay_expected = fields.Float('Overpassed Deadline',digits=(16,2),readonly=True, group_operator="avg")

    user_id = fields.Many2one('res.users', 'User', readonly=True)
    team_id = fields.Many2one('crm.team', 'Sales Team', readonly=True)
    country_id =fields.Many2one('res.country', 'Country', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    probability = fields.Float('Probability',digits=(16,2),readonly=True, group_operator="avg")
    total_revenue = fields.Float('Total Revenue',digits=(16,2),readonly=True)
    expected_revenue = fields.Float('Expected Revenue', digits=(16,2),readonly=True)
    stage_id = fields.Many2one('crm.stage', 'Stage', readonly=True, domain="[('team_ids', '=', team_id)]")
    partner_id = fields.Many2one('res.partner', 'Partner' , readonly=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    priority = fields.Selection(crm.AVAILABLE_PRIORITIES, 'Priority'),
    type =fields.Selection([
        ('lead','Lead'),
        ('opportunity','Opportunity')
    ],'Type', help="Type is used to separate Leads and Opportunities")


#TODO: require to migrate when base method migrate
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'crm_opportunity_report')
        cr.execute("""
            CREATE OR REPLACE VIEW crm_opportunity_report AS (
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
                    c.team_id,
                    c.campaign_id,
                    c.source_id,
                    c.medium_id,
                    c.partner_id,
                    c.country_id,
                    c.planned_revenue as total_revenue,
                    c.planned_revenue*(c.probability/100) as expected_revenue,
                    c.create_date as create_date,
                    extract('epoch' from (c.date_closed-c.create_date))/(3600*24) as  delay_close,
                    abs(extract('epoch' from (c.date_deadline - c.date_closed))/(3600*24)) as  delay_expected,
                    extract('epoch' from (c.date_open-c.create_date))/(3600*24) as  delay_open
                FROM
                    crm_lead c
                WHERE c.active = 'true'
                GROUP BY c.id,
                    c.date_deadline,
                    c.date_open,
                    c.date_deadline,
                    c.date_open ,
                    c.date_closed,
                    c.date_last_stage_update,
                    c.user_id,
                    c.probability,
                    c.stage_id,
                    c.type,
                    c.company_id,
                    c.priority,
                    c.team_id,
                    c.campaign_id,
                    c.source_id,
                    c.medium_id,
                    c.partner_id,
                    c.country_id,
                    c.planned_revenue,
                    c.create_date
            )""")
