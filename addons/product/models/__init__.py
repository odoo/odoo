# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# flake8: noqa: F401

# don't try to be a good boy and sort imports alphabetically.
# `product.template` should be initialised before `product.product`
from . import product_template
from . import product_product

from . import decimal_precision
from . import product_attribute
from . import product_category
from . import product_packaging
from . import product_pricelist
from . import product_pricelist_item
from . import product_supplierinfo
from . import product_tag
from . import res_company
from . import res_config_settings
from . import res_country_group
from . import res_currency
from . import res_partner
from . import uom_uom
