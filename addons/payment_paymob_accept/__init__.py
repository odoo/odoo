# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import controllers

import odoo.addons.payment as payment  # prevent circular import error with payment


def post_init_hook(env):
    payment.setup_provider(env, "paymob")


def uninstall_hook(env):
    payment.reset_payment_provider(env, "paymob")
