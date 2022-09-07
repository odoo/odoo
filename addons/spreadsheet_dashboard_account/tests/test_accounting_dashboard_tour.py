from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged('post_install', '-at_install')
class TestAccountingDashboard(HttpCase):

    def test_accounting_dashboard(self):
        self.start_tour('/web', 'spreadsheet_dashboard_accounting', login='admin')

    def test_invoicing_dashboard(self):
        self.start_tour('/web', 'spreadsheet_dashboard_invoicing', login='admin')

    def test_benchmark_dashboard(self):
        self.start_tour('/web', 'spreadsheet_dashboard_benchmark', login='admin')
