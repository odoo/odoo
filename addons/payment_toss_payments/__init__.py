# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models

from odoo.addons.payment import setup_provider, reset_payment_provider
from odoo.addons.payment_toss_payments import const


def post_init_hook(env):
    setup_provider(env, 'tosspayments')


def uninstall_hook(env):
    reset_payment_provider(env, 'tosspayments')
