from . import models
from . import wizard


def uninstall_hook(env):
    dashboards = env["dashboard.dashboard"].sudo().search([])
    dashboards.created_action_id.unlink()
    dashboards.created_menu_id.unlink()
