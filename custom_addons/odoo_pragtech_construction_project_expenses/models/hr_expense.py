from odoo import models, fields, api, _

class HrExpense(models.Model):
    _inherit = "hr.expense"
    
    project_id = fields.Many2one('project.project',string='Project')