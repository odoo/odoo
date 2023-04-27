# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, SUPERUSER_ID

from . import models
from . import controllers

def _post_init_hook(cr, registry):
    """ Disable the acquirer because new mandatory fields are added in this module. """
    env = api.Environment(cr, SUPERUSER_ID, {})
    acquirers = env['payment.acquirer'].search([
        ('provider', '=', 'adyen'),
        ('state', '!=', 'disabled'),
    ])
    acquirers.write({
        'state': 'disabled',
    })
