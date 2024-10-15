# Part of Odoo. See LICENSE file for full copyright and licensing details.

# flake8: noqa: F401

# don't try to be a good boy and sort imports alphabetically.
# `product.template` should be initialised before `product.product`
from .product_template import ProductTemplate
from .product_product import ProductProduct

from .decimal_precision import DecimalPrecision
from .ir_attachment import IrAttachment
from .product_attribute import ProductAttribute
from .product_attribute_custom_value import ProductAttributeCustomValue
from .product_attribute_value import ProductAttributeValue
from .product_catalog_mixin import ProductCatalogMixin
from .product_category import ProductCategory
from .product_combo import ProductCombo
from .product_combo_item import ProductComboItem
from .product_document import ProductDocument
from .product_packaging import ProductPackaging
from .product_pricelist import ProductPricelist
from .product_pricelist_item import ProductPricelistItem
from .product_supplierinfo import ProductSupplierinfo
from .product_tag import ProductTag
from .product_template_attribute_line import ProductTemplateAttributeLine
from .product_template_attribute_exclusion import ProductTemplateAttributeExclusion
from .product_template_attribute_value import ProductTemplateAttributeValue
from .res_company import ResCompany
from .res_config_settings import ResConfigSettings
from .res_country_group import ResCountryGroup
from .res_currency import ResCurrency
from .res_partner import ResPartner
from .uom_uom import UomUom
