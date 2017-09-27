# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# flake8: noqa: F401

from . import res_config_settings
from . import decimal_precision

# don't try to be a good boy and sort imports alphabetically.
# `product.template` should be initialised before `product.product`
from . import product_template
from . import product

from . import product_attribute
from . import product_pricelist
from . import product_uom
from . import res_company
from . import res_partner
