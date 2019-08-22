from odoo import models


class AccountChartTemplate(models.Model):

    _inherit = 'account.chart.template'

    def _prepare_all_journals(self, acc_template_ref, company, journals_dict=None):
        """ If Peruvian chart, we don't create sales journal as we need more data to create it properly """
        journals = super()._prepare_all_journals(acc_template_ref, company, journals_dict=journals_dict)
        if company.country_id == self.env.ref('base.pe'):
            for journal in journals:
                if journal['type'] == 'sale':
                    journal.update({'l10n_latam_use_documents': True})
        return journals
