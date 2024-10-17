# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import controllers

from .models.product_wishlist import (
    ProductProduct, ProductTemplate, ProductWishlist,
    ResPartner,
)
from .models.res_users import ResUsers
