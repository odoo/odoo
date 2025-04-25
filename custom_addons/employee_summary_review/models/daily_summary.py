import logging
_logger = logging.getLogger(__name__)
_logger.info(">>> LOADED: DailySummary model <<<")

from odoo import models, fields, api    

class DailySummary(models.Model):
    _name = 'daily.summary'
    _description = 'Employee Daily Work Summary'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(string="Title", required=True)
    employee_id = fields.Many2one('hr.employee', string="Employee", required=True, 
                                 default=lambda self: self.env.user.employee_id)
    date = fields.Date(default=fields.Date.today)
    work_description = fields.Text(string="Work Summary", required=True)
    reviewed = fields.Boolean(string="Reviewed", default=False)
    review_ids = fields.One2many('summary.review', 'summary_id', string="Reviews")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('reviewed', 'Reviewed')
    ], default='draft', tracking=True)

    def action_submit(self):
        self.write({'state': 'submitted'})

    def action_review(self):
        self.write({'state': 'reviewed'})
