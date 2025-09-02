# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models


def _auto_install_pos_urban_piper_with_demo(env):
    """If pos_restaurant is installed with demo data, also install pos_urban_piper."""
    module_pos_urban_piper = env['ir.module.module']._get('pos_urban_piper')
    module_pos_restaurant = env['ir.module.module']._get('pos_restaurant')
    if module_pos_restaurant.demo and module_pos_urban_piper and module_pos_urban_piper.state == 'uninstalled':
        module_pos_urban_piper.button_install()
