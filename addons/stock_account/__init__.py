# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import report
from . import wizard

from odoo import api, SUPERUSER_ID, _, tools

def _configure_journals(cr, registry):
    """Setting journal and property field (if needed)"""

    env = api.Environment(cr, SUPERUSER_ID, {})
    Journal = env['account.journal']
    Property = env['ir.property'].sudo()
    ChartTemplate = env['account.chart.template']

    # if we already have a coa installed, create journal and set property field
    for company in env['res.company'].search([('chart_template', '!=', False)]):

        # Check if property exists for stock account journal exists
        template_code = company.chart_template
        field = env['ir.model.fields']._get("product.category", "property_stock_journal")
        properties = Property.search([('fields_id', '=', field.id), ('company_id', '=', company.id)])

        # If not, check if you can find a journal that is already there with the same name, otherwise create one
        if not properties:
            journal = Journal.search([('code', '=', 'STJ'), ('company_id', '=', company.id)], limit=1)
            if not journal:
                journal_data = ChartTemplate._get_account_journal(template_code, company)
                journal = Journal.create(journal_data[f'{company.id}_inventory_valuation'])
            Property._set_default('property_stock_journal', 'product.category', journal.id, company)

        # Property Stock Accounts
        template_data = ChartTemplate._get_template_data(template_code, company)
        for field in (
            'property_stock_account_input_categ_id',
            'property_stock_account_output_categ_id',
            'property_stock_valuation_account_id',
        ):
            account_ref = template_data.get(field)
            if account_ref:
                account = env.ref(account_ref)
                setattr(company, field, account.id)
                Property._set_default(field, 'product.category', account, company)
