# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import wizards

from odoo import api, SUPERUSER_ID


def post_init_hook(cr, registry):
    """ Create `account.payment.method` records for the installed payment providers. """
    env = api.Environment(cr, SUPERUSER_ID, {})
    PaymentProvider = env['payment.provider']
    installed_providers = PaymentProvider.search([('module_id.state', '=', 'installed')])
    for code in set(installed_providers.mapped('code')):
        PaymentProvider._setup_payment_method(code)


def uninstall_hook(cr, registry):
    """ Delete `account.payment.method` records created for the installed payment providers. """
    env = api.Environment(cr, SUPERUSER_ID, {})
    installed_providers = env['payment.provider'].search([('module_id.state', '=', 'installed')])
    env['account.payment.method'].search([
        ('code', 'in', installed_providers.mapped('code')),
        ('payment_type', '=', 'inbound'),
    ]).unlink()
