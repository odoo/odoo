# Part of Odoo. See LICENSE file for full copyright and licensing details.

from random import randint
from odoo import fields, models


class SkillType(models.Model):
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

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        return [dict(vals, name=self.env._("%s (copy)", skill_type.name), color=0) for skill_type, vals in zip(self, vals_list)]
