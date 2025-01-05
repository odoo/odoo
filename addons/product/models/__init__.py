# Part of Odoo. See LICENSE file for full copyright and licensing details.

# flake8: noqa: F401

# don't try to be a good boy and sort imports alphabetically.
# `product.template` should be initialised before `product.product`
from . import product_template
from . import product_product

from . import ir_attachment
from . import product_attribute
from . import product_attribute_custom_value
from . import product_attribute_value
from . import product_catalog_mixin
from . import product_category
from . import product_combo
from . import product_combo_item
from . import product_document
from . import product_packaging
from . import product_pricelist
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
