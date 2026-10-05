# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo.tests import TransactionCase


class TestPosHrDashboard(TransactionCase):

    def test_pos_dashboard_uses_employee(self):
        """ The orders list of the POS dashboard shows the employee instead of the user. """
        dashboard = self.env.ref('spreadsheet_dashboard_pos.spreadsheet_dashboard_pos')
        data = json.loads(dashboard.spreadsheet_data)
        columns = [column['name'] for column in data['lists']['1']['columns']]
        self.assertIn('employee_id', columns)
        self.assertNotIn('user_id', columns)
