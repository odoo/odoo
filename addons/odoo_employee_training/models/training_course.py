# -*- coding: utf-8 -*-
from odoo import models, fields, api

  #===========================================================================================================
  #==== PIPELINE ============ EMPLOYEE INFO ==> TRAINING COURSE =============================================
  #===========================================================================================================

  #ToDo:Maintain a list of training courses (Title, Description, Duration, etc.)DONE!
  #ToDo:Categorize Courses (Technical ,Soft Skills, Saftey)DONE!


class TrainingCourse(models.Model):
    _name = 'training.course'
    _description = 'Training Course'

    name = fields.Char(string='Course Title', required=True)
    employee_id = fields.Many2one('hr.employee', string='Employee')
    description = fields.Text(string='Course Description')
    duration = fields.Float(string='Duration (hours)')
    category_id = fields.Many2one('training.course.category', string='Category')

class TrainingCourseCategory(models.Model):
    _name = 'training.course.category'
    _description = 'Training Course Category'

    name = fields.Char(string='Category', required=True)
