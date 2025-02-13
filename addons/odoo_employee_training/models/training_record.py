# -*- coding: utf-8 -*-
from odoo import models, fields, api

  #===========================================================================================================
  #==== PIPELINE ============ EMPLOYEE INFO ==> TRAINING COURSE ==> TRAINING RECORD ==========================
  #===========================================================================================================

  #ToDo:Record when an employee completes a course (Date, Trainer, Score/Result if applicable)DONE!
  #ToDo:Allow for attaching certificates or other relevant documents.DONE!


class TrainingRecord(models.Model):
    _name = 'training.record'
    _description = 'Training Record'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    course_id = fields.Many2one('training.course', string='Course', required=True)
    completion_date = fields.Date(string='Completion Date')
    trainer = fields.Char(string='Trainer')
    result = fields.Char(string='Result')
    certificate_attachment = fields.Binary(string='Certificate')
