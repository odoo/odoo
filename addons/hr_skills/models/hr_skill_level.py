from odoo import api, fields, models


class HrSkillLevel(models.Model):
    _name = "hr.skill.level"
    _description = "Skill Level"
    _order = "level_progress, id"

    skill_type_id = fields.Many2one(
        comodel_name="hr.skill.type",
        index=True,
        required=True,
        ondelete="cascade",
    )
    name = fields.Char(required=True)
    level_progress = fields.Integer(
        string="Progress",
        help="Progress from zero knowledge (0%) to fully mastered (100%).",
    )
    default_level = fields.Boolean(
        help="If checked, this level will be the default one selected when choosing this skill."
    )

    technical_is_new_default = fields.Boolean(
        compute="_compute_technical_is_new_default",
        readonly=False,
    )

    _check_level_progress = models.Constraint(
        "CHECK(level_progress BETWEEN 0 AND 100)",
        "Progress should be a number between 0 and 100.",
    )

    @api.constrains("skill_type_id")
    def _check_skill_type_id(self):
        self.env["mixin.hr.individual.skill"]._check_library_type_matches_rows(
            self, "skill_level_id"
        )

    def _compute_technical_is_new_default(self):
        self.technical_is_new_default = False

    @api.model_create_multi
    def create(self, vals_list):
        skill_levels = super().create(vals_list)
        skill_levels._demote_other_default_levels()
        return skill_levels

    def write(self, vals):
        res = super().write(vals)
        if vals.get("default_level"):
            self._demote_other_default_levels()
        return res

    def _demote_other_default_levels(self):
        promoted = self.filtered("default_level")
        if not promoted:
            return
        keep = {level.skill_type_id: level for level in promoted}
        for skill_type, level in keep.items():
            (skill_type.skill_level_ids - level).default_level = False
