# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools
from odoo import api, fields, models, _


class HrReferralReport(models.Model):
    _name = "hr.referral.report"
    _description = "Employee Referral Report"
    _auto = False
    _rec_name = 'ref_user_id'
    _order = 'write_date desc, earned_points desc'

    write_date = fields.Date(string='Last Update Date', readonly=True)
    earned_points = fields.Integer('Earned Points', readonly=True)
    points_not_hired = fields.Integer('Points Given For Not Hired', readonly=True)
    applicant_id = fields.Many2one('hr.applicant', readonly=True)
    employee_referral_hired = fields.Integer('Employee Referral Hired', readonly=True)
    employee_referral_refused = fields.Integer('Employee Referral Refused', readonly=True)
    ref_user_id = fields.Many2one('res.users', 'User', readonly=True)
    job_id = fields.Many2one('hr.job', readonly=True)
    department_id = fields.Many2one('hr.department', readonly=True)
    medium_id = fields.Many2one('utm.medium', readonly=True)
    referral_state = fields.Selection([
        ('progress', 'In Progress'),
        ('hired', 'Hired'),
        ('closed', 'Not Hired')], readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)

    def init(self):
        query = '''
            (SELECT
                a.id as id,
                a.id as applicant_id,
                a.write_date as write_date,
                points as earned_points,
                points_not_hired as points_not_hired,
                a.referral_state as referral_state,
                a.ref_user_id as ref_user_id,
                job_id,
                department_id,
                company_id,
                m.id as medium_id,
                CASE WHEN a.referral_state = 'hired' THEN 1 ELSE 0 END as employee_referral_hired,
                CASE WHEN a.referral_state = 'closed' THEN 1 ELSE 0 END as employee_referral_refused
            FROM
                hr_applicant a
                LEFT JOIN
                    (SELECT applicant_id, SUM(points) as points
                    FROM hr_referral_points
                    GROUP BY applicant_id) point ON a.id = point.applicant_id
                LEFT JOIN
                    (SELECT applicant_id, SUM(points) as points_not_hired
                    FROM hr_referral_points
                    GROUP BY applicant_id) points_not_hired ON (a.id = points_not_hired.applicant_id AND a.referral_state = 'closed')
                LEFT JOIN utm_medium m ON medium_id = m.id
            WHERE
                a.ref_user_id IS NOT NULL
            )
        '''

        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, query), (_('Direct Referral'),))
