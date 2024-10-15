# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .models import (
    LoyaltyCard, LoyaltyHistory, LoyaltyProgram, LoyaltyReward, SaleOrder,
    SaleOrderCouponPoints, SaleOrderLine,
)
from .wizard import SaleLoyaltyCouponWizard, SaleLoyaltyRewardWizard


def uninstall_hook(env):
    """Delete loyalty history record accessing order on uninstall."""
    env['loyalty.history'].search([('order_model', '=', 'sale.order')]).unlink()
