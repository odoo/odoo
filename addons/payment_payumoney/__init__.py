# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models

from odoo.exceptions import UserError
from odoo.tools import config

from odoo.addons.payment import setup_provider, reset_payment_acquirer


def pre_init_hook(cr):
    if not any(config.get(key) for key in ('init', 'update')):
        raise UserError(
            "This module is deprecated and cannot be installed. "
            "Consider installing the Payment Acquirer: Razorpay module instead.")


def post_init_hook(cr, registry):
    setup_provider(cr, registry, 'payumoney')


def uninstall_hook(cr, registry):
    reset_payment_acquirer(cr, registry, 'payumoney')
