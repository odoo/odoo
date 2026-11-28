from odoo import api, fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    l10n_tr_einvoice_sequence_ids = fields.One2many(
        comodel_name='l10n_tr_edi.invoice.sequence',
        inverse_name='journal_id',
        string="e-Document Sequences",
        help="Use a different invoice series depending on the characteristics of the invoice. "
             "The first series whose conditions all match replaces the journal code in the invoice number.",
    )

    @api.depends('country_code', 'company_id.l10n_tr_edi_provider')
    def _compute_show_refresh_out_einvoices_status_button(self):
        # EXTENDS 'account'
        super()._compute_show_refresh_out_einvoices_status_button()
        self.filtered(lambda j: j._l10n_tr_edi_is_exchanging() and j.type == 'sale').show_refresh_out_einvoices_status_button = True

    def button_fetch_in_einvoices(self):
        # EXTENDS 'account'
        super().button_fetch_in_einvoices()
        if any(journal._l10n_tr_edi_is_exchanging() for journal in self):
            self.env['account.move']._cron_l10n_tr_edi_fetch_einvoice_purchase_documents()

    def button_refresh_out_einvoices_status(self):
        # EXTENDS 'account'
        super().button_refresh_out_einvoices_status()
        if any(journal._l10n_tr_edi_is_exchanging() for journal in self):
            self.env['account.move']._cron_l10n_tr_edi_fetch_status()

    def _l10n_tr_edi_is_exchanging(self):
        """Return whether this journal's company exchanges e-Documents with the GİB, through a provider."""
        self.ensure_one()
        return self.country_code == 'TR' and bool(self.company_id.l10n_tr_edi_provider)
