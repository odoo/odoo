# -*- coding: utf-8 -*-

from odoo import api, SUPERUSER_ID

def update_withhold_type(env):
    # Recreate account tax group templates
    ChartTemplate = env['account.chart.template']
    tax_group_data = ChartTemplate._get_account_tax_group('ec')
    for company in env['res.company'].search([('chart_template', '=', 'ec')]):
        ChartTemplate = env['account.chart.template'].with_company(company)
        ChartTemplate._load_data({'account.tax.group': tax_group_data})

    # Reclassifies withhold taxes into independent tax groups for sales and purchases
    env.cr.execute('''
        UPDATE account_tax t
        SET tax_group_id=tgnew.id 
        FROM account_tax_group tgnew, account_tax_group tgold
        WHERE t.type_tax_use='sale'
            AND tgold.id = t.tax_group_id
            AND tgold.l10n_ec_type='withhold_vat'
            AND tgnew.company_id = t.company_id
            AND tgnew.l10n_ec_type='withhold_vat_sale'
    ''')
    env.cr.execute('''
        UPDATE account_tax t
        SET tax_group_id=tgnew.id 
        FROM account_tax_group tgnew, account_tax_group tgold
        WHERE t.type_tax_use='purchase'
            AND tgold.id = t.tax_group_id
            AND tgold.l10n_ec_type='withhold_vat'
            AND tgnew.company_id = t.company_id
            AND tgnew.l10n_ec_type='withhold_vat_purchase'
    ''')
    env.cr.execute('''
        UPDATE account_tax t
        SET tax_group_id=tgnew.id 
        FROM account_tax_group tgnew, account_tax_group tgold
        WHERE t.type_tax_use='sale'
            AND tgold.id = t.tax_group_id
            AND tgold.l10n_ec_type='withhold_income_tax'
            AND tgnew.company_id = t.company_id
            AND tgnew.l10n_ec_type='withhold_income_sale'
    ''')
    env.cr.execute('''
        UPDATE account_tax t
        SET tax_group_id=tgnew.id 
        FROM account_tax_group tgnew, account_tax_group tgold
        WHERE t.type_tax_use='purchase'
            AND tgold.id = t.tax_group_id
            AND tgold.l10n_ec_type='withhold_income_tax'
            AND tgnew.company_id = t.company_id
            AND tgnew.l10n_ec_type='withhold_income_purchase'
    ''')

def update_type_tax_use(env):
    # sets type_tax_use = none for withholding taxes
    env.cr.execute('''
        UPDATE account_tax
        SET type_tax_use = 'none'
        WHERE tax_group_id IN (SELECT id FROM account_tax_group WHERE l10n_ec_type IN ('withhold_income_purchase','withhold_vat_purchase','withhold_income_sale','withhold_vat_sale'))
    ''')

def update_tax_repartition_line_vat_withhold(env):
    # For tax repartition lines in vat withhold taxes, replace factor_percent=12% with factor_percent=100%
    env.cr.execute('''
        UPDATE account_tax_repartition_line
        SET factor_percent = 100 
        WHERE factor_percent = 12 
        AND repartition_type = 'tax'
        AND tax_id in (
            SELECT id
            FROM account_tax
            WHERE country_id = (SELECT id FROM res_country WHERE code = 'EC' LIMIT 1) --Country is Ecuador)
            AND tax_group_id IN (
                SELECT id FROM account_tax_group WHERE l10n_ec_type IN ('withhold_vat_sale', 'withhold_vat_purchase')
                )
            )
    ''')

def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    update_withhold_type(env)
    update_type_tax_use(env)
    update_tax_repartition_line_vat_withhold(env)
