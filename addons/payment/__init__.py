# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import utils
from . import wizards

from .models.ir_http import IrHttp
from .models.onboarding_step import OnboardingOnboardingStep
from .models.payment_method import PaymentMethod
from .models.payment_provider import PaymentProvider
from .models.payment_token import PaymentToken
from .models.payment_transaction import PaymentTransaction
from .models.res_company import ResCompany
from .models.res_country import ResCountry
from .models.res_partner import ResPartner
from .wizards.payment_capture_wizard import PaymentCaptureWizard
from .wizards.payment_link_wizard import PaymentLinkWizard
from .wizards.payment_onboarding_wizard import PaymentProviderOnboardingWizard


def setup_provider(env, code):
    env['payment.provider']._setup_provider(code)


def reset_payment_provider(env, code, **kwargs):
    env['payment.provider']._remove_provider(code, **kwargs)
