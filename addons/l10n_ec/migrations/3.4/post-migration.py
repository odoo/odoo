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
    env.cr.execute('''
        --for invoice_tax_id
        UPDATE account_tax_repartition_line
        SET factor_percent = 100 
        WHERE factor_percent = 12 
        AND repartition_type = 'tax'
        AND invoice_tax_id in (
            SELECT id
            FROM account_tax
            WHERE country_id = (SELECT id FROM res_country WHERE code = 'EC' LIMIT 1) --Country is Ecuador)
            AND tax_group_id IN (
                SELECT id FROM account_tax_group WHERE l10n_ec_type IN ('withhold_vat_sale','withhold_vat_purchase')
                )
            )
    ''')
    env.cr.execute('''
        --for refund_tax_id
        UPDATE account_tax_repartition_line
        SET factor_percent = 100 
        WHERE factor_percent = 12 
        AND repartition_type = 'tax'
        AND refund_tax_id in (
            SELECT id
            FROM account_tax
            WHERE country_id = (SELECT id FROM res_country WHERE code = 'EC' LIMIT 1) --Country is Ecuador)
            AND tax_group_id IN (
                SELECT id FROM account_tax_group WHERE l10n_ec_type IN ('withhold_vat_sale','withhold_vat_purchase')
                )
            )
    ''')

def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    update_withhold_type(env)
    update_type_tax_use(env)
    update_vat_withhold_base_percent(env)
