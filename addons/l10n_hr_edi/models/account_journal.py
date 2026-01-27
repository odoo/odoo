from odoo import api, fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    l10n_hr_business_premises_label = fields.Char(
        string="Business premises label",
        default='1',
        required=True,
        size=20,
        help="Must contain at least one character and a maximum of 20 numeric (0-9) and/or alphabetic (a-z, A-Z) characters.",
    )
    l10n_hr_issuing_device_label = fields.Char(
        string="Issuing device label",
        default='1',
        required=True,
        help="Must contain only numeric characters",
    )
    l10n_hr_business_premises_label_refund = fields.Char(
        string="Business premises label (refund approval)",
        default='1',
        required=True,
        size=20,
        help="Must contain at least one character and a maximum of 20 numeric (0-9) and/or alphabetic (a-z, A-Z) characters.",
    )
    l10n_hr_issuing_device_label_refund = fields.Char(
        string="Issuing device label (refund approval)",
        default='2',
        required=True,
        help="Must contain only numeric characters",
    )
    # MER-specific fields
    l10n_hr_mer_connection_state = fields.Selection(related='company_id.l10n_hr_mer_connection_state')
    l10n_hr_is_mer_journal = fields.Boolean(string='Journal used for eRacun via MojEracun', compute='_compute_l10n_hr_is_mer_journal')

    @api.depends('company_id.l10n_hr_mer_purchase_journal_id')
    def _compute_l10n_hr_is_mer_journal(self):
        for journal in self:
            journal.l10n_hr_is_mer_journal = journal.company_id.l10n_hr_mer_purchase_journal_id == journal

    def l10n_hr_mer_get_new_documents(self):
        self.company_id._l10n_hr_mer_get_new_documents(undelivered_only=True)

    def l10n_hr_mer_get_new_documents_all(self):
        self.company_id._l10n_hr_mer_get_new_documents(undelivered_only=False)

    def l10n_hr_mer_get_message_status(self):
        self.company_id._l10n_hr_mer_fetch_document_status_company()
