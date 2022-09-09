from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged('post_install', '-at_install')
class TestEventsDashboard(HttpCase):

    def test_events_dashboard(self):
        self.start_tour('/web', 'spreadsheet_dashboard_events', login='admin')
