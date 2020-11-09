# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api, fields, _


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    def _prepare_journals(self, loaded_data):
        # OVERRIDE
        res = super()._prepare_journals(loaded_data)
        if self.env.company._localization_use_documents():
            for journal_vals in res['sale'] + res['purchase']:
                journal_vals['l10n_latam_use_documents'] = True
        return res
