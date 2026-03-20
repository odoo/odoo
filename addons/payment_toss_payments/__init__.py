# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers, models
from odoo.addons.payment import reset_payment_provider, setup_provider


def post_init_hook(env):
    setup_provider(env, 'toss_payments')


def uninstall_hook(env):
    reset_payment_provider(env, 'toss_payments')
