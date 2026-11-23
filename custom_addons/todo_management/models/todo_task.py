from odoo import models, fields, api
from odoo.exceptions import ValidationError

class TodoTask(models.Model):
    _name = 'todo.task'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'To-Do Task'

    ref = fields.Char(default='New', readonly=True)
    name = fields.Char('Task Name', required=True, tracking=True)
    description = fields.Text('Description')
    assigned_to = fields.Many2one('res.users', string='Assigned To',tracking=1, required=True)
    due_date = fields.Date('Due Date')
    status = fields.Selection([
        ('new', 'New'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('closed', 'Closed'),
    ], string='Status', default='new')
    estimated_time = fields.Float('Estimated Time (hours)')
    lines_ids = fields.One2many('timesheet.entry', 'task_id', string='Task Lines')
    active = fields.Boolean('Active', default=True)
    is_late = fields.Boolean(default=False, string='Is Late?', tracking=1)

    @api.model_create_multi
    def create(self,vals):
        res = super(TodoTask,self).create(vals)
        for rec in res:
            rec.ref = self.env['ir.sequence'].next_by_code('todo.sequence') or 'New'
            rec.status = 'in_progress'
            rec.message_post(body=f"Task '{rec.name}' has been created and assigned to {rec.assigned_to.name}.")
        return res

    def action_close_task(self):
        for rec in self:
            rec.status = 'closed'
            rec.message_post(body=f"Task '{rec.name}' has been closed.")

    def check_past_due_tasks(self):
        task_ids = self.search([])
        for rec in task_ids:
            if rec.due_date and rec.due_date < fields.Date.today() and rec.status not in ['completed', 'closed']:
                rec.is_late = True



class TimeSheetEntry(models.Model):
    _name = 'timesheet.entry'
    _description = 'Timesheet Entry'

    task_id = fields.Many2one('todo.task', string='Task', required=True)
    due_date = fields.Date('Due Date')
    description = fields.Text('Description')
    hours_spent = fields.Float('Hours Spent')

    @api.constrains('hours_spent')
    def _check_total_hours(self):
        for rec in self:
            total_hours = sum(entry.hours_spent for entry in rec.task_id.lines_ids)
            if total_hours > rec.task_id.estimated_time:
                raise ValidationError("Total hours spent cannot exceed the estimated time for the task.")

