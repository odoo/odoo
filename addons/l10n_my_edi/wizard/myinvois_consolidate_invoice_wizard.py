# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.tools import split_every

MAX_LINE_COUNT_PER_INVOICE = 100


class MyInvoisConsolidateInvoiceWizard(models.TransientModel):
    _name = 'myinvois.consolidate.invoice.wizard'
    _description = 'Consolidate Invoice Wizard'

    # ------------------
    # Fields declaration
    # ------------------

    date_from = fields.Date(
        string='Date From',
        required=True,
    )
    date_to = fields.Date(
        string='Date To',
        required=True,
    )
    consolidation_type = fields.Selection(
        selection=[
            ('invoice', 'Invoice'),
        ],
        required=True,
    )

    # --------------
    # Action methods
    # --------------

    def button_consolidate(self):
        """
        By default, we only consolidated orders that are in the range, done and not invoiced.
        We do allow to also consolidate invoices linked to a cancelled consolidated invoice.

        Note that doing so lock the cancelled invoice into its cancelled state.
        """
        self.ensure_one()
        myinvois_document_vals = self._get_myinvois_document_vals()
        if myinvois_document_vals:
            myinvois_documents = self.env["myinvois.document"].create(myinvois_document_vals)
            return myinvois_documents.action_show_myinvois_documents()
        return False

    # ----------------
    # Business methods
    # ----------------

    def _get_myinvois_document_vals(self):
        """
        Prepare and return a list of dicts containing the values needed to create the consolidated invoices for the
        records inbetween the provided dates.
        :return: A list of dicts used to create the consolidated invoices.
        """
        self.ensure_one()
        if self.consolidation_type == 'invoice':
            journal_id = self.env.context.get('journal_id')
            journal = self.env['account.journal'].browse(journal_id)
            domain = Domain([
                ("state", "=", "posted"),
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to),
                '|',
                ('l10n_my_edi_document_ids', '=', False),
                ('l10n_my_edi_document_ids', 'not any', [('myinvois_state', '!=', 'cancelled')])
            ])

            # Add partner filter. We only pick partners that are marked as General Public via their TIN, or that do not have any tax information set.
            partner_domain = self.env['myinvois.document']._myinvois_get_consolidated_invoice_partner_domain()
            domain &= partner_domain

            if journal_id:
                domain &= Domain('journal_id', '=', journal.id)
                if journal.type == 'sale':
                    domain &= Domain('move_type', 'in', ('out_invoice', 'out_refund'))
                elif journal.type == 'purchase':
                    domain &= Domain('move_type', 'in', ('in_invoice', 'in_refund'))

            moves_to_consolidate = self.env['account.move'].search(domain)
            if not moves_to_consolidate:
                raise ValidationError(self.env._('Invalid Operation. No invoices to consolidate.'))

            uses_debit_note = self.env['myinvois.document']._myinvois_is_debit_notes_used()

            # We start by preparing the consolidated invoice(s), taking only the invoices and vendor bills.
            consolidated_invoice_vals = []
            invoices_to_consolidate = moves_to_consolidate.filtered(lambda m: m.move_type in ('out_invoice', 'in_invoice') and (not uses_debit_note or not m.debit_origin_id))
            self._get_myinvois_consolidated_invoice_vals(invoices_to_consolidate, consolidated_invoice_vals)
            # Next, we will take all credit notes and prepare additional consolidated invoices with them.
            # We need to differentiate refunds from regular credit notes to be able to set the correct type later on.
            credit_notes_to_consolidate = moves_to_consolidate.filtered(lambda m: m.move_type in ('out_refund', 'in_refund'))
            self._get_myinvois_consolidated_invoice_vals(  # Regular credit notes
                credit_notes_to_consolidate.filtered(lambda m: not self.env['account.edi.xml.ubl_myinvois_my']._l10n_my_edi_get_refund_details(m)[0]),
                consolidated_invoice_vals,
            )
            self._get_myinvois_consolidated_invoice_vals(  # Refunds
                credit_notes_to_consolidate.filtered(lambda m: self.env['account.edi.xml.ubl_myinvois_my']._l10n_my_edi_get_refund_details(m)[0]),
                consolidated_invoice_vals,
            )
            # Lastly, we repeat the same process but for debit notes.
            debit_notes_to_consolidate = moves_to_consolidate.filtered(lambda m: m.move_type in ('out_invoice', 'in_invoice') and uses_debit_note and m.debit_origin_id)
            self._get_myinvois_consolidated_invoice_vals(debit_notes_to_consolidate, consolidated_invoice_vals)
            return consolidated_invoice_vals
        return None

    def _get_myinvois_consolidated_invoice_vals(self, invoices_to_consolidate, consolidated_invoice_vals):
        # We want to create the documents by grouping invoices by currencies and journals.
        # We will first group by currencies, split the invoices for a same currency in lines for each journal
        # Then finally create the documents.
        for currency, invoices_to_consolidate_in_currency in invoices_to_consolidate.grouped("currency_id").items():
            lines_per_journal_prefix = self.env["myinvois.document"]._split_invoices_in_lines(invoices_to_consolidate_in_currency)

            # We now know the amount of lines; we want to create one consolidated invoice per 100 lines.
            for (journal, prefix), lines in lines_per_journal_prefix.items():
                for line_batch in split_every(MAX_LINE_COUNT_PER_INVOICE, lines, list):
                    invoices = self.env["account.move"].union(*line_batch)
                    consolidated_invoice_vals.append({
                        "invoice_ids": [Command.set(invoices.ids)],
                        "company_id": journal.company_id.id,
                        "currency_id": currency.id,
                        "is_consolidated_invoice": True,
                        "move_type": invoices[0].move_type,
                        "journal_id": journal.id,
                        "is_debit_note": self.env['myinvois.document']._myinvois_is_debit_notes_used() and bool(invoices[0].debit_origin_id),
                    })
