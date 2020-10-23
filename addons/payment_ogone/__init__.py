# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import controllers

from odoo.addons.payment.models.payment_acquirer import create_missing_journals
from odoo.addons.payment import reset_payment_acquirer

def post_init_hook(_cr, _registry):
    create_missing_journals(_cr, _registry)

def uninstall_hook(cr, registry):
    reset_payment_acquirer(cr, registry, 'ogone')
