# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2014 Tech Receptives (<http://techreceptives.com>).
from . import models

from .models.account_move import AccountMove
from .models.res_bank import ResPartnerBank
from .models.res_company import ResCompany
from .models.res_partner import ResPartner
from .models.template_sg import AccountChartTemplate

def _preserve_tag_on_taxes(env):
    from odoo.addons.account.models.chart_template import preserve_existing_tags_on_taxes
    preserve_existing_tags_on_taxes(env, 'l10n_sg')
