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
    """ Set the downpayment_account_id field for existing companies, based on the value defined in the chart template. """
    for company in env.companies:
        if not company.chart_template:
            continue

        ChartTemplate = env["account.chart.template"].with_company(company)
        company_template_data = ChartTemplate._get_chart_template_data(company.chart_template).get('res.company', {})

        if downpayment_account_id := company_template_data.get(company.id, {}).get('downpayment_account_id'):
            downpayment_account = ChartTemplate.ref(downpayment_account_id, raise_if_not_found=False)
            if downpayment_account:
                company.downpayment_account_id = downpayment_account
