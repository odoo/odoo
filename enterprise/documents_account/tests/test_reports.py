# -*- coding: utf-8 -*-

from odoo import fields
from odoo.tests import tagged

from odoo.addons.account_reports.tests.common import TestAccountReportsCommon

@tagged('post_install', '-at_install')
class TestReports(TestAccountReportsCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.report = cls.env.ref('account_reports.balance_sheet')

    def test_report_export_wizard(self):
        '''
        The wizard in documents_account overrides the one in account_reports.
        This test makes sure that the folder_id and tag_ids are properly set on get_attachment_vals()
        '''
        options = self._generate_options(self.report, fields.Date.from_string('2017-02-01'), fields.Date.from_string('2017-02-01'))

        action = self.report.open_report_export_wizard(options)

        wizard = self.env[action['res_model']].browse(action['res_id'])
        wizard = wizard.with_context(account_report_generation_options=options)
        export_format_ids = self.env['account_reports.export.wizard.format'].search([('fun_param', '=', 'export_to_xlsx')])
        wizard['export_format_ids'] = export_format_ids

        wizard.export_report()
