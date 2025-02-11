# Part of Odoo. See LICENSE file for full copyright and licensing details.

from random import randint

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class HrSkillType(models.Model):
    _name = 'hr.skill.type'
    _description = "Skill Type"
    _order = "name"

    def _get_default_color(self):
        return randint(1, 11)

    active = fields.Boolean('Active', default=True)
    name = fields.Char(required=True, translate=True)
    skill_ids = fields.One2many('hr.skill', 'skill_type_id', string="Skills")
    skill_level_ids = fields.One2many('hr.skill.level', 'skill_type_id', string="Levels", copy=True)
    color = fields.Integer('Color', default=_get_default_color)

    @api.constrains('skill_ids', 'skill_level_ids')
    def _check_no_null_skill_or_skill_level(self):
        incorrect_skill_type = self.env['hr.skill.type']
        for skill_type in self:
            if not skill_type.skill_ids or not skill_type.skill_level_ids:
                incorrect_skill_type |= skill_type
        if incorrect_skill_type:
            raise ValidationError(
                _("The following skills type must contain at least one skill and one level: %s",
                  "\n".join(skill_type.name for skill_type in incorrect_skill_type)))

    @api.onchange('skill_level_ids')
    def _onchange_skill_level_ids(self):
        for level in self.skill_level_ids:
            if level.technical_is_new_default:
                (self.skill_level_ids - level).write({'default_level': False})
                # This value need to be set to False, to reset it for the frontend.
                level.technical_is_new_default = False
                break

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        return [dict(vals, name=self.env._("%s (copy)", skill_type.name), color=0) for skill_type, vals in zip(self, vals_list)]
