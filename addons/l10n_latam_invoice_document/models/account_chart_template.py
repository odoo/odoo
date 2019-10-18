# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api, fields, _


class AccountChartTemplate(models.Model):

    _inherit = 'account.chart.template'

    @api.model
    def _prepare_all_journals(self, acc_template_ref, company, journals_dict=None):
        """ We add use_documents or not depending on the context"""
        journal_data = super()._prepare_all_journals(acc_template_ref, company, journals_dict)

        # if chart has localization, then we use documents by default
        if company._localization_use_documents():
            for vals_journal in journal_data:
                if vals_journal['type'] in ['sale', 'purchase']:
                    vals_journal['l10n_latam_use_documents'] = True
        return journal_data
