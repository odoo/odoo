# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models


def uninstall_hook(env):
    # remove plannings which are scheduled by rental sale order
    env['planning.slot'] \
        .search([
            ('sale_line_id', '!=', False),
            ('sale_line_id.is_rental', '=', True),
        ]) \
        .unlink()
