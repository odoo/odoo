from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged('post_install', '-at_install')
class TestPosDashboard(HttpCase):

    def test_pos_dashboard(self):
        self.start_tour('/web', 'spreadsheet_dashboard_pos', login='admin')
