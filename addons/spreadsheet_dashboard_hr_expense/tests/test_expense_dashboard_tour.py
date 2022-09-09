from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged('post_install', '-at_install')
class TestExpenseDashboard(HttpCase):

    def test_expense_dashboard(self):
        self.start_tour('/web', 'spreadsheet_dashboard_expense', login='admin')
