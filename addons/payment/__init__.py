# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import utils
from . import wizards

from odoo import api, SUPERUSER_ID


def setup_provider(cr, registry, provider_code):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['payment.acquirer']._setup_provider(provider_code)


def reset_payment_acquirer(cr, registry, provider):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['payment.acquirer']._remove_provider(provider)
