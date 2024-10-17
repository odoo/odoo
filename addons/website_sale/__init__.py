# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import report

from .models.account_move import AccountMove
from .models.crm_team import CrmTeam
from .models.delivery_carrier import DeliveryCarrier
from .models.digest import DigestDigest
from .models.ir_http import IrHttp
from .models.payment_token import PaymentToken
from .models.product_attribute import ProductAttribute
from .models.product_document import ProductDocument
from .models.product_image import ProductImage
from .models.product_pricelist import ProductPricelist
from .models.product_product import ProductProduct
from .models.product_public_category import ProductPublicCategory
from .models.product_ribbon import ProductRibbon
from .models.product_tag import ProductTag
from .models.product_template import ProductTemplate
from .models.product_template_attribute_line import ProductTemplateAttributeLine
from .models.product_template_attribute_value import ProductTemplateAttributeValue
from .models.res_company import ResCompany
from .models.res_config_settings import ResConfigSettings
from .models.res_partner import ResPartner
from .models.sale_order import SaleOrder
from .models.sale_order_line import SaleOrderLine
from .models.website import Website
from .models.website_base_unit import WebsiteBaseUnit
from .models.website_menu import WebsiteMenu
from .models.website_sale_extra_field import WebsiteSaleExtraField
from .models.website_snippet_filter import WebsiteSnippetFilter
from .models.website_track import WebsiteTrack
from .models.website_visitor import WebsiteVisitor
from .report.sale_report import SaleReport


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
