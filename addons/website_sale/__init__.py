# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import report


def _post_init_hook(env):
    terms_conditions = env['ir.config_parameter'].get_param('account.use_invoice_terms')
    if not terms_conditions:
        env['ir.config_parameter'].set_param('account.use_invoice_terms', True)
    companies = env['res.company'].search([])
    for company in companies:
        company.terms_type = 'html'
    env['website'].search([]).auth_signup_uninvited = 'b2c'

def uninstall_hook(env):
    ''' Need to reenable the `product` pricelist multi-company rule that were
        disabled to be 'overridden' for multi-website purpose
    '''
    access1 = env.ref('product.access_product_pricelist_global', raise_if_not_found=False)
    access2 = env.ref('product.access_product_pricelist_item_global', raise_if_not_found=False)
    accesses = (access1 or env['ir.access']) + (access2 or env['ir.access'])
    accesses.active = True
