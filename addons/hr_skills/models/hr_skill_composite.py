# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, api, fields, models
from odoo.exceptions import ValidationError


class HrSkillComposite(models.Model):
    _name = "hr.skill.composite"
    _description = "Composition of Skill, level and type"
    _rec_name = "skill_id"
    _order = "skill_level_id"

    skill_id = fields.Many2one(
        comodel_name="hr.skill",
        compute="_compute_skill_id",
        store=True,
        domain="[('skill_type_id', '=', skill_type_id)]",
        readonly=False,
        required=True,
        ondelete="cascade",
    )
    skill_level_id = fields.Many2one(
        comodel_name="hr.skill.level",
        compute="_compute_skill_level_id",
        domain="[('skill_type_id', '=', skill_type_id)]",
        store=True,
        readonly=False,
        required=True,
        ondelete="cascade",
    )
    skill_type_id = fields.Many2one(
        comodel_name="hr.skill.type",
        required=True,
        ondelete="cascade",
    )
    level_progress = fields.Integer(related="skill_level_id.level_progress")
    is_certification = fields.Boolean(related="skill_type_id.is_certification")
    date_from = fields.Date(
        default=fields.Date.today()
    )  # should this maybe be computed? So today if it is a certification and none if not?
    date_to = fields.Date()

    @api.constrains("skill_id", "skill_type_id")
    def _check_skill_type(self):
        for composite_skill in self:
            if composite_skill.skill_id not in composite_skill.skill_type_id.skill_ids:
                raise ValidationError(
                    self.env._(
                        "The skill %(name)s and skill type %(type)s doesn't match",
                        name=composite_skill.skill_id.name,
                        type=composite_skill.skill_type_id.name,
                    ),
                )

    @api.constrains("skill_type_id", "skill_level_id")
    def _check_skill_level(self):
        for composite_skill in self:
            if composite_skill.skill_level_id not in composite_skill.skill_type_id.skill_level_ids:
                raise ValidationError(
                    self.env._(
                        "The skill level %(level)s is not valid for skill type: %(type)s",
                        level=composite_skill.skill_level_id.name,
                        type=composite_skill.skill_type_id.name,
                    ),
                )

    @api.depends("skill_type_id")
    def _compute_skill_id(self):
        for composite_skill in self:
            if composite_skill.skill_id.skill_type_id != composite_skill.skill_type_id:
                composite_skill.skill_id = False

    @api.depends("skill_id")
    def _compute_skill_level_id(self):
        for composite_skill in self:
            if not composite_skill.skill_id:
                composite_skill.skill_level_id = False
            else:
                skill_levels = composite_skill.skill_type_id.skill_level_ids
                composite_skill.skill_level_id = (
                    skill_levels.filtered("default_level") or skill_levels[0] if skill_levels else False
                )

    @api.depends("skill_id", "skill_level_id")
    def _compute_display_name(self):
        for composite_skill in self:
            composite_skill.display_name = f"{composite_skill.skill_id.name}: {composite_skill.skill_level_id.name}"

    def swap_out_skill_records(self, vals):
        target_model = self.env.context.get("target_res_model", False)
        target_id = self.env.context.get("target_res_id", False)

        if target_model and target_id:
            target_record = self.env[target_model].browse(target_id)

            new_or_existing_skill = self.create(
                {
                    "skill_id": vals.get("skill_id", self.skill_id.id),
                    "skill_type_id": vals.get("skill_type_id", self.skill_type_id.id),
                    "skill_level_id": vals.get(
                        "skill_level_id",
                        self.skill_level_id.id,
                    ),
                },
            )
            target_record.write(
                {"composite_skill_ids": [Command.unlink(self.id), Command.link(new_or_existing_skill.id)]},
            )

    def write(self, vals):
        """
        We only want to write to records when they are a certification.
        """
        if self.is_certification:
            super().write(vals)
        else:
            self.swap_out_skill_records(vals)
            super().write({})

    @api.model_create_multi
    def create(self, vals_list):
        """
        We only want one copy of each combination of a skill_name/skill_level except if it is a certification.
        """
        new_vals_list = []
        existing_skills = self.env["hr.skill.composite"]
        for vals in vals_list:
            skill_is_certification = self.env["hr.skill.type"].browse(vals["skill_type_id"]).is_certification
            if skill_is_certification:
                new_vals_list.append(vals)
            else:
                existing_composite_skill = self.env["hr.skill.composite"].search(
                    [
                        ("skill_id", "=", vals["skill_id"]),
                        ("skill_level_id", "=", vals["skill_level_id"]),
                        ("skill_type_id", "=", vals["skill_type_id"]),
                    ],
                )
                if existing_composite_skill:
                    existing_skills += existing_composite_skill
                else:
                    new_vals_list.append(vals)
        res = super().create(new_vals_list)
        return res | existing_skills
