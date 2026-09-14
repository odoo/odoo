from odoo import Command, api, fields, models
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class HrSkillType(models.Model):
    _name = "hr.skill.type"
    _inherit = ["mixin.color"]
    _description = "Skill Type"
    _order = "sequence, name"

    active = fields.Boolean(default=True)
    sequence = fields.Integer()
    name = fields.Char(
        translate=True,
        required=True,
    )
    skill_ids = fields.One2many(
        comodel_name="hr.skill",
        inverse_name="skill_type_id",
        string="Skills",
    )
    skill_level_ids = fields.One2many(
        comodel_name="hr.skill.level",
        inverse_name="skill_type_id",
        string="Levels",
        copy=True,
    )
    color = fields.Integer(default=lambda self: self._default_color())
    levels_count = fields.Integer(
        compute="_compute_levels_count",
        store=True,
        help="Number of levels linked to this skill type",
    )
    is_certification = fields.Boolean(
        string="Certification",
        help="if checked the skill type become a certification type",
    )

    @api.model
    def _get_certification_type(self):
        return self.search([("is_certification", "=", True)], limit=1)

    @api.constrains("skill_ids", "skill_level_ids")
    def _check_no_null_skill_or_skill_level(self):
        incorrect_skill_type = self.env["hr.skill.type"]
        for skill_type in self:
            if not skill_type.skill_ids or not skill_type.skill_level_ids:
                incorrect_skill_type |= skill_type
        if incorrect_skill_type:
            _debug.logic("skill_type_incomplete", types=incorrect_skill_type)
            raise ValidationError(
                self.env._(
                    "The following skills type must contain at least one skill and one level: %s",
                    "\n".join(skill_type.name for skill_type in incorrect_skill_type),
                )
            )

    @api.depends("name", "is_certification")
    def _compute_display_name(self):
        for skill_type in self:
            if skill_type.is_certification:
                skill_type.display_name = skill_type.name + "\U0001f396"
            else:
                skill_type.display_name = skill_type.name

    @api.depends("skill_level_ids")
    def _compute_levels_count(self):
        for skill_type in self:
            skill_type.levels_count = len(skill_type.skill_level_ids)

    @api.onchange("skill_level_ids")
    def _onchange_skill_level_ids(self):
        for level in self.skill_level_ids:
            if level.technical_is_new_default:
                (self.skill_level_ids - level).write({"default_level": False})
                level.technical_is_new_default = False
                break

    def copy_data(self, default=None):
        default = default or {}
        vals_list = super().copy_data(default=default)
        _debug.lifecycle("skill_type_copied", types=self, overrides=list(default))
        for skill_type, vals in zip(self, vals_list, strict=True):
            if "name" not in default:
                vals["name"] = self.env._(
                    "%(skill_type_name)s (copy)", skill_type_name=skill_type.name
                )
            if "color" not in default:
                vals["color"] = 0
            if "skill_ids" not in default:
                vals["skill_ids"] = [
                    Command.create(skill_vals)
                    for skill_vals in skill_type.skill_ids.copy_data()
                ]
        return vals_list

    def copy_translations(self, new, excluded=()):
        super().copy_translations(new, excluded=(*excluded, "name"))
        self._copy_translations_of_renamed_field(
            new,
            "name",
            lambda record, term: record.env._(
                "%(skill_type_name)s (copy)", skill_type_name=term
            ),
        )
