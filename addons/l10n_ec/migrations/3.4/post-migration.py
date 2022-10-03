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

def deprecate_old_withhold_group(env):
    deprecated_withhold_vat_group = env.ref('l10n_ec.tax_group_withhold_vat', False)
    deprecated_withhold_profit_group = env.ref('l10n_ec.tax_group_withhold_income', False)
    if deprecated_withhold_vat_group:
        deprecated_withhold_vat_group.name += ' (Deprecated)'
    if deprecated_withhold_profit_group:
        deprecated_withhold_profit_group += ' (Deprecated)'

def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    update_withhold_type(env)
    update_type_tax_use(env)
    deprecate_old_withhold_group(env)
