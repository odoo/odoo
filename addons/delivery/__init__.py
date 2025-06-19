# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import wizard

from odoo.addons.payment import reset_payment_provider, setup_provider


def post_init_hook(env):
    setup_provider(env, 'custom', custom_mode='cash_on_delivery')


def uninstall_hook(env):
    reset_payment_provider(env, 'custom', custom_mode='cash_on_delivery')
