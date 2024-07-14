from odoo.addons.spreadsheet.tests.validate_spreadsheet_data import (
    ValidateSpreadsheetData,
)
from odoo.tests.common import tagged


@tagged("-at_install", "post_install")
class TestSpreadsheetTemplateData(ValidateSpreadsheetData):
    def test_validate_template_data(self):
        """validate fields and models used in templates"""
        templates = self.env["spreadsheet.template"].search([])
        for template in templates:
            with self.subTest(template.name):
                self.validate_spreadsheet_data(
                    template.spreadsheet_data, template.name
                )
