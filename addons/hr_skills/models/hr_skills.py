# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class Skill(models.Model):
    _name = 'hr.skill'
    _description = "Skill"
    _order = "sequence"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    skill_type_id = fields.Many2one('hr.skill.type', required=True, ondelete='cascade')

    def name_get(self):
        if not self._context.get('from_skill_dropdown'):
            return super().name_get()
        return [(record.id, f"{record.name} ({record.skill_type_id.name})") for record in self]


class EmployeeSkill(models.Model):
    _name = 'hr.employee.skill'
    _description = "Skill level for an employee"
    _rec_name = 'skill_id'
    _order = "skill_level_id"

    employee_id = fields.Many2one('hr.employee', required=True, ondelete='cascade')
    skill_id = fields.Many2one('hr.skill', compute='_compute_skill_id', store=True, domain="[('skill_type_id', '=', skill_type_id)]", readonly=False, required=True)
    skill_level_id = fields.Many2one('hr.skill.level', compute='_compute_skill_level_id', domain="[('skill_type_id', '=', skill_type_id)]", store=True, readonly=False, required=True)
    skill_type_id = fields.Many2one('hr.skill.type', required=True)
    level_progress = fields.Integer(related='skill_level_id.level_progress')

    _sql_constraints = [
        ('_unique_skill', 'unique (employee_id, skill_id)', "Two levels for the same skill is not allowed"),
    ]

    @api.constrains('skill_id', 'skill_type_id')
    def _check_skill_type(self):
        for record in self:
            if record.skill_id not in record.skill_type_id.skill_ids:
                raise ValidationError(_("The skill %(name)s and skill type %(type)s doesn't match", name=record.skill_id.name, type=record.skill_type_id.name))

    @api.constrains('skill_type_id', 'skill_level_id')
    def _check_skill_level(self):
        for record in self:
            if record.skill_level_id not in record.skill_type_id.skill_level_ids:
                raise ValidationError(_("The skill level %(level)s is not valid for skill type: %(type)s", level=record.skill_level_id.name, type=record.skill_type_id.name))

    @api.depends('skill_type_id')
    def _compute_skill_id(self):
        for record in self:
            if record.skill_id.skill_type_id != record.skill_type_id:
                record.skill_id = False

    @api.depends('skill_id')
    def _compute_skill_level_id(self):
        for record in self:
            if not record.skill_id:
                record.skill_level_id = False
            else:
                skill_levels = record.skill_type_id.skill_level_ids
                record.skill_level_id = skill_levels.filtered('default_level') or skill_levels[0] if skill_levels else False


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

class SkillType(models.Model):
    _name = 'hr.skill.type'
    _description = "Skill Type"

    name = fields.Char(required=True)
    skill_ids = fields.One2many('hr.skill', 'skill_type_id', string="Skills")
    skill_level_ids = fields.One2many('hr.skill.level', 'skill_type_id', string="Levels")

    def _set_default_level(self):
        if self.env.context.get('no_skill_level_check'):
            return

        for types in self:
            if not types.skill_level_ids.filtered('default_level'):
                types.skill_level_ids[:1].default_level = True
