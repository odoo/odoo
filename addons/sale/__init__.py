# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tools.misc import str2bool
from odoo.tools.sql import SQL

from . import const
from . import controllers
from . import models
from . import report
from . import wizard


def _pre_init_sale(env):
    """Allow installing sale in databases with large account.analytic.line tables.

    The different fields are all NULL (falsy) for existing AAL,
    the computation is way more efficient in SQL than in Python.
    """
    env.cr.execute(SQL("""
       ALTER TABLE account_analytic_line
       ADD COLUMN IF NOT EXISTS order_id INT4,
       ADD COLUMN IF NOT EXISTS so_line  INT4
    """))


def _post_init_hook(env):
    _synchronize_crons(env)
    _setup_downpayment_account(env)


def _synchronize_crons(env):
    for param, cron_xmlid in const.PARAM_CRON_MAPPING.items():
        if cron := env.ref(cron_xmlid, raise_if_not_found=False):
            cron.active = env['ir.config_parameter'].get_bool(param)


def _setup_downpayment_account(env):
    env['account.chart.template']._load_pre_defined_data({
        'res.company': {'downpayment_account_id'},
    })
