# Part of Odoo. See LICENSE file for full copyright and licensing details.


def uninstall_hook(env):
    env['spreadsheet.dashboard']._pos_hr_restore_dashboard(
        'spreadsheet_dashboard_pos_restaurant.spreadsheet_dashboard_pos_restaurant',
        'spreadsheet_dashboard_pos_restaurant/data/files/pos_restaurant_dashboard.json',
    )
