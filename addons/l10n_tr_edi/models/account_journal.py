from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    l10n_tr_einvoice_sequence_ids = fields.One2many(
        comodel_name='l10n_tr_nilvera_einvoice.invoice.sequence',
        inverse_name='journal_id',
        string="e-Document Sequences",
        help="Use a different invoice series depending on the characteristics of the invoice. "
             "The first series whose conditions all match replaces the journal code in the invoice number.",
    )
