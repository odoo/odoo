from __future__ import annotations

from odoo.api import Environment

from . import models


def _uninstall_cleanup(env: Environment) -> None:
    """Reset customized light and dark color assets on uninstall."""
    env['res.config.settings']._reset_light_color_assets()
    env['res.config.settings']._reset_dark_color_assets()
