# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import report
from . import wizard


def _post_init_hook(env):
    _setup_accrual_accounts(env)


def _setup_accrual_accounts(env):
    env['account.chart.template']._load_pre_defined_data({
        'res.company': {
            'account_bills_to_receive_id',
            'account_billed_not_received_id',
        }
    })
