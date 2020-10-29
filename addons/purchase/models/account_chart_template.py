# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _

import logging
_logger = logging.getLogger(__name__)


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"


    @api.multi
    def generate_properties(self, acc_template_ref, company, property_list=None):
        res = super(AccountChartTemplate, self).generate_properties(acc_template_ref=acc_template_ref, company=company)
        PropertyObj = self.env['ir.property']  # Property Stock Journal

        todo_list = [  # Property Stock Accounts
            'property_account_creditor_price_difference_categ',
        ]
        for record in todo_list:
            account = getattr(self, record)
            value = account and 'account.account,' + str(acc_template_ref[account.id]) or False
            if value:
                field = self.env['ir.model.fields'].search([('name', '=', record), ('model', '=', 'product.category'), ('relation', '=', 'account.account')], limit=1)
                vals = {
                    'name': record,
                    'company_id': company.id,
                    'fields_id': field.id,
                    'value': value,
                }
                properties = PropertyObj.search([('name', '=', record), ('company_id', '=', company.id)], limit=1)
                if not properties:
                    # create the property
                    PropertyObj.create(vals)
                elif not properties.value_reference:
                    # update the property if False
                    properties.write(vals)

        return res
