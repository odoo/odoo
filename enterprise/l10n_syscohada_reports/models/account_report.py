from odoo import fields, models


class AccountReport(models.Model):
    _inherit = 'account.report'

    availability_condition = fields.Selection(selection_add=[('coa_children', "Children of the Chart of Accounts")])

    def _is_available_for(self, options):
        if self.availability_condition == 'coa_children':
            companies = self.env['res.company'].browse(self.get_report_company_ids(options))
            for code in companies.mapped('chart_template'):
                if self.chart_template in self.env['account.chart.template']._get_parent_template(code):
                    return True

            return False

        return super()._is_available_for(options)

    def _compute_is_account_coverage_report_available(self):
        coa_children_reports = self.filtered(lambda report: report.availability_condition == 'coa_children')
        super(AccountReport, (self - coa_children_reports))._compute_is_account_coverage_report_available()

        if coa_children_reports:
            all_code_available = set(self.env['account.chart.template']._get_parent_template(self.env.company.chart_template))
            for report in coa_children_reports:
                report.is_account_coverage_report_available = self.chart_template in all_code_available
