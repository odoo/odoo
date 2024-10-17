# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard

from .models.loyalty_card import LoyaltyCard
from .models.loyalty_history import LoyaltyHistory
from .models.loyalty_program import LoyaltyProgram
from .models.loyalty_reward import LoyaltyReward
from .models.sale_order import SaleOrder
from .models.sale_order_coupon_points import SaleOrderCouponPoints
from .models.sale_order_line import SaleOrderLine
from .wizard.sale_loyalty_coupon_wizard import SaleLoyaltyCouponWizard
from .wizard.sale_loyalty_reward_wizard import SaleLoyaltyRewardWizard


def uninstall_hook(env):
    """Delete loyalty history record accessing order on uninstall."""
    env['loyalty.history'].search([('order_model', '=', 'sale.order')]).unlink()
