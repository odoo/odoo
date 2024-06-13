# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import populate
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
    pl_rule = env.ref('product.product_pricelist_comp_rule', raise_if_not_found=False)
    pl_item_rule = env.ref('product.product_pricelist_item_comp_rule', raise_if_not_found=False)
    multi_company_rules = pl_rule or env['ir.rule']
    multi_company_rules += pl_item_rule or env['ir.rule']
    multi_company_rules.write({'active': True})
