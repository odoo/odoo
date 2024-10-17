# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models

from .models.account_account import AccountAccount
from .models.account_tax import AccountTax
from .models.res_bank import ResBank, ResPartnerBank
from .models.template_mx import AccountChartTemplate


def _enable_group_uom_post_init(env):
    env['res.config.settings'].create({
        'group_uom': True,  # set units of measure to True by default in mx
    }).execute()
