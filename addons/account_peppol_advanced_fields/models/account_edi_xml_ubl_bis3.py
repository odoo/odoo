from odoo import models


class AccountEdiXmlUbl_Bis3(models.AbstractModel):
    _inherit = 'account.edi.xml.ubl_bis3'

    def _add_invoice_header_nodes(self, document_node, vals):
        super()._add_invoice_header_nodes(document_node, vals)
        invoice = vals['invoice']
        if invoice.peppol_contract_document_reference:
            document_node['cac:ContractDocumentReference'] = {'cbc:ID': {'_text': invoice.peppol_contract_document_reference}}
        if invoice.peppol_originator_document_reference:
            document_node['cac:OriginatorDocumentReference'] = {'cbc:ID': {'_text': invoice.peppol_originator_document_reference}}
        if invoice.peppol_despatch_document_reference:
            document_node['cac:DespatchDocumentReference'] = {'cbc:ID': {'_text': invoice.peppol_despatch_document_reference}}
        if invoice.peppol_additional_document_reference:
            document_node['cac:AdditionalDocumentReference'] = {'cbc:ID': {'_text': invoice.peppol_additional_document_reference}}
        if invoice.peppol_accounting_cost:
            document_node['cbc:AccountingCost'] = {'_text': invoice.peppol_accounting_cost}
        if vals['document_type'] == 'invoice' and invoice.peppol_project_reference:
            # ProjectReference only exists in Invoice
            document_node['cac:ProjectReference'] = {'cbc:ID': {'_text': invoice.peppol_project_reference}}

    def _add_invoice_delivery_nodes(self, document_node, vals):
        super()._add_invoice_delivery_nodes(document_node, vals)
        invoice = vals['invoice']
        if invoice.peppol_delivery_location_id and 'cac:Delivery' in document_node:
            document_node['cac:Delivery']['cac:DeliveryLocation']['cbc:ID'] = {
                '_text': invoice.peppol_delivery_location_id,
                'schemeID': '0088',
            }
