from odoo.tests import tagged
from odoo.tests.common import HttpCase

TEST_CONTENT = '{"sheets": [{"cells":{"A1":{"content":"😃"}}}]}'

@tagged('post_install', '-at_install')
class TestSpreadsheetTemplateFeatures(HttpCase):

    def test_spreadsheet_templates_features(self):
        self.env["spreadsheet.template"].create({
            "spreadsheet_data": TEST_CONTENT,
            "name": "Template with special characters",
        })
        self.start_tour('/web', 'spreadsheet_template_features', login='admin')
