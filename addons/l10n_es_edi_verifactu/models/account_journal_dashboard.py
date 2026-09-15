from odoo import models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def _fill_sale_purchase_dashboard_data(self, dashboard_data):
        super()._fill_sale_purchase_dashboard_data(dashboard_data)
        if self.company_id.l10n_es_edi_verifactu_required:
            for sale_journal in self.filtered(lambda j: j.type == 'sale'):
                verifactu_rejected = self.env['account.move'].search_count(
                    [('l10n_es_edi_verifactu_state', '=', 'rejected'), ('journal_id', '=', sale_journal.id)])
                dashboard_data[sale_journal.id].update({'vf_rejected': verifactu_rejected})
