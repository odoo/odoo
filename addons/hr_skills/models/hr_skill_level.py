# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SkillLevel(models.Model):
    _name = 'hr.skill.level'
    _description = "Skill Level"
    _order = "level_progress desc"

    skill_type_id = fields.Many2one('hr.skill.type', ondelete='cascade')
    name = fields.Char(required=True)
    level_progress = fields.Integer(string="Progress", help="Progress from zero knowledge (0%) to fully mastered (100%).")
    default_level = fields.Boolean(help="If checked, this level will be the default one selected when choosing this skill.")

    _sql_constraints = [
        ('check_level_progress', 'CHECK(level_progress BETWEEN 0 AND 100)', "Progress should be a number between 0 and 100."),
    ]

    def name_get(self):
        if not self._context.get('from_skill_level_dropdown'):
            return super().name_get()
        return [(record.id, f"{record.name} ({record.level_progress}%)") for record in self]

    def create(self, vals_list):
        levels = super().create(vals_list)
        levels.skill_type_id._set_default_level()
        return levels

    def write(self, values):
        levels = super().write(values)
        self.skill_type_id._set_default_level()
        return levels

    def unlink(self):
        skill_types = self.skill_type_id
        res = super().unlink()
        skill_types._set_default_level()
        return res

    @api.constrains('default_level', 'skill_type_id')
    def _constrains_default_level(self):
        for skill_type in set(self.mapped('skill_type_id')):
            if len(skill_type.skill_level_ids.filtered('default_level')) > 1:
                raise ValidationError(_('Only one default level is allowed per skill type.'))

    def action_set_default(self):
        self.ensure_one()
        self.skill_type_id.skill_level_ids.with_context(no_skill_level_check=True).default_level = False
        self.default_level = True
