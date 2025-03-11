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
    _setup_property_downpayment_account(env)


def _synchronize_crons(env):
    for param, cron_xmlid in const.PARAM_CRON_MAPPING.items():
        if cron := env.ref(cron_xmlid, raise_if_not_found=False):
            cron.active = str2bool(env['ir.config_parameter'].get_param(param, 'False'))


def _setup_property_downpayment_account(env):
    # Get companies that already have the property set
    ProductCategory = env['product.category']

    # Create property for companies without it
    for company in env.companies:
        if not company.chart_template or ProductCategory.with_company(company).search_count([('property_account_downpayment_categ_id', '!=', False)], limit=1):
            continue

        template_data = env['account.chart.template']._get_chart_template_data(company.chart_template).get('template_data')
        if template_data and template_data.get('property_account_downpayment_categ_id'):
            property_downpayment_account = env.ref(f'account.{company.id}_{template_data["property_account_downpayment_categ_id"]}', raise_if_not_found=False)
            if property_downpayment_account:
                env['ir.default'].set('product.category', 'property_account_downpayment_categ_id', property_downpayment_account.id, company_id=company.id)
