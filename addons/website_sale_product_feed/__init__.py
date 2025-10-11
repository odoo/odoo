# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models


def _post_init_hook(env):
    websites = env['website'].search([])
    enable_gmc = any(site.enabled_gmc_src for site in websites)
    # Enable the feature group if already enabled on a website
    if enable_gmc:
        env.ref('base.group_user')._apply_group(env.ref('website_sale_product_feed.group_product_feed'))
        websites.enabled_gmc_src = enable_gmc
    websites[:1]._populate_product_feeds()
