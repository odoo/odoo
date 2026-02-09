from odoo import models


class AccountEdiXmlUBLBIS3(models.AbstractModel):
    _inherit = "account.edi.xml.ubl_bis3"

    def _can_export_selfbilling(self):
        # At the moment, self-billing is only supported for BIS3.
        return self._name == 'account.edi.xml.ubl_bis3'

    def _export_invoice_vals(self, invoice):
        # EXTENDS account.edi.xml.ubl_bis3
        vals = super()._export_invoice_vals(invoice)

        # For self-billing invoices, modify the customization_id, profile_id, and document_type_code
        if invoice.is_purchase_document() and self._can_export_selfbilling() and invoice.journal_id.is_self_billing:
            vals['vals'].update({
                'customization_id': self._get_selfbilling_customization_ids()['ubl_bis3'],
                'profile_id': 'urn:fdc:peppol.eu:2017:poacc:selfbilling:01:1.0',
            })

            # Set InvoiceTypeCode to 389 for invoices, CreditNoteTypeCode to 261 for credit notes
            if vals['document_type'] == 'invoice':
                vals['vals']['document_type_code'] = 389
            elif vals['document_type'] == 'credit_note':
                vals['vals']['document_type_code'] = 261

        return vals
