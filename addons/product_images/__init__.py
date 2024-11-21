# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard


def uninstall_hook(env):
    ICP = env['ir.config_parameter']
    ICP.set_param('google.pse.id', False)
    ICP.set_param('google.custom_search.key', False)
