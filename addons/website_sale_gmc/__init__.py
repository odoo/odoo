# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models


def _post_init_hook(env):
    websites_enabled_gmc = env['website'].search([('enabled_gmc_src', '=', True)])

    # Enable the feature group if already enabled on a website
    if websites_enabled_gmc:
        env.ref('base.group_user')._apply_group(env.ref('website_sale_gmc.group_product_feed'))

    websites_enabled_gmc._populate_product_feeds()
