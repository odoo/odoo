# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo import tools
from odoo.addons.crm.models import crm_stage


class CrmLeadReportAssign(models.Model):
    """ CRM Lead Report """
    _name = "crm.lead.report.assign"
    _auto = False
    _description = "CRM Lead Report"

    partner_assigned_id = fields.Many2one('res.partner', 'Partner', readonly=True)
    grade_id = fields.Many2one('res.partner.grade', 'Grade', readonly=True)
    user_id = fields.Many2one('res.users', 'User', readonly=True)
    country_id = fields.Many2one('res.country', 'Country', readonly=True)
    team_id = fields.Many2one('crm.team', 'Sales Team', oldname='section_id', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    date_assign = fields.Date('Assign Date', readonly=True)
    create_date = fields.Datetime('Create Date', readonly=True)
    delay_open = fields.Float('Delay to Assign', digits=(16, 2), readonly=True, group_operator="avg", help="Number of Days to open the case")
    delay_close = fields.Float('Delay to Close', digits=(16, 2), readonly=True, group_operator="avg", help="Number of Days to close the case")
    delay_expected = fields.Float('Overpassed Deadline', digits=(16, 2), readonly=True, group_operator="avg")
    probability = fields.Float('Avg Probability', digits=(16, 2), readonly=True, group_operator="avg")
    probability_max = fields.Float('Max Probability', digits=(16, 2), readonly=True, group_operator="max")
    planned_revenue = fields.Float('Planned Revenue', digits=(16, 2), readonly=True)
    probable_revenue = fields.Float('Probable Revenue', digits=(16, 2), readonly=True)
    tag_ids = fields.Many2many('crm.lead.tag', 'crm_lead_tag_rel', 'lead_id', 'tag_id', 'Tags')
    partner_id = fields.Many2one('res.partner', 'Customer', readonly=True)
    opening_date = fields.Datetime('Opening Date', readonly=True)
    date_closed = fields.Datetime('Close Date', readonly=True)
    nbr_cases = fields.Integer('# of Cases', readonly=True, oldname='nbr')
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    priority = fields.Selection(crm_stage.AVAILABLE_PRIORITIES, 'Priority')
    type = fields.Selection([
        ('lead', 'Lead'),
        ('opportunity', 'Opportunity')
    ], 'Type', help="Type is used to separate Leads and Opportunities")

    @api.model_cr
    def init(self):
        """
            CRM Lead Report
            @param cr: the current row, from the database cursor
        """
        tools.drop_view_if_exists(self._cr, 'crm_lead_report_assign')
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
