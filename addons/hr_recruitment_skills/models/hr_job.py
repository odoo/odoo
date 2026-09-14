from markupsafe import Markup

from odoo import api, fields, models


class HrJob(models.Model):
    _inherit = "hr.job"

    applicant_matching_score = fields.Float(
        string="Matching Score(%)",
        compute="_compute_applicant_matching_score",
        groups="hr_recruitment.group_hr_recruitment_interviewer",
    )

    @api.depends_context("active_applicant_id")
    def _compute_applicant_matching_score(self):
        applicant = self.env["hr.applicant"].browse(
            self.env.context.get("active_applicant_id")
        )
        for job in self:
            job.applicant_matching_score = (
                applicant._get_skill_match(job)["score"]
                if applicant and job.current_job_skill_ids
                else False
            )

    def action_search_matching_applicants(self):
        self.check_singleton()
        help_message_1 = self.env._("No Matching Applicants")
        help_message_2 = self.env._(
            "We do not have any applicants who meet the skill requirements for this job position in the database at the moment."
        )
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "hr_recruitment.crm_case_categ0_act_job"
        )
        context = self.env["ir.actions.actions"]._eval_action_context(action["context"])
        context["matching_job_id"] = self.id
        action.update(
            {
                "name": self.env._("Matching Applicants"),
                "views": [
                    (
                        self.env.ref(
                            "hr_recruitment_skills.crm_case_tree_view_inherit_hr_recruitment_skills"
                        ).id,
                        "list",
                    ),
                    (False, "form"),
                ],
                "context": context,
                "domain": [
                    ("job_id", "!=", self.id),
                    (
                        "current_applicant_skill_ids",
                        "any",
                        [("skill_id", "in", self.current_job_skill_ids.skill_id.ids)],
                    ),
                ],
                "help": Markup(
                    "<p class='o_view_nocontent_empty_folder'>%s</p><p>%s</p>"
                )
                % (help_message_1, help_message_2),
            }
        )
        return action
