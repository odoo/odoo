# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    candidate_skill_ids = fields.One2many(related="candidate_id.candidate_skill_ids", readonly=False)
    skill_ids = fields.Many2many(related="candidate_id.skill_ids", readonly=False)
    matching_score = fields.Float(string="Matching Score", compute="_compute_matching_score", search="_search_matching_score",
        help="The Matching Score reflects the match between the job positions's skills and those found in the applicant's resume.")
    expected_skill_ids = fields.Many2many(related="job_id.skill_ids")

    @api.depends('skill_ids', 'job_id.skill_ids')
    def _compute_matching_score(self):
        for applicant in self:
            if not applicant.job_id.skill_ids:
                applicant.matching_score = 0.0
            else:
                matching_skill_ids = applicant.job_id.skill_ids & applicant.skill_ids
                applicant.matching_score = (len(matching_skill_ids) / len(applicant.job_id.skill_ids))

    def _search_matching_score(self, operator, value):
        if operator in ('like', 'ilike', 'not ilike', 'not like') or isinstance(value, bool):
            raise UserError(_('Operation not supported'))
        query = f"""
            SELECT ha.id
              FROM hr_applicant AS ha
              JOIN hr_job AS hj ON hj.id = ha.job_id
              LEFT JOIN hr_candidate AS hc ON hc.id = ha.candidate_id
              LEFT JOIN hr_candidate_skill AS hcs ON hcs.candidate_id = hc.id
              LEFT JOIN hr_job_hr_skill_rel AS hjs ON hjs.hr_job_id = hj.id
              LEFT JOIN hr_skill AS hs ON hs.id = hjs.hr_skill_id
              LEFT JOIN (
                SELECT hr_job_id, COUNT(hr_skill_id) AS total_required_skills
                  FROM hr_job_hr_skill_rel
              GROUP BY hr_job_id
              ) AS required_skills ON required_skills.hr_job_id = ha.job_id
              LEFT JOIN (
                    SELECT ha.id AS applicant_id, COUNT(DISTINCT hcs.skill_id) AS total_matched_skills
                      FROM hr_applicant AS ha
                      JOIN hr_candidate AS hc ON hc.id = ha.candidate_id
                      JOIN hr_candidate_skill AS hcs ON hcs.candidate_id = hc.id
                      JOIN hr_job_hr_skill_rel AS hjs ON hjs.hr_job_id = ha.job_id
                     WHERE hcs.skill_id = hjs.hr_skill_id
                  GROUP BY ha.id
              ) AS matched_skills ON matched_skills.applicant_id = ha.id
             WHERE ha.job_id IS NOT NULL
          GROUP BY ha.id, required_skills.total_required_skills, matched_skills.total_matched_skills
            HAVING
                COALESCE((matched_skills.total_matched_skills * 100.0) / required_skills.total_required_skills, 0) {operator} {value}
        """
        self.env.cr.execute(query)
        applicant_ids = [applicant[0] for applicant in self.env.cr.fetchall()]
        return [('id', 'in', applicant_ids)]
