# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template(model='account.journal')
    def _get_latam_document_account_journal(self, template_code):
        """ We add use_documents or not depending on the context"""
        if self.env.company._localization_use_documents():
            return {
                'sale': {'l10n_latam_use_documents': True},
                'purchase': {'l10n_latam_use_documents': True},
            }
