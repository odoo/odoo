# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# flake8: noqa: F401

# don't try to be a good boy and sort imports alphabetically.
# `product.template` should be initialised before `product.product`
from .product_template import ProductTemplate
from .product_product import ProductProduct

from . import decimal_precision
from . import ir_attachment
from . import product_attribute
from .product_attribute_custom_value import ProductAttributeCustomValue
from . import product_attribute_value
from .product_catalog_mixin import ProductCatalogMixin
from . import product_category
from .product_document import ProductDocument
from .product_packaging import ProductPackaging
from .product_pricelist import Pricelist
from . import product_pricelist_item
from . import product_supplierinfo
from . import product_tag
from . import product_template_attribute_line
from . import product_template_attribute_exclusion
from . import product_template_attribute_value
from . import res_company
from . import res_config_settings
from . import res_country_group
from . import res_currency
from . import res_partner
from . import uom_uom

