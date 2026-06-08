from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestHrTimesheetImportTemplate(TransactionCase):

    def setUp(self):
        super().setUp()
        self.AccountLine = self.env['account.analytic.line']

    def fetch_template_for_timesheet(self, is_timesheet):
        return self.AccountLine.with_context(is_timesheet=is_timesheet).get_import_templates()

    def test_import_template(self):
        template = self.fetch_template_for_timesheet(True)
        self.assertEqual(len(template), 1)
        self.assertEqual(
            template[0]['template'], '/hr_timesheet/static/xls/timesheets_import_template.xlsx',
        )
        template = self.fetch_template_for_timesheet(False)
        self.assertEqual(template, [])
        template = self.fetch_template_for_timesheet(None)
        self.assertEqual(template, [])
