# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from odoo.addons.website_sale import setup_website_tax_display


def _post_init_hook(env):
    setup_website_tax_display(env, "tax_excluded", "US")
