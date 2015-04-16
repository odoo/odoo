# -*- coding: utf-8 -*-

from openerp import fields, models, tools
from openerp.addons.crm.models import crm

class CrmOpportunityReport(models.Model):
    """ CRM Opportunity Analysis """
    _name = "crm.opportunity.report"
    _auto = False
    _description = "CRM Opportunity Analysis"
    _rec_name = 'date_deadline'
    _inherit = ["utm.mixin"]

    date_deadline = fields.Date(string='Exp. Closing', readonly=True, help="Expected Closing")
    create_date = fields.Datetime(string='Creation Date', readonly=True)
    opening_date = fields.Datetime(string='Assignation Date', readonly=True)
    date_closed = fields.Datetime(string='Close Date', readonly=True)
    date_last_stage_update = fields.Datetime(string='Last Stage Update', readonly=True)
    nbr_cases = fields.Integer(string="# of Cases", readonly=True)

    # durations
    delay_open = fields.Float(string='Delay to Assign', digits=(16,2), readonly=True, group_operator="avg", help="Number of Days to open the case")
    delay_close = fields.Float(string='Delay to Close', digits=(16,2), readonly=True, group_operator="avg", help="Number of Days to close the case")
    delay_expected = fields.Float(string='Overpassed Deadline', digits=(16,2), readonly=True, group_operator="avg")
    user_id = fields.Many2one('res.users', string='User', readonly=True)
    team_id = fields.Many2one('crm.team', string='Sales Team', oldname='section_id', readonly=True)
    country_id = fields.Many2one('res.country', string='Country', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    probability = fields.Float(digits=(16,2), readonly=True, group_operator="avg")
    total_revenue = fields.Float(string='Total Revenue', digits=(16,2), readonly=True)
    expected_revenue = fields.Float(string='Expected Revenue', digits=(16,2), readonly=True)
    stage_id = fields.Many2one('crm.stage', string='Stage', readonly=True, domain="[('team_ids', '=', team_id)]")
    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    priority = fields.Selection(crm.AVAILABLE_PRIORITIES)
    type = fields.Selection([
        ('lead','Lead'),
        ('opportunity','Opportunity')
    ], help="Type is used to separate Leads and Opportunities")
    lost_reason = fields.Many2one('crm.lost.reason', string='Lost Reason', readonly=True)
    date_conversion = fields.Datetime(string='Conversion Date', readonly=True)
    
    
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
                    extract('epoch' from (c.date_open-c.create_date))/(3600*24) as  delay_open,
                    c.lost_reason,
                    c.date_conversion as date_conversion
                FROM
                    crm_lead c
                WHERE c.active = 'true'
                GROUP BY c.id
            )""")
