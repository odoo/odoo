# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools
from odoo.addons.hr_recruitment.models import hr_recruitment


class HrRecruitmentReport(models.Model):
    _name = "hr.recruitment.report"
    _description = "Recruitments Statistics"
    _auto = False
    _rec_name = 'date_create'
    _order = 'date_create desc'

    active = fields.Boolean('Active')
    user_id = fields.Many2one('res.users', 'User', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    date_create = fields.Datetime('Create Date', readonly=True)
    date_last_stage_update = fields.Datetime('Last Stage Update', readonly=True)
    date_closed = fields.Date('Closed', readonly=True)
    job_id = fields.Many2one('hr.job', 'Applied Job', readonly=True)
    stage_id = fields.Many2one('hr.recruitment.stage', 'Stage')
    type_id = fields.Many2one('hr.recruitment.degree', 'Degree')
    department_id = fields.Many2one('hr.department', 'Department', readonly=True)
    priority = fields.Selection(hr_recruitment.AVAILABLE_PRIORITIES, 'Appreciation')
    salary_prop = fields.Float("Salary Proposed", digits=0)
    salary_prop_avg = fields.Float("Avg. Proposed Salary", group_operator="avg", digits=0)
    salary_exp = fields.Float("Salary Expected", digits=0)
    salary_exp_avg = fields.Float("Avg. Expected Salary", group_operator="avg", digits=0)
    partner_id = fields.Many2one('res.partner', 'Partner', readonly=True)
    delay_close = fields.Float('Avg. Delay to Close', digits=(16, 2), readonly=True, group_operator="avg", help="Number of Days to close the project issue")
    last_stage_id = fields.Many2one('hr.recruitment.stage', 'Last Stage')
    medium_id = fields.Many2one('utm.medium', 'Medium', readonly=True, help="This is the method of delivery. Ex: Postcard, Email, or Banner Ad")
    source_id = fields.Many2one('utm.source', 'Source', readonly=True, help="This is the source of the link Ex: Search Engine, another domain, or name of email list")

    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self._cr, 'hr_recruitment_report')
        self._cr.execute("""
            create or replace view hr_recruitment_report as (
                 select
                     min(s.id) as id,
                     s.active,
                     s.create_date as date_create,
                     date(s.date_closed) as date_closed,
                     s.date_last_stage_update as date_last_stage_update,
                     s.partner_id,
                     s.company_id,
                     s.user_id,
                     s.job_id,
                     s.type_id,
                     s.department_id,
                     s.priority,
                     s.stage_id,
                     s.last_stage_id,
                     s.medium_id,
                     s.source_id,
                     sum(salary_proposed) as salary_prop,
                     (sum(salary_proposed)/count(*)) as salary_prop_avg,
                     sum(salary_expected) as salary_exp,
                     (sum(salary_expected)/count(*)) as salary_exp_avg,
                     extract('epoch' from (s.write_date-s.create_date))/(3600*24) as delay_close,
                     count(*) as nbr
                 from hr_applicant s
                 group by
                     s.active,
                     s.date_open,
                     s.create_date,
                     s.write_date,
                     s.date_closed,
                     s.date_last_stage_update,
                     s.partner_id,
                     s.company_id,
                     s.user_id,
                     s.stage_id,
                     s.last_stage_id,
                     s.type_id,
                     s.priority,
                     s.job_id,
                     s.department_id,
                     s.medium_id,
                     s.source_id
            )
        """)
