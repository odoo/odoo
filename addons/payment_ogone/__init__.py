# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models

from odoo.exceptions import UserError
from odoo.tools import config

from odoo.addons.payment import reset_payment_acquirer


def uninstall_hook(cr, registry):
    reset_payment_acquirer(cr, registry, 'ogone')


def pre_init_hook(cr):
    if not any(config.get(key) for key in ('init', 'update')):
        raise UserError(
            "This module is deprecated and cannot be installed. "
            "Consider installing the Payment Acquirer: Stripe module instead.")
