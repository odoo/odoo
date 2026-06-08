# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

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

    @template(model='res.company')
    def _get_stock_res_company(self, template_code):
        return {
            self.env.company.id: {
                'account_stock_journal_id': 'inventory_valuation',
            },
        }
