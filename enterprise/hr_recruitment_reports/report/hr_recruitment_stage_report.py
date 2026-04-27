# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools.sql import drop_view_if_exists, SQL


class HrRecruitmentStageReport(models.Model):
    _name = 'hr.recruitment.stage.report'
    _description = 'Recruitment Stage Analysis'
    _auto = False

    applicant_id = fields.Many2one('hr.applicant', readonly=True)
    name = fields.Char('Applicant Name', readonly=True)
    stage_id = fields.Many2one('hr.recruitment.stage', readonly=True)
    job_id = fields.Many2one('hr.job', readonly=True)
    days_in_stage = fields.Float(readonly=True, aggregator='avg')

    state = fields.Selection([
        ('is_hired', 'Hired'),
        ('in_progress', 'In Progress'),
        ('refused', 'Refused'),
        ('archived', 'Archived'),
    ], readonly=True)

    company_id = fields.Many2one('res.company', readonly=True)
    date_begin = fields.Date('Start Date', readonly=True)
    date_end = fields.Date('End Date', readonly=True)

    def init(self):
        drop_view_if_exists(self.env.cr, self._table)
        query = """
WITH application_stage_history AS (
SELECT
    ha.id AS applicant_id,
    c.partner_name AS name,
    ha.job_id AS job_id,
    ha.company_id AS company_id,
    CASE
        WHEN ha.active IS FALSE and ha.refuse_reason_id IS NOT NULL THEN 'refused'
        WHEN ha.active IS FALSE and ha.refuse_reason_id IS NULL THEN 'archived'
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
    hr_candidate c
ON
    c.id = ha.candidate_id
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
),
current_application_stage AS (
SELECT
    ha.id AS applicant_id,
    c.partner_name AS name,
    ha.job_id AS job_id,
    ha.company_id AS company_id,
    CASE
        WHEN ha.active IS FALSE AND ha.refuse_reason_id IS NOT NULL THEN 'refused'
        WHEN ha.active IS FALSE AND ha.refuse_reason_id IS NULL THEN 'archived'
        WHEN ha.date_closed IS NOT NULL THEN 'is_hired'
        ELSE 'in_progress'
    END AS state,
    COALESCE(md.date, ha.create_date) AS date_begin,
    NOW() AT TIME ZONE 'utc' AS date_end,
	CASE
		WHEN ha.refuse_date IS NOT NULL THEN ABS(EXTRACT(EPOCH FROM md.date - COALESCE (ha.refuse_date, ha.create_date)))/(24*60*60)
		ELSE
	EXTRACT(EPOCH FROM NOW() AT TIME ZONE 'utc' - COALESCE(md.date, ha.create_date))/(24*60*60)
	END AS days_in_stage,
    ha.stage_id
FROM
    hr_applicant ha
JOIN
    hr_candidate c
ON
    c.id = ha.candidate_id
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
),
global_cte AS(
    SELECT applicant_id, name, job_id, company_id, state, date_begin, date_end, days_in_stage, stage_id FROM application_stage_history
    UNION ALL
    SELECT applicant_id, name, job_id, company_id, state, date_begin, date_end, days_in_stage, stage_id FROM current_application_stage
)
SELECT
    ROW_NUMBER() OVER (ORDER BY date_begin) AS id, applicant_id, name, job_id, company_id, state, date_begin, date_end, days_in_stage, stage_id
    FROM global_cte
        """
        self.env.cr.execute(SQL("CREATE OR REPLACE VIEW %s AS (%s)", SQL.identifier(self._table), SQL(query)))
