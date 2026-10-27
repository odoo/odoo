# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('it', 'account.account')
    def _get_it_withholding_account_account(self):
        return self._parse_csv('it', 'account.account', module='l10n_it_edi_withholding')

    @template('it', 'account.tax')
    def _get_it_withholding_account_tax(self):
        additionnal = self._parse_csv('it', 'account.tax', module='l10n_it_edi_withholding')
        self._deref_account_tags('it', additionnal)
        return additionnal

    @template('it', 'account.tax.group')
    def _get_it_withholding_account_tax_group(self):
        return self._parse_csv('it', 'account.tax.group', module='l10n_it_edi_withholding')
