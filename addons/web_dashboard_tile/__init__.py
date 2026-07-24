from . import models


def _post_init_hook(env):
    """Force recreate UI actions for tile categories after upgrade."""
    categories = env["tile.category"].search([("active", "=", True)])
    # Delete old actions and menus, recreate with new view_mode
    categories._delete_ui()
    # Reset action_id and menu_id
    categories.write({"action_id": False, "menu_id": False})
    categories._create_ui()
