# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import report

from odoo import api, SUPERUSER_ID, _, tools

def _configure_accounts(cr, registry):
    """Setting property field (if needed)"""

    env = api.Environment(cr, SUPERUSER_ID, {})

    # if we already have a coa installed, create set property field
    company_ids = env['res.company'].search([('chart_template_id', '!=', False)])

    for company_id in company_ids:

        # Property Stock Accounts
        todo_list = [
            'property_account_creditor_price_difference_categ',
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
                }
                properties = env['ir.property'].search([
                    ('name', '=', record),
                    ('company_id', '=', company_id.id),
                ])
                if properties:
                    properties.write(vals)
                else:
                    # create the property
                    env['ir.property'].create(vals)
