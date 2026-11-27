# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import receipt
from . import models


def _auto_install_pos_food_delivery_urbanpiper_with_demo(env):
    """If pos_restaurant is installed with demo data, also install pos_food_delivery_urbanpiper."""
    module_pos_food_delivery_urbanpiper = env['ir.module.module']._get('pos_food_delivery_urbanpiper')
    module_pos_restaurant = env['ir.module.module']._get('pos_restaurant')
    if module_pos_restaurant.demo and module_pos_food_delivery_urbanpiper and module_pos_food_delivery_urbanpiper.state == 'uninstalled':
        module_pos_food_delivery_urbanpiper.button_install()


def uninstall_hook(env):
    env['pos.config'].search([('module_pos_restaurant', '=', True)]).module_pos_restaurant = False
