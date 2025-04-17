# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tools.misc import str2bool

from . import const
from . import controllers
from . import models
from . import report
from . import wizard


def _post_init_hook(env):
    _synchronize_crons(env)
    _setup_downpayment_account(env)


def _synchronize_crons(env):
    for param, cron_xmlid in const.PARAM_CRON_MAPPING.items():
        if cron := env.ref(cron_xmlid, raise_if_not_found=False):
            cron.active = str2bool(env['ir.config_parameter'].get_param(param, 'False'))


def _setup_downpayment_account(env):
    for company in env.companies:
        if not company.chart_template:
            continue

        template_data = env['account.chart.template']._get_chart_template_data(company.chart_template).get('template_data')
        if template_data and template_data.get('downpayment_account_id'):
            property_downpayment_account = env['account.chart.template'].with_company(company).ref(template_data['downpayment_account_id'], raise_if_not_found=False)
            if property_downpayment_account:
                company.downpayment_account_id = property_downpayment_account
