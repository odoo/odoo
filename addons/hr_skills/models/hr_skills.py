# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class Employee(models.Model):
    _inherit = 'hr.employee'

    employee_skill_ids = fields.One2many('hr.employee.skill', 'employee_id', string="Skills", ondelete='cascade')

class Skill(models.Model):
    _name = 'hr.skill'
    _description = "Skill"

    name = fields.Char(required=True)
    skill_type_id = fields.Many2one('hr.skill.type')

class EmployeeSkill(models.Model):
    _name = 'hr.employee.skill'
    _description = "Skill level for an employee"

    employee_id = fields.Many2one('hr.employee', required=True)
    skill_id = fields.Many2one('hr.skill', required=True)
    skill_level_id = fields.Many2one('hr.skill.level', required=True)
    skill_type_id = fields.Many2one('hr.skill.type', required=True)
    progress = fields.Integer(related='skill_level_id.progress')

    _sql_constraints = [
        ('_unique_skill', 'unique (employee_id, skill_id)', "Two levels for the same skill is not allowed"),
    ]

    @api.constrains('skill_id', 'skill_type_id')
    def _check_skill_type(self):
        for record in self:
            if record.skill_id not in record.skill_type_id.skill_ids:
                raise ValidationError(_("The skill and skill type doesn't match"))

    @api.constrains('skill_type_id', 'skill_level_id')
    def _check_skill_type(self):
        for record in self:
            if record.skill_level_id not in record.skill_type_id.skill_level_ids:
                raise ValidationError(_("The skill and skill type doesn't match"))

class SkillLevel(models.Model):
    _name = 'hr.skill.level'
    _description = "Skill Level"

    skill_type_id = fields.Many2one('hr.skill.type')
    name = fields.Char(required=True)
    progress = fields.Integer(help="Progress from zero knowledge (0%) to fully mastered (100%).")
    sequence = fields.Integer(default=100)

class SkillType(models.Model):
    _name = 'hr.skill.type'
    _description = "Skill Type"

    name = fields.Char(required=True)
    skill_ids = fields.One2many('hr.skill', 'skill_type_id', string="Skills", ondelete='cascade')
    skill_level_ids = fields.One2many('hr.skill.level', 'skill_type_id', string="Levels", ondelete='cascade')