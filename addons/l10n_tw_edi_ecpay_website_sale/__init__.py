# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models


def _post_init_hook(env):
    tw_extra_step = env.ref('l10n_tw_edi_ecpay_website_sale.checkout_step_invoicing')
    for website in env['website'].search([]):
        tw_extra_step.copy({'website_id': website.id})
