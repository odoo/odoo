# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models


def post_init_hook(env):
    providers = (
        env['payment.provider'].sudo().search([('code', '=', 'worldline')])
        or env.ref('payment.payment_provider_worldline')
    )
    if providers:
        providers._apply_worldline_branding()


def uninstall_hook(env):
    providers = (
        env['payment.provider'].sudo().search([('code', '=', 'worldline')])
        or env.ref('payment.payment_provider_worldline')
    )
    if providers:
        providers._apply_default_worldline_branding()
