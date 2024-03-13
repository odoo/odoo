# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import controllers

from odoo.addons.payment import setup_provider, reset_payment_provider


def post_init_hook(cr, registry):
    setup_provider(cr, registry, 'sips')


def uninstall_hook(cr, registry):
    reset_payment_provider(cr, registry, 'sips')
