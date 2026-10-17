# Part of Odoo. See LICENSE file for full copyright and licensing details.
from . import models


def uninstall_hook(env):
    env['pos.config'].search([('module_pos_deposit_management', '=', True)]).module_pos_deposit_management = False
