# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard


def uninstall_hook(env):
    """Delete loyalty history record accessing order on uninstall."""
    env['loyalty.history'].search([('order_model', '=', 'sale.order')]).unlink()
