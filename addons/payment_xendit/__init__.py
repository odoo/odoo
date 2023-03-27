from . import models
from . import controllers
from . import tests

from odoo.addons.payment import setup_provider, reset_payment_provider

def post_init_hook(cr, registry):
    setup_provider(cr, registry, 'xendit')

def uninstall_hook(cr, registry):
    reset_payment_provider(cr, registry, 'xendit')
