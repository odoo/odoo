# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import wizards


def post_init_hook(env):
    """ Create `account.payment.method` records for the installed payment providers. """
    PaymentProvider = env['payment.provider']
    installed_providers = PaymentProvider.search([('module_id.state', '=', 'installed')])
    for code in set(installed_providers.mapped('code')):
        PaymentProvider._setup_payment_method(code)


def uninstall_hook(env):
    """ Delete `account.payment.method` and `account.payment.method.line` records
    created for the installed payment providers. """
    installed_providers = env['payment.provider'].search([('module_id.state', '=', 'installed')])
    payment_method_obj = env['account.payment.method'].search([
        ('code', 'in', installed_providers.mapped('code')),
        ('payment_type', '=', 'inbound'),])
    if payment_method_obj:
        env.cr.execute('delete from account_payment_method_line where payment_method_id in %s', (tuple(payment_method_obj.ids),))
    payment_method_obj.unlink()
