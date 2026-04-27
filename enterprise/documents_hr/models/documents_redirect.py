from odoo import fields, models


class DocumentRedirect(models.Model):
    _inherit = "documents.redirect"

    # Add the employee for URLs already sent
    employee_id = fields.Many2one("hr.employee")
