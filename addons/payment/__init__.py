# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import utils
from . import wizards

from odoo import api, SUPERUSER_ID


def reset_payment_acquirer(cr, registry, provider):
    env = api.Environment(cr, SUPERUSER_ID, {})
    acquirers = env['payment.acquirer'].search([('provider', '=', provider)])
    acquirers.write({
        'provider': 'none',
        'state': 'disabled',
    })
