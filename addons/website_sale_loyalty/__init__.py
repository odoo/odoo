# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import wizard

from .models.loyalty_card import LoyaltyCard
from .models.loyalty_program import LoyaltyProgram
from .models.loyalty_rule import LoyaltyRule
from .models.sale_order import SaleOrder
from .models.sale_order_line import SaleOrderLine
from .wizard.coupon_share import CouponShare
