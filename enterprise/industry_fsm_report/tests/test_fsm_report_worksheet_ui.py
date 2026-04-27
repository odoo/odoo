# Part of Odoo. See LICENSE file for full copyright and licensing details.
# -*- coding: utf-8 -*-

from odoo.tests import tagged, HttpCase

@tagged('post_install', '-at_install')
class TestFSMReportWorksheetUI(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_admin = cls.env.ref('base.user_admin')

    def test_ui(self):
        self.start_tour('/odoo', 'industry_fsm_report_worksheet_test_tour', login=self.user_admin.login)
