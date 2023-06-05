# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models

def pre_init_hook(env):
    # check env is ready to use
    env['test_loading_1.model'].search([], limit=1)

def post_init_hook(env):
    # this function won't be called by default since it is not declared in the __manifest__.py
    module = env.ref('base.module_test_loading_2')
    if module:
        module.sudo().button_install()
