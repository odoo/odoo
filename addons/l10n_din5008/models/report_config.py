from odoo import fields, models


class ReportConfig(models.Model):
    _inherit = "report.config"

    has_position_column = fields.Boolean(string="Show Position Column in Reports")
