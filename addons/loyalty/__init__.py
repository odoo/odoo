# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import wizard

from .models.loyalty_card import LoyaltyCard
from .models.loyalty_history import LoyaltyHistory
from .models.loyalty_mail import LoyaltyMail
from .models.loyalty_program import LoyaltyProgram
from .models.loyalty_reward import LoyaltyReward
from .models.loyalty_rule import LoyaltyRule
from .models.product_product import ProductProduct
from .models.product_template import ProductTemplate
from .models.res_partner import ResPartner
from .wizard.base_partner_merge import BasePartnerMergeAutomaticWizard
from .wizard.loyalty_card_update_balance import LoyaltyCardUpdateBalance
from .wizard.loyalty_generate_wizard import LoyaltyGenerateWizard
