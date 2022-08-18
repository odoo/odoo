# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import report
from . import wizard

from odoo import api, SUPERUSER_ID, _, tools

def _configure_journals(cr, registry):
    """Setting journal and property field (if needed)"""

    env = api.Environment(cr, SUPERUSER_ID, {})

    # if we already have a coa installed, create journal and set property field
    company_ids = env['res.company'].search([('chart_template_id', '!=', False)])
    todo_list = [
        'property_stock_account_input_categ_id',
        'property_stock_account_output_categ_id',
        'property_stock_valuation_account_id',
    ]
    # Property Stock Accounts
    for company_id in company_ids:
        # Check if property exists for stock account journal exists
        field = env['ir.model.fields']._get("product.category", "property_stock_journal")
        properties = env['ir.property'].sudo().search([
            ('fields_id', '=', field.id),
            ('company_id', '=', company_id.id)])

        # If not, check if you can find a journal that is already there with the same name, otherwise create one
        if not properties:
            journal_id = env['account.journal'].search([
                ('name', '=', _('Inventory Valuation')),
                ('company_id', '=', company_id.id),
                ('type', '=', 'general')], limit=1).id
            if not journal_id:
                journal_id = env['account.journal'].create({
                    'name': _('Inventory Valuation'),
                    'type': 'general',
                    'code': 'STJ',
                    'company_id': company_id.id,
                    'show_on_dashboard': False
                }).id
            env['ir.property']._set_default(
                'property_stock_journal',
                'product.category',
                journal_id,
                company_id,
            )

        for name in todo_list:
            account = getattr(company_id, name)
            if account:
                env['ir.property']._set_default(
                    name,
                    'product.category',
                    account,
                    company_id,
                )
    for name in todo_list:
        env['ir.property']._set_multi(
            name,
            'product.category',
            {category.id: False for category in env['product.category'].search([])},
            True
        )
