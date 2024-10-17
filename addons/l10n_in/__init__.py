# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import demo

from .demo.account_demo import AccountChartTemplate
from .models.account_invoice import AccountMove
from .models.account_move_line import AccountMoveLine
from .models.account_tax import AccountTax
from .models.company import ResCompany
from .models.iap_account import IapAccount
from .models.port_code import L10n_InPortCode
from .models.product_template import ProductTemplate
from .models.res_config_settings import ResConfigSettings
from .models.res_country_state import ResCountryState
from .models.res_partner import ResPartner
from .models.uom_uom import UomUom

def init_settings(env):
    # Activate cash rounding by default for all companies as soon as the module is installed.
    group_user = env.ref('base.group_user').sudo()
    group_user._apply_group(env.ref('account.group_cash_rounding'))

def post_init(env):
    init_settings(env)
