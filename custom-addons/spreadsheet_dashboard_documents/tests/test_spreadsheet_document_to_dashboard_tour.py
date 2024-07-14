from odoo.tests.common import TransactionCase

class TestSpreadsheetDocumentToDashboardTour(TransactionCase):
    def add_document_to_dashboard_group(self):
        self.start_tour('/web', 'spreadsheet_dashboard_document_add_document_to_dashboard_group', login='admin')
