import logging
_logger = logging.getLogger(__name__)
_logger.info(">>> LOADED: DailySummary model <<<")

from odoo import models, fields, api    

class DailySummary(models.Model):
    _name = 'daily.summary'
    _description = 'Employee Daily Work Summary'

    name = fields.Char(string="Title", required=True)
    employee_id = fields.Many2one('hr.employee', string="Employee", required=True, default=lambda self: self.env.user.employee_id)
    date = fields.Date(default=fields.Date.today)
    work_description = fields.Text(string="Work Summary", required=True)
    reviewed = fields.Boolean(string="Reviewed", default=False)
    review_ids = fields.One2many('summary.review', 'summary_id', string="Reviews")
