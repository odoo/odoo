# -*- coding: utf-8 -*-
from odoo import models, fields, api

  #================================================================
  #ToDo:Allow managers to assess and assign skills to employees.DONE!
  #ToDo:linked Skills to training courses DONE!
  #ToDo:Add a new page for Skills UNDER DEVELOPMENT
  #================================================================


class EmployeeSkill(models.Model):
    _name = 'employee.skill'
    _inherit = 'hr.employee.skill'
    _description = 'Employee Skill'

    display_name = fields.Char(string='Display Name', required=True)
    description = fields.Text(string='Skill Description')

    course_ids = fields.Many2many('training.course', string='Related Courses')
