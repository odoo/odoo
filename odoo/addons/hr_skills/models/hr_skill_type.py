# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SkillType(models.Model):
    _name = 'hr.skill.type'
    _description = "Skill Type"
    _order = "name"

    name = fields.Char(required=True)
    skill_ids = fields.One2many('hr.skill', 'skill_type_id', string="Skills")
    skill_level_ids = fields.One2many('hr.skill.level', 'skill_type_id', string="Levels")
