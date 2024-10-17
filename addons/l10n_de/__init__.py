# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models

from .models.account_account import AccountAccount
from .models.account_journal import AccountJournal
from .models.account_move import AccountMove
from .models.datev import AccountTax, ProductTemplate
from .models.ir_actions_report import IrActionsReport
from .models.ir_attachment import IrAttachment
from .models.res_company import ResCompany
from .models.template_de_skr04 import AccountChartTemplate


def _post_init_hook(env):
    env['res.groups']._activate_group_account_secured()
