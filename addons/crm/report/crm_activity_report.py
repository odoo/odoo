# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools


class CrmActivityReport(models.Model):
    """ CRM Lead Analysis """
    _name = "crm.activity.report"
    _auto = False
    _description = "CRM Activity Analysis"
    _rec_name = 'id'

    date = fields.Datetime('Date', readonly=True)
    author_id = fields.Many2one('res.partner', 'Author', readonly=True)
    user_id = fields.Many2one('res.users', 'Responsible', readonly=True)
    team_id = fields.Many2one('crm.team', 'Sales Team', readonly=True)
    lead_id = fields.Many2one('crm.lead', "Lead", readonly=True)
    subject = fields.Char('Summary', readonly=True)
    subtype_id = fields.Many2one('mail.message.subtype', 'Activity', readonly=True)
    country_id = fields.Many2one('res.country', 'Country', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    stage_id = fields.Many2one('crm.stage', 'Stage', readonly=True)
    partner_id = fields.Many2one('res.partner', 'Partner/Customer', readonly=True)
    lead_type = fields.Char(
        string='Type',
        selection=[('lead', 'Lead'), ('opportunity', 'Opportunity')],
        help="Type is used to separate Leads and Opportunities")
    active = fields.Boolean('Active', readonly=True)
    probability = fields.Float('Probability', group_operator='avg', readonly=True)

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'crm_activity_report')
        cr.execute("""
            CREATE OR REPLACE VIEW crm_activity_report AS (
                select
                    m.id,
                    m.subtype_id,
                    m.author_id,
                    m.date,
                    m.subject,
                    l.id as lead_id,
                    l.user_id,
                    l.team_id,
                    l.country_id,
                    l.company_id,
                    l.stage_id,
                    l.partner_id,
                    l.type as lead_type,
                    l.active,
                    l.probability
                from
                    "mail_message" m
                join
                    "crm_lead" l
                on
                    (m.res_id = l.id)
                WHERE
                    (m.model = 'crm.lead')
            )""")
