from odoo.tests.common import TransactionCase

class TestSpreadsheetDashboardOpenDashboardTour(TransactionCase):
    def open_dashboard(self):
        self.start_tour('/web', 'spreadsheet_dashboard_open_dashboard', login='admin')
