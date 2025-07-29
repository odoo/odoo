# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import wizards


def uninstall_hook(env):
    """ Delete `account.payment.method` records created for the installed payment providers. """
    env['account.payment.method'].search([
        ('code', '=', 'online_payment_provider'),
        ('payment_type', '=', 'inbound'),
    ]).unlink()
