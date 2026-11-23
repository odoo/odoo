from odoo import fields, models


class FsReport(models.Model):
    _name = 'fs.report'
    _description = 'Financial Statement Report'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True)
    report_type = fields.Selection(
        [('balance_sheet', 'As-of date (Balance Sheet)'),
         ('period', 'Date range (P&L, Cash Flow)')],
        required=True, default='balance_sheet')
    line_ids = fields.One2many('fs.report.line', 'report_id', string='Lines')

    _code_uniq = models.Constraint('unique(code)', 'Report code must be unique.')
