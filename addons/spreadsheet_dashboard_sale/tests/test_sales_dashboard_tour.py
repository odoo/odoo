from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged('post_install', '-at_install')
class TestSalesDashboard(HttpCase):

    def test_sales_dashboard(self):
        self.start_tour('/web', 'spreadsheet_dashboard_sales', login='admin')

    def test_product_dashboard(self):
        self.start_tour('/web', 'spreadsheet_dashboard_product', login='admin')
