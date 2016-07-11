# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, SUPERUSER_ID


def _set_accounts(cr, registry):
    #write the default debit account on salary rule having xml_id like 'l10n_be_hr_payroll.1' up to 'l10n_be_hr_payroll.1409'
    env = api.Environment(cr, SUPERUSER_ID, {})
    names = [str(x) for x in range(1,1410)]
    data = env['ir.model.data'].search([('model', '=', 'hr.salary.rule'), ('module', '=', 'l10n_be_hr_payroll'), ('name', 'in', names)])
    account = env['account.account'].search([('code', 'like', '4530%')], limit=1)
    if account and data:
        rule_ids = [x['res_id'] for x in data.read(['res_id'])]
        env['hr.salary.rule'].browse(rule_ids).write({'account_debit': account.id})
