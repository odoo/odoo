from odoo import api, fields, models


class HrSkill(models.Model):
    _name = "hr.skill"
    _description = "Skill"
    _order = "sequence, name, id"

    name = fields.Char(
        translate=True,
        required=True,
    )
    sequence = fields.Integer(default=10)
    skill_type_id = fields.Many2one(
        comodel_name="hr.skill.type",
        index=True,
        required=True,
        ondelete="cascade",
    )
    color = fields.Integer(related="skill_type_id.color")

    @api.constrains("skill_type_id")
    def _check_skill_type_id(self):
        self.env["mixin.hr.individual.skill"]._check_library_type_matches_rows(
            self, "skill_id"
        )

    @api.depends("skill_type_id")
    @api.depends_context("from_skill_dropdown")
    def _compute_display_name(self):
        if not self.env.context.get("from_skill_dropdown"):
            super()._compute_display_name()
            return
        for record in self:
            record.display_name = f"{record.name} ({record.skill_type_id.name})"
