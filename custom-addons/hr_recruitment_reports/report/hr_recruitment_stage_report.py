# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools
from odoo import fields, models

from psycopg2 import sql

class HrRecruitmentStageReport(models.Model):
    _name = 'hr.recruitment.stage.report'
    _description = 'Recruitment Stage Analysis'
    _auto = False

    applicant_id = fields.Many2one('hr.applicant', readonly=True)
    name = fields.Char('Applicant Name', readonly=True)
    stage_id = fields.Many2one('hr.recruitment.stage', readonly=True)
    job_id = fields.Many2one('hr.job', readonly=True)
    days_in_stage = fields.Float(readonly=True, group_operator='avg')

    state = fields.Selection([
        ('is_hired', 'Hired'),
        ('in_progress', 'In Progress'),
        ('refused', 'Refused'),
    ], readonly=True)

    company_id = fields.Many2one('res.company', readonly=True)
    date_begin = fields.Date('Start Date', readonly=True)
    date_end = fields.Date('End Date', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(sql.SQL("""CREATE OR REPLACE VIEW {} AS (
SELECT
    ROW_NUMBER() OVER () AS ID,
    ha.id AS applicant_id,
    ha.partner_name AS name,
    ha.job_id AS job_id,
    ha.company_id AS company_id,
    CASE
        WHEN ha.active IS FALSE THEN 'refused'
        WHEN ha.date_closed IS NOT NULL THEN 'is_hired'
        ELSE 'in_progress'
    END AS state,
    COALESCE(LAG(mm.date) OVER (PARTITION BY mm.res_id ORDER BY mm.id), ha.create_date) AS date_begin,
    mm.date AS date_end,
    EXTRACT(EPOCH FROM mm.date - COALESCE(LAG(mm.date) OVER (PARTITION by mm.res_id ORDER BY mm.id), ha.create_date))/(24*60*60)::decimal(16,2) AS days_in_stage,
    CASE WHEN EXISTS(SELECT 1 from hr_recruitment_stage WHERE id = mtv.old_value_integer)
        THEN mtv.old_value_integer
        ELSE NULL
    END AS stage_id
FROM
    hr_applicant ha
JOIN
    mail_message mm
ON
    mm.res_id = ha.id
    AND mm.model = 'hr.applicant'
JOIN
    mail_tracking_value mtv
ON
    mtv.mail_message_id = mm.id
JOIN
    ir_model_fields imf
ON
    mtv.field_id = imf.id
    AND imf.model = 'hr.applicant'
    AND imf.name = 'stage_id'

UNION ALL

SELECT
    ROW_NUMBER() OVER () AS id,
    ha.id AS applicant_id,
    ha.partner_name AS name,
    ha.job_id AS job_id,
    ha.company_id AS company_id,
    CASE
        WHEN ha.active IS FALSE THEN 'refused'
        WHEN ha.date_closed IS NOT NULL THEN 'is_hired'
        ELSE 'in_progress'
    END AS state,
    COALESCE(md.date, ha.create_date) AS date_begin,
    NOW() AT TIME ZONE 'utc' AS date_end,
    EXTRACT(EPOCH FROM NOW() AT TIME ZONE 'utc' - COALESCE(md.date, ha.create_date))/(24*60*60)::decimal(16,2) AS days_in_stage,
    ha.stage_id
FROM
    hr_applicant ha
JOIN
    hr_recruitment_stage hrs
ON
    hrs.id = ha.stage_id
LEFT JOIN LATERAL (
    SELECT
        mm.date
    FROM
        mail_message mm
    JOIN
        mail_tracking_value mtv
    ON
        mm.id = mtv.mail_message_id
    JOIN
        ir_model_fields imf
    ON
        mtv.field_id = imf.id
        AND imf.model = 'hr.applicant'
        AND imf.name = 'stage_id'
    WHERE
        mm.res_id = ha.id
        AND mm.model = 'hr.applicant'
    ORDER BY mm.id desc
    FETCH FIRST ROW ONLY
) md ON TRUE
WHERE
    hrs.hired_stage IS NOT TRUE
)""").format(sql.Identifier(self._table)))
