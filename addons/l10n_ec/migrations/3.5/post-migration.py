# -*- coding: utf-8 -*-

from odoo import api, SUPERUSER_ID, Command

def update_withhold_income_sale_repartition_lines(env):
    # Delete tag_ids for withhold income sale repartition lines
    # Delete tag_ids for withhold income sale account move lines
    report_tax_codes = ['343', '393', '346', '396', '344', '394', '3440', '3940', '345', '395']
    account_account_tags_names = []
    for tax_code in report_tax_codes:
        account_account_tags_names.append(f'+{tax_code} (Reporte 103)')
        account_account_tags_names.append(f'-{tax_code} (Reporte 103)')
    account_account_tags = env['account.account.tag'].search([('name', 'in', account_account_tags_names), ('country_id.code', '=', 'EC')])
    tax_group_id = env.ref('l10n_ec.tax_group_withhold_income_sale')
    domain_repartition_line = ['|', ('invoice_tax_id.tax_group_id', '=', tax_group_id.id), ('refund_tax_id.tax_group_id', '=', tax_group_id.id)]
    repartition_line_ids = env['account.tax.repartition.line'].search(domain_repartition_line)
    account_move_line_ids = env['account.move.line'].search([('tax_line_id.tax_group_id', '=', tax_group_id.id)])
    query = '''
    DELETE FROM account_account_tag_account_tax_repartition_line_rel 
           WHERE account_tax_repartition_line_id IN %s
           AND account_account_tag_id IN %s;
    DELETE FROM account_account_tag_account_move_line_rel
           WHERE account_move_line_id IN %s
           AND account_account_tag_id IN %s;
    '''
    env.cr.execute(query, (tuple(repartition_line_ids.ids), tuple(account_account_tags.ids), tuple(account_move_line_ids.ids), tuple(account_account_tags.ids)))

def update_missing_account_tags_in_taxes(env):
    # All vat taxes to add the missing account tag
    ''' 
    Create a dictionary with the tax base code in the key, and the account tag name in the value.
    Search by account tag name, becasue there is not direct realationship betweet tags and taxes, or between tags and report lines
    {
    <tax l10n_ec_code_base value>: <tax account tag name>,
    }
    '''
    tax_sale = {
        '411': '+401 (Reporte 104)',
        '412': '+402 (Reporte 104)',
        '415': '+405 (Reporte 104)',
        '416': '+406 (Reporte 104)',
        '413': '+403 (Reporte 104)',
        '414': '+404 (Reporte 104)',
        '417': '+407 (Reporte 104)',
        '418': '+408 (Reporte 104)',
        '441': '+431 (Reporte 104)',
        '444': '+434 (Reporte 104)',
        }
    tax_purchase = {
        '510': '+500 (Reporte 104)',
        '511': '+501 (Reporte 104)',
        '512': '+502 (Reporte 104)',
        '513': '+503 (Reporte 104)',
        '514': '+504 (Reporte 104)',
        '515': '+505 (Reporte 104)',
        '516': '+506 (Reporte 104)',
        '517': '+507 (Reporte 104)',
        '518': '+508 (Reporte 104)',
        '541': '+531 (Reporte 104)',
        '542': '+532 (Reporte 104)',
        '545': '+535 (Reporte 104)',
        }
    taxes_to_change = {
        **tax_sale,
        **tax_purchase,
    }
    company_ids = env['res.company'].sudo().search([('country_id', '=', env.ref('base.ec').id)])
    for company in company_ids:
        for l10n_ec_code_base, tax_account_tag_name in taxes_to_change.items():
            account_tag_id = env['account.account.tag'].search([('country_id', '=', env.ref('base.ec').id), ('name', '=', tax_account_tag_name)], limit=1)
            account_tax_ids = env['account.tax'].search([('company_id', '=', company.id), ('l10n_ec_code_base', '=', l10n_ec_code_base)])
            for tax_id in account_tax_ids:
                if account_tag_id:
                    # Add missing account tag in tax
                    repartition_line_ids = tax_id.invoice_repartition_line_ids.filtered(lambda line: line.repartition_type == 'base')
                    repartition_line_ids.write({
                        'tag_ids': [Command.link(account_tag_id.id)]
                    })
                    # Search account move lines by tax, and add missing account tag
                    move_lines_domain = [('tax_ids', 'in', [tax_id.id]), ('move_id.l10n_latam_document_type_id.internal_type', 'in', ['invoice', 'purchase_liquidation'])]
                    move_line_ids = env['account.move.line'].search(move_lines_domain)
                    move_line_ids.write({
                        'tax_tag_ids': [Command.link(account_tag_id.id)]
                    })

def update_no_updateable_option_in_l10n_ec_ifrs_record(env):
    # Change the no updateable option to False, in the l10n_ec_ifrs record
    env['ir.model.data'].search([('module','=','l10n_ec'), ('name','=','l10n_ec_ifrs')]).write({'noupdate':False})

def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    update_withhold_income_sale_repartition_lines(env)
    update_missing_account_tags_in_taxes(env)
    update_no_updateable_option_in_l10n_ec_ifrs_record(env)
