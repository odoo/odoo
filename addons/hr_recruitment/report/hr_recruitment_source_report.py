# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools
from odoo import api, fields, models


class HrRecruitmentSourceReport(models.Model):
    _name = "hr.recruitment.source.report"
    _description = "Recruitment Sources Report"
    _auto = False

    applicant = fields.Integer('# Applicant', group_operator="sum", readonly=True)
    hired = fields.Integer('# Hired', group_operator="sum", readonly=True)
    refused = fields.Integer('# Refused', group_operator="sum", readonly=True)
    cost = fields.Integer('Source Cost', group_operator="sum", readonly=True)

    cost_by_applicant = fields.Integer('Cost by Applicant', group_operator="avg", readonly=True)
    cost_by_hired = fields.Integer('Cost by Hired', group_operator="avg", readonly=True)
    cost_by_refused = fields.Integer('Cost by Refused', group_operator="avg", readonly=True)

    job_id = fields.Many2one('hr.job', readonly=True)
    source_id = fields.Many2one('utm.source', readonly=True)
    campaign_id = fields.Many2one('utm.campaign', readonly=True)

    process_duration = fields.Integer('Process Duration', group_operator="avg", readonly=True)

    def _query(self, fields='', from_clause='', left_join_clause='', groupby_fields=''):
        select_ = """
                  s.id as id,
                  s.job_id,
                  s.campaign_id,
                  s.source_id,
                  cost,
                  count(a.id) as applicant,
                  SUM(CASE WHEN a.date_closed IS NOT NULL THEN 1 ELSE 0 END) as hired,
                  SUM(CASE WHEN a.active IS FALSE THEN 1 ELSE 0 END) as refused,
                  AVG(CASE WHEN a.date_closed IS NOT NULL THEN date_part('day', a.date_closed - a.create_date) ELSE NULL END) as process_duration,
                  (cost/NULLIF(count(a.id),0)) as cost_by_applicant,
                  (cost/NULLIF(SUM(CASE WHEN a.date_closed IS NOT NULL THEN 1 ELSE 0 END),0)) as cost_by_hired,
                  (cost/NULLIF(SUM(CASE WHEN a.active IS FALSE THEN 1 ELSE 0 END),0)) as cost_by_refused
                  %s
        """ % fields

        from_ = """
                hr_recruitment_source s
                %s
        """ % from_clause

        left_join_ = """
                    LEFT JOIN hr_applicant a on (a.job_id = s.job_id AND
                                                a.campaign_id = s.campaign_id AND
                                                a.source_id = s.source_id)
                     %s
        """ % left_join_clause

        groupby_ = """
                   s.id,
                   s.campaign_id,
                   s.source_id,
                   s.job_id,
                   cost
                   %s
        """ % groupby_fields

        return '(SELECT %s FROM %s %s GROUP BY %s)' % (select_, from_, left_join_, groupby_)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, self._query()))
