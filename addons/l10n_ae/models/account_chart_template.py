# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, Command
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('ae', 'account.journal')
    def _get_ae_account_journal(self):
        """ If UAE chart, we add 2 new journals TA and IFRS"""
        return {
            "tax_adjustment":{
                "name": "Tax Adjustments",
                "code": "TA",
                "type": "general",
                "show_on_dashboard": True,
                "sequence": 1,
            },
            "ifrs16": {
                "name": "IFRS 16",
                "code": "IFRS",
                "type": "general",
                "show_on_dashboard": True,
                "sequence": 10,
            }
        }

    @template('ae', 'account.account')
    def _get_ae_account_account(self):
        return {
            "uae_account_100101": {
                'allowed_journal_ids': [Command.link('ifrs16')],
            },
            "uae_account_100102": {
                'allowed_journal_ids': [Command.link('ifrs16')],
            },
            "uae_account_400070": {
                'allowed_journal_ids': [Command.link('ifrs16')],
            },
        }
