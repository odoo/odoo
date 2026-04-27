from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged("post_install", "-at_install")
class TestSpreadsheetDocumentToDashboardTour(HttpCase):
    def test_add_document_to_dashboard_group(self):
        self.start_tour('/odoo', 'spreadsheet_dashboard_document_add_document_to_dashboard_group', login='admin')
