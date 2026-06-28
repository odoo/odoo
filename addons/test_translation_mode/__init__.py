from . import models
from . import tools


def post_init_hook(env):
    env['ir.module.module']._update_translations(overwrite=True)


def uninstall_hook(env):
    env['ir.module.module']._update_translations(overwrite=True)
