# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class EmployeeSkill(models.Model):
    _name = 'hr.employee.skill'
    _description = "Skill level for an employee"
    _rec_name = 'skill_id'
    _order = "skill_type_id, skill_level_id"

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

    def _create_logs(self):
        today = fields.Date.context_today(self)
        skill_to_create_vals = []
        for employee_skill in self:
            existing_log = self.env['hr.employee.skill.log'].search([
                ('employee_id', '=', employee_skill.employee_id.id),
                ('department_id', '=', employee_skill.employee_id.department_id.id),
                ('skill_id', '=', employee_skill.skill_id.id),
                ('date', '=', today),
            ])
            if existing_log:
                existing_log.write({'skill_level_id': employee_skill.skill_level_id.id})
            else:
                skill_to_create_vals.append({
                    'employee_id': employee_skill.employee_id.id,
                    'skill_id': employee_skill.skill_id.id,
                    'skill_level_id': employee_skill.skill_level_id.id,
                    'department_id': employee_skill.employee_id.department_id.id,
                    'skill_type_id': employee_skill.skill_type_id.id,
                })
        if skill_to_create_vals:
            self.env['hr.employee.skill.log'].create(skill_to_create_vals)

    @api.model_create_multi
    def create(self, vals_list):
        employee_skills = super().create(vals_list)
        employee_skills._create_logs()
        return employee_skills

    def write(self, vals):
        res = super().write(vals)
        self._create_logs()
        return res
