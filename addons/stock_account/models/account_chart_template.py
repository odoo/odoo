# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    def _get_stock_account_res_company(self, template_code):
        return {
            company_id: filtered_vals
            for company_id, vals in self._get_chart_template_model_data(template_code, 'res.company').items()
            if (filtered_vals := {
                fname: value
                for fname, value in vals.items()
                if fname in [
                    'account_stock_journal_id',
                    'account_stock_valuation_id',
                    'account_production_wip_account_id',
                    'account_production_wip_overhead_account_id',
                ]
            })
        }

    def _get_stock_account_account(self, template_code):
        return {
            xmlid: filtered_vals
            for xmlid, vals in self._get_chart_template_model_data(template_code, 'account.account').items()
            if (filtered_vals := {
                fname: value
                for fname, value in vals.items()
                if fname in ['account_stock_expense_id', 'account_stock_variation_id']
            })
        }

    @template(model='account.journal')
    def _get_stock_account_journal(self, template_code):
        return {
            'inventory_valuation': {
                'name': _('Inventory Valuation'),
                'code': 'STJ',
                'type': 'general',
                'sequence': 10,
                'show_on_dashboard': False,
            },
        }

    @template()
    def _get_stock_template_data(self, template_code):
        return {
            'stock_journal': 'inventory_valuation',
        }
