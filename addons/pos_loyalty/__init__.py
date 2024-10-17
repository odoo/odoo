# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models

from .models.barcode_rule import BarcodeRule
from .models.loyalty_card import LoyaltyCard
from .models.loyalty_mail import LoyaltyMail
from .models.loyalty_program import LoyaltyProgram
from .models.loyalty_reward import LoyaltyReward
from .models.loyalty_rule import LoyaltyRule
from .models.pos_config import PosConfig
from .models.pos_order import PosOrder
from .models.pos_order_line import PosOrderLine
from .models.pos_session import PosSession
from .models.product_product import ProductProduct
from .models.res_partner import ResPartner


def uninstall_hook(env):
    """Delete loyalty history record accessing pos order on uninstall."""
    env['loyalty.history'].search([('order_model', '=', 'pos.order')]).unlink()
