# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _

import logging
_logger = logging.getLogger(__name__)


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    def _get_account_journal(self, template_code, company):
        cid = (company or self.env.company).id
        return {
            **(super()._get_account_journal(template_code, company)),
            f'{cid}_inventory_valuation': {
                'name': _('Inventory Valuation'),
                "company_id": cid,
                'code': 'STJ',
                'type': 'general',
                'sequence': 8,
                'show_on_dashboard': False,
            },
        }

    def _get_template_data(self, template_code, company):
        cid = (company or self.env.company).id
        return {
            **(super()._get_template_data(template_code, company)),
            'property_stock_journal':                 f'account.{cid}_inventory_valuation',
            'property_stock_account_input_categ_id':  f'account.{cid}_stock_in',
            'property_stock_account_output_categ_id': f'account.{cid}_stock_out',
            'property_stock_valuation_account_id':    f'account.{cid}_stock_valuation',
        }
