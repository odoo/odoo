# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval

from odoo import fields, models, Command, api


class HrApplicant(models.Model):
    _inherit = "hr.applicant"

    applicant_skill_ids = fields.One2many(
        "hr.applicant.skill", "applicant_id", string="Skills", copy=True
    )
    skill_ids = fields.Many2many("hr.skill", compute="_compute_skill_ids", store=True)
    matching_skill_ids = fields.Many2many(
        comodel_name="hr.skill",
        string="Matching Skills",
        compute="_compute_matching_skill_ids",
    )
    missing_skill_ids = fields.Many2many(
        comodel_name="hr.skill",
        string="Missing Skills",
        compute="_compute_matching_skill_ids",
    )
    matching_score = fields.Float(
        string="Matching Score(%)", compute="_compute_matching_skill_ids"
    )

    @api.depends("applicant_skill_ids.skill_id")
    def _compute_skill_ids(self):
        for applicant in self:
            applicant.skill_ids = applicant.applicant_skill_ids.skill_id

    @api.depends_context("active_id")
    @api.depends("skill_ids")
    def _compute_matching_skill_ids(self):
        job_id = self.env.context.get("active_id")
        if not job_id:
            self.matching_skill_ids = False
            self.missing_skill_ids = False
            self.matching_score = 0
        else:
            for applicant in self:
                job_skills = self.env["hr.job"].browse(job_id).skill_ids
                applicant.matching_skill_ids = job_skills & applicant.skill_ids
                applicant.missing_skill_ids = job_skills - applicant.skill_ids
                applicant.matching_score = (
                    (len(applicant.matching_skill_ids) / len(job_skills)) * 100
                    if job_skills
                    else 0
                )

    def _get_employee_create_vals(self):
        vals = super()._get_employee_create_vals()
        vals["employee_skill_ids"] = [
            (
                0,
                0,
                {
                    "skill_id": applicant_skill.skill_id.id,
                    "skill_level_id": applicant_skill.skill_level_id.id,
                    "skill_type_id": applicant_skill.skill_type_id.id,
                },
            )
            for applicant_skill in self.applicant_skill_ids
        ]
        return vals

    def _map_applicant_skill_ids_to_talent_skill_ids(self, vals):
        """
        The applicant_skills_ids contains a list of ORM tuples i.e (command, record ID, {values})
        The challenge lies in the uniqueness of the record ID in this tuple. Each skill (e.g., 'arabic')
        has a distinct ID per applicant, i.e arabic in applicant 1 will have a different id from arabic in
        applicant 2. This means the content of applicant_skills_ids is unique for each record and attempting
        to pass it directly (e.g., applicant.pool_applicant_id.write(vals)) won't yield results so we must
        update each tuple to have the correct command and record ID for the talent pool applicant

        Returns:
            returns a list of create/update/delete commands with skill_ids relevant to the pool_applicant
        """
        applicant_skills = {a.id: a.skill_id.id for a in self.applicant_skill_ids}
        applicant_skills_type = {a.id: a.skill_type_id.id for a in self.applicant_skill_ids}
        talent_skills = {a.skill_id.id: a.id for a in self.pool_applicant_id.applicant_skill_ids}
        translated_skills = []
        for skill in vals["applicant_skill_ids"]:
            command = skill[0]
            record_id = skill[1]
            if command == 0:
                values = skill[2]
                if values["skill_id"] in talent_skills:
                    translated_skill = Command.update(
                        talent_skills[values["skill_id"]],
                        {"skill_level_id": values["skill_level_id"]},
                    )
                    translated_skills.append(translated_skill)
                else:
                    translated_skills.append(skill)
            elif command == 1:
                values = skill[2]
                if applicant_skills[record_id] in talent_skills:
                    translated_skill = Command.update(talent_skills[applicant_skills[record_id]], values)
                    translated_skills.append(translated_skill)
                else:
                    translated_skill = Command.create(
                        {
                            "skill_id": applicant_skills[record_id],
                            "skill_type_id": applicant_skills_type[record_id],
                            "skill_level_id": values["skill_level_id"],
                        }
                    )
                    translated_skills.append(translated_skill)
            elif command == 2:
                if applicant_skills[record_id] in talent_skills:
                    translated_skill = Command.delete(talent_skills[applicant_skills[record_id]])
                    translated_skills.append(translated_skill)
        return translated_skills

    def action_add_to_job(self):
        self.with_context(just_moved=True).write(
            {
                "job_id": self.env["hr.job"].browse(self.env.context.get("active_id")).id,
                "stage_id": self.env.ref("hr_recruitment.stage_job0").id,
            }
        )
        action = self.env["ir.actions.actions"]._for_xml_id("hr_recruitment.action_hr_job_applications")
        action["context"] = literal_eval(action["context"].replace("active_id", str(self.job_id.id)))
        return action

    def write(self, vals):
        if (
            "applicant_skill_ids" in vals
            and self.pool_applicant_id
            and (not self.is_pool_applicant)
        ):
            for applicant in self:
                translated_skills = applicant._map_applicant_skill_ids_to_talent_skill_ids(vals)
                applicant.pool_applicant_id.write(
                    {"applicant_skill_ids": translated_skills}
                )
        res = super().write(vals)
        return res
