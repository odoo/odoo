# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from . import controllers
from . import models
from odoo.api import Environment, SUPERUSER_ID


def post_init_hook(cr, registry):
    env = Environment(cr, SUPERUSER_ID, {})

    # Deactivate the existing tokens which won't work with the new authentication method.
    acquirer = env['payment.acquirer'].search([('provider', '=', 'stripe')])
    if acquirer:
        env['payment.token'].search([
            ('acquirer_id', 'in', acquirer.ids), ('stripe_payment_method', '=', False)
        ]).write({'active': False})
