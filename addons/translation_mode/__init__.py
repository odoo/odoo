# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import tools


def pre_init_hook(env):
    env.invalidate_all()


def post_init_hook(env):
    langs = env['res.lang'].get_installed()
    filter_lang = [code for code, _ in langs]
    mod_names = list(env['ir.module.module']._installed())
    env['ir.module.module']._load_module_terms(mod_names, filter_lang, overwrite=True)
