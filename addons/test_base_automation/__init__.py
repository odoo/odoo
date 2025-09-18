# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models


def _post_init_hook(env):
    """
    Post-initialization hook to create demo data if enabled.

    This function is called after the module is installed.
    It checks if demo data is enabled and creates example automations.
    """
    # Only create demo data if module was installed with demo=True
    # This is automatically handled by Odoo's demo mechanism
    if env.context.get("install_mode"):
        # Check if demo data should be loaded
        module = env["ir.module.module"].search(
            [("name", "=", "test_base_automation")], limit=1
        )
        if module and module.demo:
            from .demo import demo_data

            demo_data._setup_demo_data(env)
