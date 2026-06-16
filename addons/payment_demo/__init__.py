# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models

from odoo.addons.payment import setup_provider, reset_payment_provider


def post_init_hook(env):
    setup_provider(env, 'demo')

    demo_provider = env.ref('payment_demo.payment_provider_demo', raise_if_not_found=False)
    if demo_provider and demo_provider.journal_id:
        demo_provider.write({'state': 'test', 'is_published': True})


def uninstall_hook(env):
    reset_payment_provider(env, 'demo')
