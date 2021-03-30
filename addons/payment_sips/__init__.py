# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import controllers

from odoo.addons.payment import reset_payment_acquirer
from odoo.addons.payment.models.payment_acquirer import create_missing_journals  # post-init hook


def uninstall_hook(cr, registry):
    reset_payment_acquirer(cr, registry, 'sips')
