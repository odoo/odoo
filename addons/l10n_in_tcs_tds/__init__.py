# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models

from odoo import api, SUPERUSER_ID

import logging

_logger = logging.getLogger(__name__)


def load_taxes(env):
    in_chart_template = env.ref('l10n_in.indian_chart_template_standard')
    for company in env['res.company'].search([('chart_template_id', '=', in_chart_template.id)]):
        try:
            with env.cr.savepoint():
                tax_template_ids = env['ir.model.data'].search([
                    ('module', '=', 'l10n_in_tcs_tds'),
                    ('model', '=', 'account.tax.template'),
                    ]).mapped('res_id')
                generated_tax_res = env['account.tax.template'].browse(tax_template_ids)._generate_tax(company)
                taxes_ref = generated_tax_res['tax_template_to_tax']
        except Exception:
            taxes_ref = {}
            _logger.error("Can't load TDS and TCS taxes for company: %s(%s).", company.name, company.id)
        if taxes_ref:
            try:
                with env.cr.savepoint():
                    account_ref = {}
                    # Generating Accounts from templates.
                    account_template_ref = in_chart_template.generate_account(taxes_ref, {}, in_chart_template.code_digits, company)
                    account_ref.update(account_template_ref)

                    # writing account values after creation of accounts
                    for key, value in generated_tax_res['account_dict']['account.tax.repartition.line'].items():
                        if value['account_id']:
                            key.write({
                                'account_id': account_ref.get(value['account_id']),
                            })
            except Exception:
                _logger.error("Can't load TCS and TDS account so account is not set in taxes of company: %s(%s).", company.name, company.id)


def l10n_in_post_init(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    load_taxes(env)
