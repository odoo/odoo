# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from .models import (
    AccountJournal, AccountMove, AccountPayment, AccountPaymentMethod,
    AccountPaymentMethodLine, OnboardingOnboardingStep, PaymentTransaction,
)
from .wizards import (
    AccountPaymentRegister, PaymentLinkWizard, PaymentRefundWizard,
    ResConfigSettings,
)


def post_init_hook(env):
    """ Create `account.payment.method` records for the installed payment providers. """
    PaymentProvider = env['payment.provider']
    installed_providers = PaymentProvider.search([('module_id.state', '=', 'installed')])
    for code in set(installed_providers.mapped('code')):
        PaymentProvider._setup_payment_method(code)


def uninstall_hook(env):
    """ Delete `account.payment.method` records created for the installed payment providers. """
    installed_providers = env['payment.provider'].search([('module_id.state', '=', 'installed')])
    env['account.payment.method'].search([
        ('code', 'in', installed_providers.mapped('code')),
        ('payment_type', '=', 'inbound'),
    ]).unlink()
