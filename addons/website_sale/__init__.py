# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, SUPERUSER_ID, _
from . import controllers
from . import models
from . import wizard
from . import report


def uninstall_hook(cr, registry):
    """ Need to reenable the `product` pricelist multi-company rule that were
        disabled to be 'overridden' for multi-website purpose
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    pl_rule = env.ref('product.product_pricelist_comp_rule', raise_if_not_found=False)
    pl_item_rule = env.ref('product.product_pricelist_item_comp_rule', raise_if_not_found=False)
    multi_company_rules = pl_rule or env['ir.rule']
    multi_company_rules += pl_item_rule or env['ir.rule']
    multi_company_rules.write({'active': True})


def post_init_hook(cr, registry):
    """ Need to add product filters to previously created website """
    # Do the same as in _bootstrap_snippet_filters()
    env = api.Environment(cr, SUPERUSER_ID, {})
    filter = env.ref('website_sale.dynamic_filter_demo_products', raise_if_not_found=False)
    if filter:
        for website in env['website'].search([('id', '!=', filter.website_id.id)]):
            filter.copy({'website_id': website.id})
