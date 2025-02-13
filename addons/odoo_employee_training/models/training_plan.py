# -*- coding: utf-8 -*-
from odoo import models, fields, api

  #===========================================================================================================
  #==== PIPELINE ============ EMPLOYEE INFO ==> TRAINING PLAN ==> TRAINING COURSE ============================
  #===========================================================================================================

  #ToDo: Allow managers to create training plans for employees or roles.DONE!
  #ToDo: A plan should outline the required courses and their due dates.DONE!
  #ToDo: Track the progress of employees against their plans.DONE!


class TrainingPlan(models.Model):
    _name = 'training.plan'
    _description = 'Training Plan'
    _rec_name = 'name'

    name = fields.Char(string='Plan Name', required=True, default=lambda self: self.env['ir.sequence'].next_by_code('training.plan'))
    employee_id = fields.Many2one('hr.employee', string='Employee')
    role_id = fields.Many2one('hr.job', string='Role')
    course_ids = fields.Many2many('training.course', string='Courses')
    due_date = fields.Date(string='Due Date')
    progress = fields.Float(string='Progress', compute='_compute_progress')

    
    @api.depends('course_ids')
    def _compute_progress(self):
        for plan in self:
            completed_courses = len(plan.course_ids.filtered(lambda c: c in plan.employee_id.training_record_ids.mapped('course_id')))
            total_courses = len(plan.course_ids)
            plan.progress = (completed_courses / total_courses) * 100 if total_courses > 0 else 0

    
    def _notify_overdue_training(self):
        today = fields.Date.today()
        overdue_plans = self.search([('due_date', '<', today), ('progress', '<', 100)])
        for plan in overdue_plans:
            template = self.env.ref('odoo_employee_training.email_template_overdue_training')
            self.env['mail.template'].browse(template.id).send_mail(plan.id)
