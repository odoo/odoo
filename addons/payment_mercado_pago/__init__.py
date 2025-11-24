# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers, models
from odoo.addons import payment  # Prevent circular import error with payment (res.country).


def post_init_hook(env):
    payment.setup_provider(env, 'mercado_pago')


def uninstall_hook(env):
    payment.reset_payment_provider(env, 'mercado_pago')
