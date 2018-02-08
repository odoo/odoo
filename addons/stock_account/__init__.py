# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard

from odoo import api, SUPERUSER_ID, _, tools

def _configure_journals(cr, registry):
    """Setting journal and property field (if needed)"""

    env = api.Environment(cr, SUPERUSER_ID, {})

    # if we already have a coa installed, create journal and set property field
    company_ids = env['res.company'].search([('chart_template_id', '!=', False)])

    for company_id in company_ids:
        # Check if property exists for stock account journal exists
        properties = env['ir.property'].search([
            ('name', '=', 'property_stock_journal'),
            ('company_id', '=', company_id.id)])

        # If not, check if you can find a journal that is already there with the same name, otherwise create one
        if not properties:
            journal_id = env['account.journal'].search([
                ('name', '=', _('Stock Journal')),
                ('company_id', '=', company_id.id),
                ('type', '=', 'general')], limit=1).id
            if not journal_id:
              journal_id = env['account.journal'].create({
                'name': _('Stock Journal'),
                'type': 'general',
                'code': 'STJ',
                'company_id': company_id.id,
                'show_on_dashboard': False
              }).id
            vals = {
                'name': 'property_stock_journal',
                'fields_id': env['ir.model.fields'].search([
                    ('name', '=', 'property_stock_journal'),
                    ('model', '=', 'product.category'),
                    ('relation', '=', 'account.journal')], limit=1).id,
                'company_id': company_id.id,
                'value': 'account.journal,' + str(journal_id)
            }
            env['ir.property'].create(vals)

        # Property Stock Accounts
        todo_list = [
            'property_stock_account_input_categ_id',
            'property_stock_account_output_categ_id',
            'property_stock_valuation_account_id',
        ]

        for record in todo_list:
            account = getattr(company_id, record)
            value = account and 'account.account,' + str(account.id) or False
            if value:
                field_id = env['ir.model.fields'].search([
                  ('name', '=', record),
                  ('model', '=', 'product.category'),
                  ('relation', '=', 'account.account')
                ], limit=1).id
                vals = {
                    'name': record,
                    'company_id': company_id.id,
                    'fields_id': field_id,
                    'value': value,
                    'res_id': 'product.category,'+str(env.ref('product.product_category_all').id),
                }
                properties = env['ir.property'].search([
                    ('name', '=', record),
                    ('company_id', '=', company_id.id),
                    ('value_reference', '!=', False)])
                if not properties:
                    # create the property
                    env['ir.property'].create(vals)

    stock_account = env.ref('account.demo_stock_account', False)
    if stock_account:
        account_id = env['account.account'].search([('tag_ids', '=', stock_account.id)], limit=1).id
        fields_id = env['ir.model.fields'].search([('model', '=', 'product.category'), ('name', '=', 'property_stock_valuation_account_id')], limit=1).id
        if not account_id:
            account_id = env['account.account'].search([('user_type_id', '=', env.ref('account.data_account_type_current_assets').id)], limit=1).id
        if account_id:
            vals = {
                'name': 'property_stock_valuation_account_id',
                'fields_id': fields_id,
                'value': 'account.account,'+str(account_id),
                'company_id': env.ref('base.main_company').id,
            }
            env['ir.model.data']._update('ir.property', 'stock_account', vals, 'property_stock_valuation_account_id')
