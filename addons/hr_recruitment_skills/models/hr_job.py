from ast import literal_eval

from markupsafe import Markup

from odoo import api, fields, models


class HrJob(models.Model):
    _inherit = "hr.job"

    applicant_matching_score = fields.Float(string="Matching Score(%)", compute="_compute_applicant_matching_score",
        groups="hr_recruitment.group_hr_recruitment_interviewer")

    @api.depends_context("active_applicant_id")
    def _compute_applicant_matching_score(self):
        active_applicant_id = self.env.context.get("active_applicant_id")
        if not active_applicant_id:
            for job in self:
                job.applicant_matching_score = False
            return

        applicant = self.env["hr.applicant"].browse(active_applicant_id)
        for job in self:
            if not job.job_skill_ids:
                job.applicant_matching_score = False
                continue
            job_skills = job.job_skill_ids
            job_degree = job.expected_degree.score * 100
            job_total = sum(job.job_skill_ids.mapped("level_progress")) + job_degree
            job_skill_map = {js.skill_id.id: js.level_progress for js in job_skills}

            matching_applicant_skills = applicant.current_applicant_skill_ids.filtered(
                lambda a: a.skill_id.id in job_skill_map,
            )
            applicant_degree = applicant.type_id.score * 100 if job_degree > 1 else 0
            applicant_total = (
                sum(
                    min(skill.level_progress, job_skill_map[skill.skill_id.id] * 2)
                    for skill in matching_applicant_skills
                )
                + applicant_degree
            )

            job.applicant_matching_score = applicant_total / job_total * 100

    def action_search_matching_applicants(self):
        self.ensure_one()
        help_message_1 = self.env._("No Matching Applicants")
        help_message_2 = self.env._("We do not have any applicants who meet the skill requirements for this job position in the database at the moment.")
        action = self.env['ir.actions.actions']._for_xml_id('hr_recruitment.crm_case_categ0_act_job')
        context = literal_eval(action['context'])
        context['matching_job_id'] = self.id
        action.update({
            'name': self.env._("Matching Applicants"),
            'views': [
                (self.env.ref('hr_recruitment_skills.crm_case_tree_view_inherit_hr_recruitment_skills').id, 'list'),
                (False, 'form'),
            ],
            'context': context,
            'domain': [
                ('job_id', '!=', self.id),
                ('skill_ids', 'in', self.job_skill_ids.skill_id.ids),
            ],
            'help': Markup("<p class='o_view_nocontent_empty_folder'>%s</p><p>%s</p>") % (help_message_1, help_message_2),
        })
        return action
