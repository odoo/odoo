from . import models


def _uninstall_cleanup(env):
    env['res.config.settings']._reset_light_color_assets()
    env['res.config.settings']._reset_dark_color_assets()
