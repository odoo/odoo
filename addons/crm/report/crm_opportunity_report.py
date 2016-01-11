# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools
from odoo.addons.crm.models import crm_stage


class CrmOpportunityReport(models.Model):
    """ CRM Opportunity Analysis """
    _name = "crm.opportunity.report"
    _auto = False
    _description = "CRM Opportunity Analysis"
    _rec_name = 'date_deadline'

    date_deadline = fields.Date(string='Expected Closing', readonly=True)
    create_date = fields.Datetime(string='Creation Date', readonly=True)
    opening_date = fields.Datetime(string='Assignation Date', readonly=True)
    date_closed = fields.Datetime(string='Close Date', readonly=True)
    date_last_stage_update = fields.Datetime(string='Last Stage Update', readonly=True)
    active = fields.Boolean(readonly=True)

    # durations
    delay_open = fields.Float(string='Delay to Assign', digits=(16, 2), readonly=True, group_operator="avg", help="Number of Days to open the case")
    delay_close = fields.Float(string='Delay to Close', digits=(16, 2), readonly=True, group_operator="avg", help="Number of Days to close the case")
    delay_expected = fields.Float(string='Overpassed Deadline', digits=(16, 2), readonly=True, group_operator="avg")
    user_id = fields.Many2one('res.users', string='User', readonly=True)
    team_id = fields.Many2one('crm.team', 'Sales Team', oldname='section_id', readonly=True)
    nbr_activities = fields.Integer(string='# of Activities', readonly=True)
    city = fields.Char('City')
    country_id = fields.Many2one('res.country', string='Country', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    probability = fields.Float(string='Probability', digits=(16, 2), readonly=True, group_operator="avg")
    total_revenue = fields.Float(string='Total Revenue', digits=(16, 2), readonly=True)
    expected_revenue = fields.Float(string='Expected Revenue', digits=(16, 2), readonly=True)
    stage_id = fields.Many2one('crm.stage', string='Stage', readonly=True, domain="[('team_ids', '=', team_id)]")
    stage_name = fields.Char(string='Stage Name', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    priority = fields.Selection(crm_stage.AVAILABLE_PRIORITIES, string='Priority')
    type = fields.Selection([
            ('lead', 'Lead'),
            ('opportunity', 'Opportunity'),
        ], string='Type', help="Type is used to separate Leads and Opportunities")
    lost_reason = fields.Many2one('crm.lost.reason', string='Lost Reason', readonly=True)
    date_conversion = fields.Datetime(string='Conversion Date', readonly=True)
    campaign_id = fields.Many2one('utm.campaign', string='Campaign', readonly=True)
    source_id = fields.Many2one('utm.source', string='Source', readonly=True)
    medium_id = fields.Many2one('utm.medium', string='Medium', readonly=True)

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'crm_opportunity_report')
        cr.execute("""
            CREATE OR REPLACE VIEW crm_opportunity_report AS (
                SELECT
                    c.id,
                    c.date_deadline,

                    c.date_open as opening_date,
                    c.date_closed as date_closed,
                    c.date_last_stage_update as date_last_stage_update,

                    c.user_id,
                    c.probability,
                    c.stage_id,
                    stage.name as stage_name,
                    c.type,
                    c.company_id,
                    c.priority,
                    c.team_id,
                    activity.nbr_activities,
                    c.active,
                    c.campaign_id,
                    c.source_id,
                    c.medium_id,
                    c.partner_id,
                    c.city,
                    c.country_id,
                    c.planned_revenue as total_revenue,
                    c.planned_revenue*(c.probability/100) as expected_revenue,
                    c.create_date as create_date,
                    extract('epoch' from (c.date_closed-c.create_date))/(3600*24) as  delay_close,
                    abs(extract('epoch' from (c.date_deadline - c.date_closed))/(3600*24)) as  delay_expected,
                    extract('epoch' from (c.date_open-c.create_date))/(3600*24) as  delay_open,
                    c.lost_reason,
                    c.date_conversion as date_conversion
                FROM
                    "crm_lead" c
                LEFT JOIN (
                    SELECT m.res_id, COUNT(*) nbr_activities
                    FROM "mail_message" m
                    WHERE m.model = 'crm.lead'
                    GROUP BY m.res_id ) activity
                ON
                    (activity.res_id = c.id)
                LEFT JOIN "crm_stage" stage
                ON stage.id = c.stage_id
                GROUP BY c.id, activity.nbr_activities, stage.name
            )""")
