# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrJob(models.Model):
    _inherit = "hr.job"

    applicant_matching_score = fields.Float(string="Matching Score(%)", compute="_compute_applicant_matching_score",
        groups="hr_recruitment.group_hr_recruitment_interviewer")
    matching_applicant_skill_ids = fields.Many2many(string="Matching Skills", comodel_name='hr.skill',
        compute="_compute_applicant_matching_score", groups="hr_recruitment.group_hr_recruitment_interviewer")
    missing_applicant_skill_ids = fields.Many2many(string="Missing Skills", comodel_name='hr.skill',
        compute="_compute_applicant_matching_score", groups="hr_recruitment.group_hr_recruitment_interviewer")

    @api.depends_context("active_applicant_id")
    def _compute_applicant_matching_score(self):
        active_applicant_id = self.env.context.get("active_applicant_id", [])

        applicant = self.env["hr.applicant"].browse(active_applicant_id)
        applicant_skill_map = {a.skill_id.id: a.level_progress for a in applicant.current_applicant_skill_ids}

        for job in self:
            if not active_applicant_id or not job.job_skill_ids:
                job.applicant_matching_score = False
                job.matching_applicant_skill_ids = False
                job.missing_applicant_skill_ids = False
                continue

            job_degree = job.expected_degree.score * 100
            job_total = job_degree
            applicant_degree = applicant.type_id.score * 100 if job_degree > 1 else 0
            applicant_total = applicant_degree
            for skill in job.job_skill_ids:
                job_total += skill.level_progress
                applicant_total += min(applicant_skill_map.get(skill.skill_id.id, 0), skill.level_progress * 2)

            job.applicant_matching_score = applicant_total / job_total * 100
            job.matching_applicant_skill_ids = job.skill_ids.filtered(
                lambda js: js.id in applicant_skill_map,
            )
            job.missing_applicant_skill_ids = job.skill_ids - job.matching_applicant_skill_ids

    def _compute_display_name(self):
        super()._compute_display_name()
        if self.env.context.get("show_matching_score_in_name", False):
            for job in self:
                if job.applicant_matching_score:
                    name = f"{job.display_name or job.name} \t --{job.applicant_matching_score:.0f}%--"
                    job.display_name = name.strip()

    @api.model
    def name_search(self, name='', domain=None, operator='ilike', limit=100):
        if self.env.context.get('show_matching_score_in_name'):
            records = self.search_fetch(
                domain=[('id', 'not in', self.env.context.get('active_applicant_job_ids', []))],
                field_names=['display_name'],
            )
            records = records.sorted(lambda a: (a.no_of_recruitment > 0, a.applicant_matching_score), reverse=True)[:limit]
            return [(r.id, r.display_name) for r in records]
        return super().name_search(name, domain, operator, limit)

    def action_job_add_applicants(self):
        res = super().action_job_add_applicants()
        if len(self.ids) == 1:
            res["context"]["active_job_id"] = self.id
            res["context"]["active_job_applicant_ids"] = self.application_ids.ids
        return res
