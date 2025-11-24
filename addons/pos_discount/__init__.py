# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models


def uninstall_hook(env):
    env['pos.config'].search([('module_pos_discount', '=', True)]).module_pos_discount = False
