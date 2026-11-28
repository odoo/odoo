# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models


def uninstall_hook(env):
    env['spreadsheet.dashboard']._pos_hr_restore_dashboard(
        'spreadsheet_dashboard_pos.spreadsheet_dashboard_pos',
        'spreadsheet_dashboard_pos/data/files/pos_dashboard.json',
    )
