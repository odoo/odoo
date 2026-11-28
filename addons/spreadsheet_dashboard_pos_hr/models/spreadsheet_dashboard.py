# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import api, models
from odoo.tools import file_open


class SpreadsheetDashboard(models.Model):
    _inherit = 'spreadsheet.dashboard'

    def _pos_hr_use_employee(self, file_path, filter_ids=(), list_ids=()):
        """Load the base POS dashboard from ``file_path`` and make it use the
        employee (``employee_id``) instead of the user (``user_id``) in the given
        global filters and lists.
        """
        with file_open(file_path) as f:
            data = json.load(f)
        filter_ids = set(filter_ids)

        for global_filter in data.get('globalFilters', []):
            if global_filter['id'] in filter_ids:
                global_filter['modelName'] = 'hr.employee'

        def use_employee_matching(node):
            if isinstance(node, dict):
                for key, value in node.items():
                    if key in filter_ids and isinstance(value, dict) and value.get('chain') == 'user_id':
                        value['chain'] = 'employee_id'
                    else:
                        use_employee_matching(value)
            elif isinstance(node, list):
                for value in node:
                    use_employee_matching(value)

        if filter_ids:
            use_employee_matching(data)

        for list_id in list_ids:
            for column in data['lists'][list_id]['columns']:
                if column['name'] == 'user_id':
                    column['name'] = 'employee_id'

        self.spreadsheet_data = json.dumps(data)

    @api.model
    def _pos_hr_restore_dashboard(self, xmlid, file_path):
        dashboard = self.env.ref(xmlid, raise_if_not_found=False)
        if dashboard:
            with file_open(file_path) as f:
                dashboard.spreadsheet_data = f.read()
