# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tools import convert_file

from . import controllers, models
from odoo.addons.payment import reset_payment_provider, setup_provider


def pre_init_hook(env):
    # Create the provider on databases where `payment` wasn't updated since it was added
    if not env.ref("payment.payment_provider_qfpay", raise_if_not_found=False):
        convert_file(env, "payment", "data/payment_provider_data.xml", None)


def post_init_hook(env):
    setup_provider(env, "qfpay")


def uninstall_hook(env):
    reset_payment_provider(env, "qfpay")
