# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from .models import (
    IrHttp, OnboardingOnboardingStep, PaymentMethod, PaymentProvider, PaymentToken,
    PaymentTransaction, ResCompany, ResCountry, ResPartner,
)
from . import utils
from .wizards import PaymentCaptureWizard, PaymentLinkWizard, PaymentProviderOnboardingWizard


def setup_provider(env, code):
    env['payment.provider']._setup_provider(code)


def reset_payment_provider(env, code, **kwargs):
    env['payment.provider']._remove_provider(code, **kwargs)
