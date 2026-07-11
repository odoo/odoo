from __future__ import annotations

import base64

from odoo.api import Environment
from odoo.tools import file_open

from . import models


def _setup_module(env: Environment) -> None:
    """Seed the main company favicon and apps-menu background image."""
    if env.ref('base.main_company', False):
        with file_open('web/static/img/favicon.ico', 'rb') as file:
            env.ref('base.main_company').write(
                {'favicon': base64.b64encode(file.read())}
            )
        with file_open('muk_web_theme/static/src/img/background.png', 'rb') as file:
            env.ref('base.main_company').write(
                {'background_image': base64.b64encode(file.read())}
            )


def _uninstall_cleanup(env: Environment) -> None:
    """Reset the theme color assets on module uninstall."""
    env['res.config.settings']._reset_theme_color_assets()
