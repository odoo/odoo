from openerp.addons.mail.tests.common import TestMail
from datetime import datetime

class TestChartOfAccount(TestMail):

    def setUp(self):
        super(TestChartOfAccount, self).setUp()

    def test_chart_of_account(self):
        # In order to test the Analytic Charts of Account wizard I will generate chart
        account_analystic_chart = self.env['account.analytic.chart'].create({
            'from_date': datetime(datetime.now().year, 01, 01),
            'to_date': datetime(datetime.now().year, 06, 30),
        })
        
        # I clicked on Open chart Button to open the charts
        account_analystic_chart.analytic_account_chart_open_window()
