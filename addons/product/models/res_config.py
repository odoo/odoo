
from openerp.osv import osv, fields

class base_config_settings(osv.TransientModel):
    _inherit = 'base.config.settings'

    _columns = {
        'company_share_product': fields.boolean('Share product to all companies',
            help="Share your product to all companies defined in your instance.\n"
                 " * Checked : Product are visible for every company, even if a company is defined on the partner.\n"
                 " * Unchecked : Each company can see only its product (product where company is defined). Product not related to a company are visible for all companies."),
        'group_product_variant': fields.boolean('Manage Product Variants', 
            help='Work with product variant allows you to define some variant of the same products, an ease the product management in the ecommerce for example',
            implied_group='product.group_product_variant'),
    }

    def get_default_company_share_product(self, cr, uid, fields, context=None):
        product_rule = self.pool['ir.model.data'].xmlid_to_object(cr, uid, 'product.product_comp_rule', context=context)
        return {
            'company_share_product': not bool(product_rule.active)
        }

    def set_auth_company_share_product(self, cr, uid, ids, context=None):
        product_rule = self.pool['ir.model.data'].xmlid_to_object(cr, uid, 'product.product_comp_rule', context=context)
        for wizard in self.browse(cr, uid, ids, context=context):
            self.pool['ir.rule'].write(cr, uid, [product_rule.id], {'active': not bool(wizard.company_share_product)}, context=context)
