# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import report


def _post_init_hook(env):
    terms_conditions = env['ir.config_parameter'].get_bool('account.use_invoice_terms')
    if not terms_conditions:
        env['ir.config_parameter'].set_bool('account.use_invoice_terms', True)
    companies = env['res.company'].search([])
    for company in companies:
        company.terms_type = 'html'
    env['website'].search([]).auth_signup_uninvited = 'b2c'

    existing_websites = env['website'].search([])
    for website in existing_websites:
        website._create_checkout_steps()
    _create_extra_variant_images(env)

def uninstall_hook(env):
    ''' Need to reenable the `product` pricelist multi-company rule that were
        disabled to be 'overridden' for multi-website purpose
    '''
    pl_rule = env.ref('product.product_pricelist_comp_rule', raise_if_not_found=False)
    pl_item_rule = env.ref('product.product_pricelist_item_comp_rule', raise_if_not_found=False)
    multi_company_rules = pl_rule or env['ir.rule']
    multi_company_rules += pl_item_rule or env['ir.rule']
    multi_company_rules.write({'active': True})


def _create_extra_variant_images(env):
    products = env['product.product'].search([('product_tmpl_id.image_1920', '!=', False)])
    image_vals = []
    for product in products:
        image_vals.append({
            'name': product.display_name,
            'product_variant_ids': [(4, product.id)],
            'attribute_value_ids': [(6, 0, product.product_template_attribute_value_ids.ids)],
            'image_1920': product.image_variant_1920 or product.product_tmpl_id.image_1920,
            'sequence': 0,
        })
    env['product.image'].create(image_vals)
