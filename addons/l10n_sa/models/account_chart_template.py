# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, Command
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('sa', 'account.journal')
    def _get_sa_account_journal(self):
        """ If Saudi Arabia chart, we add 3 new journals Tax Adjustments, IFRS 16 and Zakat"""
        return {
            "tax_adjustment": {
                'name': 'Tax Adjustments',
                'code': 'TA',
                'type': 'general',
                'show_on_dashboard': True,
                'sequence': 1,
            },
            "ifrs16": {
                'name': 'IFRS 16 Right of Use Asset',
                'code': 'IFRS',
                'type': 'general',
                'show_on_dashboard': True,
                'sequence': 10,
            },
            "zakat": {
                'name': 'Zakat',
                'code': 'ZAKAT',
                'type': 'general',
                'show_on_dashboard': True,
                'sequence': 10,
            }
        }

    @template('sa', 'account.account')
    def _get_sa_account_account(self):
        return {
            "sa_account_100101": {'allowed_journal_ids': [Command.link('ifrs16')]},
            "sa_account_100102": {'allowed_journal_ids': [Command.link('ifrs16')]},
            "sa_account_400070": {'allowed_journal_ids': [Command.link('ifrs16')]},
            "sa_account_201019": {'allowed_journal_ids': [Command.link('zakat')]},
            "sa_account_400072": {'allowed_journal_ids': [Command.link('zakat')]},
        }
