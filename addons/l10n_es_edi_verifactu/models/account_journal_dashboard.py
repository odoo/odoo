from odoo import models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def _fill_sale_purchase_dashboard_data(self, dashboard_data):
        super()._fill_sale_purchase_dashboard_data(dashboard_data)
        if self.company_id.l10n_es_edi_verifactu_required:
            sale_journals = self.filtered(lambda j: j.type == 'sale')
            rejected_count_by_journal = {
                journal.id: count
                for journal, count in self.env['account.move']._read_group(
                    domain=[
                        ('l10n_es_edi_verifactu_state', 'in', ('rejected', 'invalid')),
                        ('journal_id', 'in', sale_journals.ids),
                    ],
                    groupby=['journal_id'],
                    aggregates=['__count'],
                )
            }
            for sale_journal in sale_journals:
                dashboard_data[sale_journal.id].update({
                    'vf_rejected': rejected_count_by_journal.get(sale_journal.id, 0),
                })
