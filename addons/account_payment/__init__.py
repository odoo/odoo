# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import wizards

from .models.account_journal import AccountJournal
from .models.account_move import AccountMove
from .models.account_payment import AccountPayment
from .models.account_payment_method import AccountPaymentMethod
from .models.account_payment_method_line import AccountPaymentMethodLine
from .models.onboarding_onboarding_step import OnboardingOnboardingStep
from .models.payment_transaction import PaymentTransaction
from .wizards.account_payment_register import AccountPaymentRegister
from .wizards.payment_link_wizard import PaymentLinkWizard
from .wizards.payment_refund_wizard import PaymentRefundWizard
from .wizards.res_config_settings import ResConfigSettings


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
