from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountJournal(models.Model):
    _inherit = "account.journal"

    l10n_latam_use_documents = fields.Boolean(
        string="Use Documents?",
        help="If active: will be using for legal invoicing (invoices, debit/credit notes)."
        " If not set means that will be used to register accounting entries not related to invoicing legal documents."
        " For Example: Receipts, Tax Payments, Register journal entries",
    )
    l10n_latam_company_use_documents = fields.Boolean(
        compute="_compute_l10n_latam_company_use_documents"
    )

    @api.depends("company_id")
    def _compute_l10n_latam_company_use_documents(self):
        for rec in self:
            rec.l10n_latam_company_use_documents = (
                rec.company_id._localization_use_documents()
            )

    @api.onchange("company_id", "type")
    def _onchange_company(self):
        self.l10n_latam_use_documents = (
            self.type in ["sale", "purchase"] and self.l10n_latam_company_use_documents
        )

    def _compute_has_sequence_holes(self):
        use_documents_journals = self.filtered(lambda j: j.l10n_latam_use_documents)
        use_documents_journals.has_sequence_holes = False
        if other_journals := self - use_documents_journals:
            super(AccountJournal, other_journals)._compute_has_sequence_holes()

    @api.constrains("l10n_latam_use_documents")
    def check_use_document(self):
        journals_with_posted_moves = {
            journal
            for [journal] in self.env["account.move"]._read_group(
                [("journal_id", "in", self.ids), ("posted_before", "=", True)],
                ["journal_id"],
            )
        }
        for rec in self:
            if rec in journals_with_posted_moves:
                raise ValidationError(
                    _(
                        'You can not modify the field "Use Documents?" if there are validated invoices in this journal!'
                    )
                )

    @api.depends("type", "l10n_latam_use_documents")
    def _compute_debit_sequence(self):
        super()._compute_debit_sequence()
        for journal in self:
            if journal.l10n_latam_use_documents:
                journal.debit_sequence = False

    @api.depends("type", "l10n_latam_use_documents")
    def _compute_refund_sequence(self):
        super()._compute_refund_sequence()
        for journal in self:
            if journal.l10n_latam_use_documents:
                journal.refund_sequence = False
