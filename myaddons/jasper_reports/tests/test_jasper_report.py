# -*- coding: utf-8 -*-
import base64
from odoo.tests.common import TransactionCase
from odoo.modules.module import get_module_resource
# from odoo.addons.jasper_reports.controllers.main import ReportController
# from odoo.addons.web.controllers.main import ReportController


class TestJasperReport(TransactionCase):

    def setUp(self):
        super(TestJasperReport, self).setUp()
        # First we have to convert .jrxml file to binary
        # In order to create a new report record
        # File path
        path = get_module_resource('jasper_reports', 'tests', 'user.jrxml')
        # Opening file
        file = open(path, 'rb')
        # Reading
        file_content = file.read()
        # Converting as base64
        report_file = base64.b64encode(file_content)

        self.JasperReport = self.env['ir.actions.report']
        self.users_model = self.env['ir.model'].search([
            ('model', '=', 'res.users')])
        self.report_data = self.JasperReport.create({
            'name': 'Jasper Test Report',
            'model': 'res.users',
            'attachment_use': True,
            'model_id': self.users_model and
            self.users_model.id or False,
            'jasper_output': 'pdf',
            'report_name': 'res_users_jasper',
            'jasper_report': True,
            'jasper_file_ids': [
                (0, 0, {
                    'default': True,
                    'filename': 'user.jrxml',
                    'file': report_file,
                })
            ]
        })

    def test_report(self):
        report_object = self.env['ir.actions.report']
        report_name = self.report_data.report_name
        report = report_object._get_report_from_name(report_name)
        docs = self.env['res.users'].search([], limit=1)
        self.assertEqual(report.report_type, 'qweb-pdf')
        # We are giving travis postgres cradentials for
        # db connectivity in order to make sure that test case
        # can connect with database.
        self.env['ir.config_parameter'].set_param('db_user', 'postgres')
        self.env['ir.config_parameter'].set_param('db_password', '')
        return report.render_jasper(docs.ids, {})
