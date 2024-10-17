# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import wizards

from odoo.addons.payment import setup_provider, reset_payment_provider

from .models.payment_provider import PaymentProvider
from .models.payment_token import PaymentToken
from .models.payment_transaction import PaymentTransaction
from .wizards.payment_capture_wizard import PaymentCaptureWizard


def post_init_hook(env):
    setup_provider(env, 'adyen')


def uninstall_hook(env):
    reset_payment_provider(env, 'adyen')
