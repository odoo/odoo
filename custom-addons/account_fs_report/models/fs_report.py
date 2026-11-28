import re

from odoo import fields, models


class FsReport(models.Model):
    _name = 'fs.report'
    _description = 'Financial Statement Report'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True)
    report_type = fields.Selection(
        [('balance_sheet', 'As-of date (Balance Sheet)'),
         ('period', 'Date range (P&L)'),
         ('cash_flow', 'Cash Flow Statement (Direct)')],
        required=True, default='balance_sheet')
    line_ids = fields.One2many('fs.report.line', 'report_id', string='Lines')

    _code_uniq = models.Constraint('unique(code)', 'Report code must be unique.')

    def get_default_report_filename(self, options, extension):
        """Match Enterprise account.report.get_default_report_filename."""
        self.ensure_one()

        def transform_period(period=""):
            dates_match = re.findall(r'\d{2}/\d{2}/\d{4}', period or '')
            if dates_match:
                return '_'.join(d.replace('/', '') for d in dates_match)
            return (period or '').replace(' ', '_').replace('_-_', '_').lower()

        def company_name(companies):
            if companies and len(companies) == 1:
                return f"_{companies[0]['name'].replace(' ', '_').lower()}"
            return ""

        companies = options.get('companies')
        if not companies:
            company_ids = options.get('company_ids') or []
            if len(company_ids) == 1:
                company = self.env['res.company'].browse(company_ids[0])
                companies = [{'name': company.name, 'id': company.id}] if company else []
            else:
                companies = []

        period = (options.get('date') or {}).get('string') or ''
        if not period:
            columns = options.get('columns') or []
            if columns:
                period = columns[0].get('name') or columns[0].get('label') or ''

        return f"{self.name.lower().replace(' ', '_')}_{transform_period(period)}{company_name(companies)}.{extension}"
