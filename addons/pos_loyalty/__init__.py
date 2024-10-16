# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .models import (
    BarcodeRule, LoyaltyCard, LoyaltyMail, LoyaltyProgram, LoyaltyReward,
    LoyaltyRule, PosConfig, PosOrder, PosOrderLine, PosSession, ProductProduct, ResPartner,
)


def uninstall_hook(env):
    """Delete loyalty history record accessing pos order on uninstall."""
    env['loyalty.history'].search([('order_model', '=', 'pos.order')]).unlink()
