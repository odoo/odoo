# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tools import file_open


def uninstall_hook(env):
    dashboard = env.ref(
        'spreadsheet_dashboard_pos_restaurant.spreadsheet_dashboard_pos_restaurant',
        raise_if_not_found=False,
    )
    if dashboard:
        with file_open('spreadsheet_dashboard_pos_restaurant/data/files/pos_restaurant_dashboard.json', 'r') as f:
            dashboard.spreadsheet_data = f.read()
        dashboard.sample_dashboard_file_path = (
            'spreadsheet_dashboard_pos_restaurant/data/files/pos_restaurant_sample_dashboard.json'
        )
