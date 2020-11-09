# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    def _prepare_journals(self, loaded_data):
        # OVERRIDE
        res = super()._prepare_journals(loaded_data)
        if self == self.env.ref('l10n_in.indian_chart_template_standard'):
            for journal_vals in res['sale'] + res['purchase']:
                journal_vals['l10n_in_gstin_partner_id'] = self.env.company.partner_id.id
            res['sale'][0]['name'] = _('Tax Invoices')
        return res


class AccountTaxTemplate(models.Model):
    _inherit = 'account.tax.template'

    l10n_in_reverse_charge = fields.Boolean("Reverse charge", help="Tick this if this tax is reverse charge. Only for Indian accounting")
