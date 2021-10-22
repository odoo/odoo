# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @template('kz', 'account.journal')
    def _get_kz_account_journal(self):
        return {
            'cash': {'default_account_id': 'kz1010'},
            'bank': {'default_account_id': 'kz1030'},
        }
