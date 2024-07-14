# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools
from odoo import fields, models, _


def nlargest(amount, data_list, method):
    return sorted(data_list, key=method, reverse=1)[:amount]

class HrRecruitmentReport(models.Model):
    _name = "hr.recruitment.report"
    _description = "Recruitment Analysis Report"
    _auto = False
    _rec_name = 'create_date'
    _order = 'create_date desc'

    count = fields.Integer('# Applicant', group_operator="sum", readonly=True)
    refused = fields.Integer('# Refused', group_operator="sum", readonly=True)
    hired = fields.Integer('# Hired', group_operator="sum", readonly=True)
    hiring_ratio = fields.Integer('# Hired Ratio', group_operator="avg", readonly=True)
    meetings_amount = fields.Integer('# Meetings', group_operator="sum", readonly=True)

    state = fields.Selection([
        ('in_progress', 'In Progress'),
        ('is_hired', 'Hired'),
        ('refused', 'Refused'),
    ], readonly=True)

    user_id = fields.Many2one('res.users', 'Recruiter', readonly=True)

    create_date = fields.Date('Start Date', readonly=True)
    create_uid = fields.Many2one('res.users', 'Creator', readonly=True)
    date_closed = fields.Date('End Date', readonly=True)
    stage_id = fields.Many2one('hr.recruitment.stage', 'Stage', readonly=True)

    name = fields.Char('Applicant Name', readonly=True)
    job_id = fields.Many2one('hr.job', readonly=True)
    medium_id = fields.Many2one('utm.medium', readonly=True)
    source_id = fields.Many2one('utm.source', readonly=True)
    process_duration = fields.Integer('Process Duration', group_operator="avg", readonly=True)
    refuse_reason_id = fields.Many2one('hr.applicant.refuse.reason', string='Refuse Reason', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True)

    def _query(self, fields='', from_clause=''):
        select_ = """
                a.id as id,
                a.user_id,
                1 as count,
                a.create_date,
                a.create_uid,
                a.date_closed,
                a.stage_id,
                a.company_id,
                a.job_id,
                a.refuse_reason_id,
                a.medium_id,
                a.source_id,
                count(m.id) as meetings_amount,
                CASE
                    WHEN a.active IS FALSE THEN 'refused'
                    WHEN a.date_closed IS NOT NULL THEN 'is_hired'
                    ELSE 'in_progress'
                END AS state,
                CASE WHEN a.partner_name IS NOT NULL THEN a.partner_name ELSE a.name END as name,
                CASE WHEN a.active IS FALSE THEN 1 ELSE 0 END as refused,
                CASE WHEN a.date_closed IS NOT NULL THEN 1 ELSE 0 END as hired,
                CASE WHEN a.date_closed IS NOT NULL THEN 100 ELSE 0 END as hiring_ratio,
                CASE WHEN a.date_closed IS NOT NULL THEN date_part('day', a.date_closed - a.create_date) ELSE NULL END as process_duration
                %s
        """ % fields

        from_ = """
                hr_applicant a
                %s
        """ % from_clause

        join_ = """
                calendar_event m
                ON a.id = m.applicant_id
                GROUP BY a.id
        """

        return '(SELECT %s FROM %s LEFT OUTER JOIN %s)' % (select_, from_, join_)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, self._query()))

    def get_leaderboard(self):
        query = """
            SELECT
                COUNT (a.id) as count,
                p.name,
                AVG (CASE WHEN a.date_closed IS NOT NULL THEN 100 ELSE 0 END) as hiring_ratio,
                COUNT (m.id) as meetings_amount,
                SUM (CASE WHEN a.date_closed IS NOT NULL THEN 1 ELSE 0 END) as is_hired
            FROM hr_applicant a
            JOIN res_users u
            ON a.user_id = u.id
            JOIN res_partner p
            ON u.partner_id = p.id
            LEFT JOIN calendar_event m
            ON a.id = m.applicant_id
            WHERE a.company_id IN %s
            GROUP BY p.name
        """
        self._cr.execute(query, [tuple(self.env.context['allowed_company_ids'])])
        result = self._cr.dictfetchall()

        parsed_result = [
            {
                'title' : _("Total applicants"),
                'ranking_list' : [{
                        'name': x['name'],
                        'score': x['count']
                    } for x in nlargest(3, result, lambda x: x['count'])]
            },
            {
                'title' : _("Total Meetings"),
                'ranking_list' : [{
                        'name': x['name'],
                        'score': x['meetings_amount']
                    } for x in nlargest(3, result, lambda x: x['meetings_amount'])]
            },
            {
                'title' : _("Total Hired"),
                'ranking_list' : [{
                        'name': x['name'],
                        'score': x['is_hired']
                    } for x in nlargest(3, result, lambda x: x['is_hired'])]
            },
            {
                'title' : _("Hiring ratio"),
                'ranking_list' : [{
                        'name': x['name'],
                        'score': str(round(x['hiring_ratio'], 1)) + '%'
                    } for x in nlargest(3, result, lambda x: x['hiring_ratio'])]
            },
        ]

        return parsed_result
