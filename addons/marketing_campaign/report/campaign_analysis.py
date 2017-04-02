# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import tools
from odoo import api, fields, models


class CampaignAnalysis(models.Model):
    _name = "campaign.analysis"
    _description = "Campaign Analysis"
    _auto = False
    _rec_name = 'date'

    res_id = fields.Integer('Resource', readonly=True)
    year = fields.Char('Execution Year', readonly=True)
    month = fields.Selection([
        ('01', 'January'),
        ('02', 'February'),
        ('03', 'March'),
        ('04', 'April'),
        ('05', 'May'),
        ('06', 'June'),
        ('07', 'July'),
        ('08', 'August'),
        ('09', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December')
        ], 'Execution Month', readonly=True)
    day = fields.Char('Execution Day', readonly=True)
    date = fields.Date('Execution Date', readonly=True, index=True)
    campaign_id = fields.Many2one('marketing.campaign', 'Campaign', readonly=True)
    activity_id = fields.Many2one('marketing.campaign.activity', 'Activity', readonly=True)
    segment_id = fields.Many2one('marketing.campaign.segment', 'Segment', readonly=True)
    partner_id = fields.Many2one('res.partner', 'Partner', readonly=True)
    country_id = fields.Many2one('res.country', related='partner_id.country_id', string='Country')
    total_cost = fields.Float(compute='_compute_total_cost', string='Cost')
    revenue = fields.Float('Revenue', readonly=True, digits=0)
    count = fields.Integer('# of Actions', readonly=True)
    state = fields.Selection([
        ('todo', 'To Do'),
        ('exception', 'Exception'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled')
    ], 'Status', readonly=True)

    @api.multi
    def _compute_total_cost(self):
        for analysis in self:
            wi_count = self.env['marketing.campaign.workitem'].search_count([('segment_id.campaign_id', '=', analysis.campaign_id.id)])
            analysis.total_cost = analysis.activity_id.variable_cost + ((analysis.campaign_id.fixed_cost or 1.00) / wi_count)

    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'campaign_analysis')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW campaign_analysis AS (
            SELECT
                min(wi.id) AS id,
                min(wi.res_id) AS res_id,
                to_char(wi.date::date, 'YYYY') AS year,
                to_char(wi.date::date, 'MM') AS month,
                to_char(wi.date::date, 'YYYY-MM-DD') AS day,
                wi.date::date AS date,
                s.campaign_id AS campaign_id,
                wi.activity_id AS activity_id,
                wi.segment_id AS segment_id,
                wi.partner_id AS partner_id ,
                wi.state AS state,
                sum(act.revenue) AS revenue,
                count(*) AS count
            FROM
                marketing_campaign_workitem wi
                LEFT JOIN res_partner p ON (p.id=wi.partner_id)
                LEFT JOIN marketing_campaign_segment s ON (s.id=wi.segment_id)
                LEFT JOIN marketing_campaign_activity act ON (act.id= wi.activity_id)
            GROUP BY
                s.campaign_id,wi.activity_id,wi.segment_id,wi.partner_id,wi.state,
                wi.date::date
            )
        """)
