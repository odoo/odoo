from odoo import Command, api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class HrApplicant(models.Model):
    _inherit = ["mixin.hr.individual.skill.owner", "hr.applicant"]

    applicant_skill_ids = fields.One2many(
        comodel_name="hr.applicant.skill",
        inverse_name="applicant_id",
        string="Skills",
        copy=True,
    )
    current_applicant_skill_ids = fields.One2many(
        comodel_name="hr.applicant.skill",
        inverse_name="applicant_id",
        compute="_compute_current_individual_skill_ids",
        search="_search_current_individual_skill_ids",
        readonly=False,
    )
    skill_ids = fields.Many2many(
        comodel_name="hr.skill",
        compute="_compute_skill_ids",
        store=True,
    )
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
    matching_score = fields.Integer(compute="_compute_matching_skill_ids")

    def _individual_skill_field_name(self):
        return "applicant_skill_ids"

    def _current_individual_skill_field_name(self):
        return "current_applicant_skill_ids"

    @api.depends("applicant_skill_ids.skill_id")
    def _compute_skill_ids(self):
        for applicant in self:
            applicant.skill_ids = applicant.applicant_skill_ids.skill_id

    def _get_skill_match(self, job):
        self.check_singleton()
        requirements = job.current_job_skill_ids
        required_progress = {
            requirement.skill_id: requirement.level_progress
            for requirement in requirements
        }
        job_degree = job.expected_degree.sudo().score * 100
        matching = self.current_applicant_skill_ids.filtered(
            lambda skill: skill.skill_id in required_progress
        )
        job_total = sum(required_progress.values()) + job_degree
        applicant_total = sum(
            min(skill.level_progress, required_progress[skill.skill_id] * 2)
            for skill in matching
        ) + (self.degree_id.score * 100 if job_degree > 1 else 0)
        _debug.logic(
            "skill_match",
            applicant=self,
            job=job,
            required=len(required_progress),
            matched=matching,
            job_total=job_total,
            applicant_total=applicant_total,
        )
        return {
            "matching_skills": matching.skill_id,
            "missing_skills": requirements.skill_id - matching.skill_id,
            "score": applicant_total / job_total * 100 if job_total else 0,
        }

    @api.depends_context("matching_job_id")
    @api.depends(
        "current_applicant_skill_ids",
        "degree_id",
        "job_id",
        "job_id.current_job_skill_ids",
        "job_id.expected_degree",
    )
    def _compute_matching_skill_ids(self):
        matching_job = self.env["hr.job"].browse(
            self.env.context.get("matching_job_id")
        )
        for applicant in self:
            job = matching_job or applicant.job_id
            if not job or not (job.current_job_skill_ids or job.expected_degree):
                _debug.logic("skill_match_skipped", applicant=applicant, job=job)
                applicant.matching_skill_ids = False
                applicant.missing_skill_ids = False
                applicant.matching_score = False
                continue
            match = applicant._get_skill_match(job)
            applicant.matching_skill_ids = match["matching_skills"]
            applicant.missing_skill_ids = match["missing_skills"]
            applicant.matching_score = round(match["score"])

    def _prepare_employee_vals(self):
        vals = super()._prepare_employee_vals()
        _debug.pipeline(
            "skills_carried_to_employee",
            applicant=self,
            skills=self.current_applicant_skill_ids,
        )
        vals["employee_skill_ids"] = [
            Command.create(
                {
                    "skill_id": applicant_skill.skill_id.id,
                    "skill_level_id": applicant_skill.skill_level_id.id,
                    "skill_type_id": applicant_skill.skill_type_id.id,
                    "valid_from": applicant_skill.valid_from,
                    "valid_to": applicant_skill.valid_to,
                }
            )
            for applicant_skill in self.current_applicant_skill_ids
        ]
        return vals

    def _map_applicant_skill_ids_to_talent_skill_ids(self, vals):
        own_skills = {row.id: row for row in self.applicant_skill_ids}
        talent_row_by_skill = {
            row.skill_id: row.id for row in self.pool_applicant_id.applicant_skill_ids
        }

        def talent_row_of(row_id):
            row = own_skills.get(row_id)
            return row and talent_row_by_skill.get(row.skill_id)

        mapped_commands = []
        _debug.pipeline(
            "skill_commands_mapped_to_talent",
            applicant=self,
            talent=self.pool_applicant_id,
            own=len(own_skills),
        )
        for command in vals.get("applicant_skill_ids"):
            match command[0]:
                case Command.UPDATE:
                    if talent_row_id := talent_row_of(command[1]):
                        mapped_commands.append(
                            Command.update(talent_row_id, command[2])
                        )
                    elif row := own_skills.get(command[1]):
                        mapped_commands.append(
                            Command.create(
                                {
                                    "skill_id": row.skill_id.id,
                                    "skill_type_id": row.skill_type_id.id,
                                    "skill_level_id": command[2].get(
                                        "skill_level_id", row.skill_level_id.id
                                    ),
                                }
                            )
                        )
                case Command.DELETE | Command.UNLINK:
                    if talent_row_id := talent_row_of(command[1]):
                        mapped_commands.append(Command.delete(talent_row_id))
                case Command.LINK:
                    if talent_row_id := talent_row_of(command[1]):
                        mapped_commands.append(Command.link(talent_row_id))
                case Command.SET:
                    mapped_commands.append(
                        Command.set(
                            [
                                talent_row_id
                                for row_id in command[2]
                                if (talent_row_id := talent_row_of(row_id))
                            ]
                        )
                    )
                case _:
                    mapped_commands.append(command)
        return mapped_commands

    def action_add_to_job(self):
        self.with_context(just_moved=True).write(
            {
                "job_id": self.env["hr.job"]
                .browse(self.env.context.get("matching_job_id"))
                .id,
                "stage_id": self.env.ref("hr_recruitment.stage_job0").id,
            }
        )
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "hr_recruitment.action_hr_job_applications"
        )
        action["context"] = self.env["ir.actions.actions"]._eval_action_context(
            action["context"], active_id=self.job_id.id
        )
        return action

    def write(self, vals):
        """A pool applicant mirrors the skills of the applicants drawn from it,
        so the raw commands are mapped onto its rows before the mixin turns
        them into the versioned form."""
        command_fields = set(self._individual_skill_command_field_names())
        if command_fields & vals.keys():
            skills = []
            for field_name in self._individual_skill_command_field_names():
                skills += vals.get(field_name) or []
            for applicant in self:
                if applicant.pool_applicant_id and not applicant.is_pool_applicant:
                    applicant.pool_applicant_id.write(
                        {
                            "applicant_skill_ids": (
                                applicant._map_applicant_skill_ids_to_talent_skill_ids(
                                    {"applicant_skill_ids": skills}
                                )
                            )
                        }
                    )
        return super().write(vals)
