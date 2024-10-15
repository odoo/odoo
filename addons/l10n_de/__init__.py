# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .models import (
    AccountAccount, AccountChartTemplate, AccountJournal, AccountMove, AccountTax,
    IrActionsReport, IrAttachment, ProductTemplate, ResCompany,
)


def _post_init_hook(env):
    env['res.groups']._activate_group_account_secured()
