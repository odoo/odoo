# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrEmployeeSkillLog(models.Model):
    _name = 'hr.employee.skill.log'
    _description = "Skills History"
    _rec_name = 'skill_id'
    _order = "employee_id,date"

    employee_id = fields.Many2one('hr.employee', required=True, ondelete='cascade')
    department_id = fields.Many2one('hr.department')
    skill_id = fields.Many2one('hr.skill', compute='_compute_skill_id', store=True, domain="[('skill_type_id', '=', skill_type_id)]", readonly=False, required=True, ondelete='cascade')
    skill_level_id = fields.Many2one('hr.skill.level', compute='_compute_skill_level_id', domain="[('skill_type_id', '=', skill_type_id)]", store=True, readonly=False, required=True, ondelete='cascade')
    skill_type_id = fields.Many2one('hr.skill.type', required=True, ondelete='cascade')
    level_progress = fields.Integer(related='skill_level_id.level_progress', store=True, aggregator="avg")
    date = fields.Date(default=fields.Date.context_today)

    _sql_constraints = [
        ('_unique_skill_log', 'unique (employee_id, department_id, skill_id, date)', "Two levels for the same skill on the same day is not allowed"),
    ]
