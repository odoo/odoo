# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.addons.account_reports.models.account_report import AccountReportFileDownloadException


class TestSaftReport(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        company = cls.company_data['company']
        cls.ReportException = AccountReportFileDownloadException
        cls.ReportModel = cls.env.ref('account_reports.general_ledger_report')
        cls.ReportHandlerModel = cls.env[cls.ReportModel.custom_handler_model_name]
        cls.report_handler = cls.ReportHandlerModel.with_company(company)

    def _generate_options(self, date_from='2023-10-01', date_to='2023-10-31'):
        return super()._generate_options(self.ReportModel, date_from, date_to)
