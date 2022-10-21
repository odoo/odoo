# -*- coding: utf-8 -*-

from odoo import api, SUPERUSER_ID

def update_withhold_type(env):
    # reclassifies withhold taxes into independent tax groups for sales and purchases
    env.cr.execute('''
        UPDATE account_tax
        SET tax_group_id=t.id FROM (SELECT id FROM account_tax_group WHERE l10n_ec_type='withhold_vat_sale') AS t
        WHERE account_tax.id IN (SELECT id FROM account_tax WHERE tax_group_id IN (SELECT id FROM account_tax_group WHERE l10n_ec_type='withhold_vat') AND type_tax_use='sale')
    ''')
    env.cr.execute('''
        UPDATE account_tax
        SET tax_group_id=t.id FROM (SELECT id FROM account_tax_group WHERE l10n_ec_type='withhold_vat_purchase') AS t
        WHERE account_tax.id IN (SELECT id FROM account_tax WHERE tax_group_id IN (SELECT id FROM account_tax_group WHERE l10n_ec_type='withhold_vat') AND type_tax_use='purchase')
    ''')
    env.cr.execute('''
        UPDATE account_tax
        SET tax_group_id=t.id FROM (SELECT id FROM account_tax_group WHERE l10n_ec_type='withhold_income_sale') AS t
        WHERE account_tax.id IN (SELECT id FROM account_tax WHERE tax_group_id IN (SELECT id FROM account_tax_group WHERE l10n_ec_type='withhold_income_tax') AND type_tax_use='sale')
    ''')
    env.cr.execute('''
        UPDATE account_tax
        SET tax_group_id=t.id FROM (SELECT id FROM account_tax_group WHERE l10n_ec_type='withhold_income_purchase') AS t
        WHERE account_tax.id IN (SELECT id FROM account_tax WHERE tax_group_id IN (SELECT id FROM account_tax_group WHERE l10n_ec_type='withhold_income_tax') AND type_tax_use='purchase')
    ''')

def update_type_tax_use(env):
    # sets type_tax_use = none for withholding taxes
    env.cr.execute('''
        UPDATE account_tax
        SET type_tax_use = 'none'
        WHERE tax_group_id IN (SELECT id FROM account_tax_group WHERE l10n_ec_type IN ('withhold_income_purchase','withhold_vat_purchase','withhold_income_sale','withhold_vat_sale'))
    ''')

def update_vat_withhold_base_percent(env):
    # For vat withhold taxes, replace factor_percent=12% with factor_percent=100%
    all_companies = env['res.company'].search([])
    ecuadorian_companies = all_companies.filtered(lambda r: r.country_code == 'EC')
    ecuadorian_taxes = env['account.tax'].search([('company_id', 'in', ecuadorian_companies.ids)])
    taxes_to_fix = ecuadorian_taxes.filtered(lambda x: x.tax_group_id.l10n_ec_type in ['withhold_vat_sale', 'withhold_vat_purchase'])
    env.cr.execute('''
        --for invoice_tax_id
        update account_tax_repartition_line
        set factor_percent=100 
        where factor_percent=12 
        and repartition_type='tax'
        and invoice_tax_id in %s
        ''', [tuple(taxes_to_fix.ids)])
    env.cr.execute('''
        --for refund_tax_id
        update account_tax_repartition_line
        set factor_percent=100 
        where factor_percent=12 
        and repartition_type='tax'
        and refund_tax_id in %s
        ''', [tuple(taxes_to_fix.ids)])

def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    update_withhold_type(env)
    update_type_tax_use(env)
    update_vat_withhold_base_percent(env)
