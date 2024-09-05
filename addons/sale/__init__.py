# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import controllers
from . import report
from . import wizard
from . import populate


def _post_init_hook(env):
    _synchronize_cron(env)
    _setup_property_downpayment_account(env)


def _synchronize_cron(env):
    send_invoice_cron = env.ref('sale.send_invoice_cron', raise_if_not_found=False)
    if send_invoice_cron:
        config = env['ir.config_parameter'].get_param('sale.automatic_invoice', False)
        send_invoice_cron.active = bool(config)


def _setup_property_downpayment_account(env):
    property_downpayment_field = env['ir.model.fields']._get("product.category", "property_account_downpayment_categ_id")
    # Get companies that already have the property set
    ir_property_companies = env['ir.property'].search([
        ('name', '=', 'property_account_downpayment_categ_id'),
    ]).mapped('company_id.id')

    # Create property for companies without it
    for company in env.companies:
        if not company.chart_template or company in ir_property_companies:
            continue

        template_data = env['account.chart.template']._get_chart_template_data(company.chart_template).get('template_data')
        if template_data and template_data.get('property_account_downpayment_categ_id'):
            property_downpayment_account = env.ref(f'account.{company.id}_{template_data["property_account_downpayment_categ_id"]}', raise_if_not_found=False)
            if property_downpayment_account:
                env['ir.property'].create({
                    'company_id': company.id,
                    'name': 'property_account_downpayment_categ_id',
                    'value_reference': 'account.account,%s' % property_downpayment_account.id,
                    'type': 'many2one',
                    'fields_id': property_downpayment_field.id,
                })
