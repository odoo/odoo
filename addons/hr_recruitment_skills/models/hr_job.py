from ast import literal_eval

from markupsafe import Markup

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

    def _compute_display_name(self):
        super()._compute_display_name()
        if self.env.context.get("show_matching_score_in_name", False):
            for job in self:
                if job.applicant_matching_score:
                    name = f"{job.display_name or job.name} \t --{job.applicant_matching_score:.2f}%--"
                    job.display_name = name.strip()

    def sort_by_applicant_matching_score(self):
        for seq, job in enumerate(self.sorted(lambda a: (a.no_of_recruitment > 0, a.applicant_matching_score), reverse=True)):
            job.sequence = seq
