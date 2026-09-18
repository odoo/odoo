from odoo import models


class AccountEdiXmlUblBis3(models.AbstractModel):
    _inherit = 'account.edi.xml.ubl_bis3'

    def _ubl_add_credit_note_type_code_node(self, vals):
        super()._ubl_add_credit_note_type_code_node(vals)
        invoice = vals.get('invoice')
        if invoice and invoice._l10n_fr_pdp_is_document_type_262():
            vals['document_node']['cbc:CreditNoteTypeCode']['_text'] = 262

    def _ubl_add_billing_reference_nodes(self, vals):
        invoice = vals.get('invoice')
        if invoice and invoice._l10n_fr_pdp_is_document_type_262():
            vals['document_node']['cac:BillingReference'] = []
            return
        super()._ubl_add_billing_reference_nodes(vals)

    def _add_invoice_header_nodes(self, document_node, vals):
        super()._add_invoice_header_nodes(document_node, vals)
        invoice = vals.get('invoice')
        if not invoice or not invoice._l10n_fr_pdp_is_document_type_262():
            return
        document_node.pop('cac:BillingReference', None)
        self._l10n_fr_pdp_add_262_header_nodes(document_node, invoice)

    def _l10n_fr_pdp_add_262_header_nodes(self, document_node, invoice):
        contract_ref = invoice._l10n_fr_pdp_get_contract_reference()
        if contract_ref:
            document_node['cac:ContractDocumentReference'] = {
                'cbc:ID': {'_text': contract_ref},
            }
        start, end = invoice._l10n_fr_pdp_get_invoicing_period()
        if start and end:
            document_node['cac:InvoicePeriod'] = {
                'cbc:StartDate': {'_text': start},
                'cbc:EndDate': {'_text': end},
            }
