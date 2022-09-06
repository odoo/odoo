# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import wizards

from odoo import api, SUPERUSER_ID


def post_init_hook(cr, registry):
    """ Create `account.payment.method` records for the installed payment providers. """
    env = api.Environment(cr, SUPERUSER_ID, {})
    PaymentAcquirer = env['payment.acquirer']
    installed_providers = PaymentAcquirer.search([('module_id.state', '=', 'installed')])
    for provider_code in set(installed_providers.mapped('provider')):
        PaymentAcquirer._setup_payment_method(provider_code)


def uninstall_hook(cr, registry):
    """ Delete `account.payment.method` records created for the installed payment providers. """
    env = api.Environment(cr, SUPERUSER_ID, {})
    installed_providers = env['payment.acquirer'].search([('module_id.state', '=', 'installed')])
    env['account.payment.method'].search([
        ('code', 'in', installed_providers.mapped('provider')),
        ('payment_type', '=', 'inbound'),
    ]).unlink()
