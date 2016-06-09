# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools import drop_view_if_exists
from odoo.addons.crm import crm_stage


class CrmLeadReportAssign(models.Model):
    """ CRM Lead Report """
    _name = "crm.lead.report.assign"
    _auto = False
    _description = "CRM Lead Report"

    partner_assigned_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    grade_id = fields.Many2one('res.partner.grade', string='Grade', readonly=True)
    user_id = fields.Many2one('res.users', string='User', readonly=True)
    country_id = fields.Many2one('res.country', string='Country', readonly=True)
    team_id = fields.Many2one('crm.team', string='Sales Team', oldname='section_id', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    date_assign = fields.Date(string='Assign Date', readonly=True)
    create_date = fields.Datetime(string='Create Date', readonly=True)
    delay_open = fields.Float(string='Delay to Assign',digits=(16,2), readonly=True, group_operator="avg", help="Number of Days to open the case")
    delay_close = fields.Float(string='Delay to Close', digits=(16,2), readonly=True, group_operator="avg", help="Number of Days to close the case")
    delay_expected = fields.Float(string='Overpassed Deadline', digits=(16,2), readonly=True, group_operator="avg")
    probability = fields.Float(string='Avg Probability', digits=(16,2), readonly=True, group_operator="avg")
    probability_max = fields.Float(string='Max Probability',digits=(16,2),readonly=True, group_operator="max")
    planned_revenue = fields.Float(string='Planned Revenue',digits=(16,2), readonly=True)
    probable_revenue = fields.Float(string='Probable Revenue', digits=(16,2), readonly=True)
    tag_ids = fields.Many2many('crm.lead.tag', 'crm_lead_tag_rel', 'lead_id', 'tag_id', string='Tags')
    partner_id = fields.Many2one('res.partner', 'Customer' , readonly=True)
    opening_date = fields.Datetime(string='Opening Date', readonly=True)
    date_closed = fields.Datetime(string='Close Date', readonly=True)
    nbr = fields.Integer(string='# of Cases', readonly=True)  # TDE FIXME master: rename into nbr_cases
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    priority = fields.Selection(crm_stage.AVAILABLE_PRIORITIES, string='Priority')
    type = fields.Selection([
        ('lead','Lead'),
        ('opportunity','Opportunity')
    ], string='Type', help="Type is used to separate Leads and Opportunities")

    @api.model_cr
    def init(self):
        drop_view_if_exists(self._cr, 'crm_lead_report_assign')
        self._cr.execute("""
            CREATE OR REPLACE VIEW crm_lead_report_assign AS (
                SELECT
                    c.id,
                    c.date_open as opening_date,
                    c.date_closed as date_closed,
                    c.date_assign,
                    c.user_id,
                    c.probability,
                    c.probability as probability_max,
                    c.type,
                    c.company_id,
                    c.priority,
                    c.team_id,
                    c.partner_id,
                    c.country_id,
                    c.planned_revenue,
                    c.partner_assigned_id,
                    p.grade_id,
                    p.date as partner_date,
                    c.planned_revenue*(c.probability/100) as probable_revenue,
                    1 as nbr,
                    c.create_date as create_date,
                    extract('epoch' from (c.write_date-c.create_date))/(3600*24) as  delay_close,
                    extract('epoch' from (c.date_deadline - c.date_closed))/(3600*24) as  delay_expected,
                    extract('epoch' from (c.date_open-c.create_date))/(3600*24) as  delay_open
                FROM
                    crm_lead c
                    left join res_partner p on (c.partner_assigned_id=p.id)
            )""")
