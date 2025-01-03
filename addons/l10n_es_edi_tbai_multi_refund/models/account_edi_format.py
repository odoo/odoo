from odoo import models


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    def _l10n_es_tbai_get_in_invoice_values_batuz(self, invoice):
        values = super()._l10n_es_tbai_get_in_invoice_values_batuz(invoice)
        credit_notes = values.pop('credit_note_invoice', self.env['account.move']) | invoice.l10n_es_tbai_reversed_ids
        if credit_notes:
            values['credit_note_invoices'] = credit_notes
        return values
