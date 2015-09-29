# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import SUPERUSER_ID

def _set_accounts(cr, registry):
    #write the default debit account on salary rule having xml_id like 'l10n_be_hr_payroll.1' up to 'l10n_be_hr_payroll.1409'
    model_obj = registry['ir.model.data']
    names = [str(x) for x in range(1,1410)]
    rec_ids = model_obj.search(cr, SUPERUSER_ID, [('model', '=', 'hr.salary.rule'), ('module', '=', 'l10n_be_hr_payroll'), ('name', 'in', names)], {})
    account_ids = registry['account.account'].search(cr, SUPERUSER_ID, [('code', 'like', '4530%')], {})
    if account_ids and rec_ids:
        rule_ids = [x['res_id'] for x in model_obj.read(cr, SUPERUSER_ID, rec_ids, ['res_id'])]
        registry['hr.salary.rule'].write(cr, SUPERUSER_ID, rule_ids, {'account_debit': account_ids[0]})
