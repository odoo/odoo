from odoo import models, fields

  #ToDo:handle the relationships between employees,courses, and training plans.DONE!
  #ToDo:handle the relationships between employees ,skills UNDER DEVELOPMENT!


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # Link to training courses
    training_course_ids = fields.One2many('training.course', 'employee_id', string='Training Courses')
    
    # Link to training records
    training_record_ids = fields.One2many('training.record', 'employee_id', string='Training Records')

    # Link to training plans
    training_plan_ids = fields.One2many('training.plan', 'employee_id', string='Training Plans')

    # Link to skills
    skill_ids = fields.One2many('employee.skill','employee_id', string='Skills')

    