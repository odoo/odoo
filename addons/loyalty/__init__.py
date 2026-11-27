# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment import reset_payment_provider, setup_provider

from . import controllers, models, wizard
from .const import LOYALTY_PAYMENT_CODES


def post_init_hook(env):
    for code in LOYALTY_PAYMENT_CODES:
        setup_provider(env, code)
    env["payment.provider"]._recompute_loyalty_publication()


def uninstall_hook(env):
    for code in LOYALTY_PAYMENT_CODES:
        reset_payment_provider(env, code)
