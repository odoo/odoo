from odoo import models


class AccountEdiXmlUBLBIS3(models.AbstractModel):
    _inherit = "account.edi.xml.ubl_bis3"

    def _can_export_selfbilling(self):
        # At the moment, self-billing is only supported for BIS3.
        return self._name == 'account.edi.xml.ubl_bis3'

    def _add_invoice_header_nodes(self, document_node, vals):
        super()._add_invoice_header_nodes(document_node, vals)
        if vals['invoice'].journal_id.is_self_billing:
            document_node['cbc:CustomizationID'] = {'_text': self._get_selfbilling_customization_ids()['ubl_bis3']}
            document_node['cbc:ProfileID'] = {'_text': 'urn:fdc:peppol.eu:2017:poacc:selfbilling:01:1.0'}

            if vals['document_type'] == 'invoice':
                document_node['cbc:InvoiceTypeCode'] = {'_text': 389}
            elif vals['document_type'] == 'credit_note':
                document_node['cbc:CreditNoteTypeCode'] = {'_text': 261}

    def _add_invoice_config_vals(self, vals):
        # EXTENDS account.edi.ubl_bis3
        vals['process_type'] = 'selfbilling' if vals['invoice'].is_purchase_document() and self._can_export_selfbilling() else 'billing'
        super()._add_invoice_config_vals(vals)
        if vals['process_type'] != 'selfbilling':
            return

        customer = vals['customer']
        supplier = vals['supplier']
        vals['supplier'] = customer
        vals['customer'] = supplier
        vals['delivery'] = supplier
