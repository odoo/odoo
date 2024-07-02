# -*- coding: utf-8 -*-

from odoo import api, SUPERUSER_ID

def update_withhold_type(env):
    # reclasifies withhold taxes into independent tax groups for sales and purchases
    env.cr.execute('''
        update account_tax
        set tax_group_id=t.id from (select id from account_tax_group where l10n_ec_type='withhold_vat_sale') as t
        where account_tax.id in (select id from account_tax where tax_group_id in (select id from account_tax_group where l10n_ec_type='withhold_vat') and type_tax_use='sale')
    ''')
    env.cr.execute('''
        update account_tax
        set tax_group_id=t.id from (select id from account_tax_group where l10n_ec_type='withhold_vat_purchase') as t
        where account_tax.id in (select id from account_tax where tax_group_id in (select id from account_tax_group where l10n_ec_type='withhold_vat') and type_tax_use='purchase')
    ''')
    env.cr.execute('''
        update account_tax
        set tax_group_id=t.id from (select id from account_tax_group where l10n_ec_type='withhold_income_sale') as t
        where account_tax.id in (select id from account_tax where tax_group_id in (select id from account_tax_group where l10n_ec_type='withhold_income_tax') and type_tax_use='sale')
    ''')
    env.cr.execute('''
        update account_tax
        set tax_group_id=t.id from (select id from account_tax_group where l10n_ec_type='withhold_income_purchase') as t
        where account_tax.id in (select id from account_tax where tax_group_id in (select id from account_tax_group where l10n_ec_type='withhold_income_tax') and type_tax_use='purchase')
    ''')

def update_type_tax_use(env):
    # sets type_tax_use = none for withholding taxes
    env.cr.execute('''
        update account_tax
        set type_tax_use = 'none'
        where tax_group_id in (select id from account_tax_group where l10n_ec_type in ('withhold_income_purchase','withhold_vat_purchase','withhold_income_sale','withhold_vat_sale'))
    ''')

def unlink_old_withhold_group(env):
    deprecated_withhold_vat_group = env.ref('l10n_ec.tax_group_withhold_vat', False)
    deprecated_withhold_profit_group = env.ref('l10n_ec.tax_group_withhold_income', False)
    deprecated_withhold_vat_group and deprecated_withhold_vat_group.unlink()
    deprecated_withhold_profit_group and deprecated_withhold_profit_group.unlink()

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

def recompute_invoice_names(env):
    #recomputes invoice name, as new l10n_latam_document_number prefixes has been provided in latam document type master data
    all_companies = env['res.company'].search([])
    ecuadorian_companies = all_companies.filtered(lambda r: r.country_code == 'EC')
    env.cr.execute('''
        --split name by space, then concatenate code prefix with last element of name
        UPDATE account_move
        SET name = CONCAT(doc.doc_code_prefix,' ',reverse(split_part(reverse(account_move.name), ' ', 1)))
        FROM account_move am
        LEFT JOIN l10n_latam_document_type doc on doc.id = am.l10n_latam_document_type_id
        WHERE am.l10n_latam_document_type_id IS NOT NULL
        AND am.state IN ('posted','cancel')
        AND am.id = account_move.id
        AND am.company_id in %s
        ''', [tuple(ecuadorian_companies.ids)])

def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    update_withhold_type(env)
    update_type_tax_use(env)
    unlink_old_withhold_group(env)
    update_vat_withhold_base_percent(env)
    recompute_invoice_names(env)
