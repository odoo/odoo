# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo.tests import TransactionCase

WAITER_FILTER_ID = '7674d2c1-e82b-4199-a991-6fae2268676b'


class TestPosRestaurantHrDashboard(TransactionCase):

    def _get_field_matching_chains(self, node, filter_id):
        if isinstance(node, dict):
            for key, value in node.items():
                if key == filter_id and isinstance(value, dict) and 'chain' in value:
                    yield value['chain']
                else:
                    yield from self._get_field_matching_chains(value, filter_id)
        elif isinstance(node, list):
            for value in node:
                yield from self._get_field_matching_chains(value, filter_id)

    def test_restaurant_dashboard_uses_employee(self):
        """ The waiter filter of the restaurant dashboard filters on the employee instead of the user. """
        dashboard = self.env.ref('spreadsheet_dashboard_pos_restaurant.spreadsheet_dashboard_pos_restaurant')
        data = json.loads(dashboard.spreadsheet_data)
        waiter_filters = [f for f in data['globalFilters'] if f['id'] == WAITER_FILTER_ID]
        self.assertEqual(len(waiter_filters), 1, "The waiter filter should exist in the dashboard")
        self.assertEqual(waiter_filters[0]['modelName'], 'hr.employee')
        chains = list(self._get_field_matching_chains(data, WAITER_FILTER_ID))
        self.assertTrue(chains, "The waiter filter should be matched on some data sources")
        self.assertEqual(set(chains), {'employee_id'})
