# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models

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
            # We will support it soon, but not now. So we put the bases for it, but it won't be available to use yet.
            # consolidation_type will never be 'invoice' unless custom code/actions are used.
            raise NotImplementedError('Support for consolidated invoices in the invoicing app is not yet implemented.')
