from odoo import models


class AccountEdiXmlUbl_Bis3(models.AbstractModel):
    _inherit = 'account.edi.xml.ubl_bis3'

    def _import_fill_invoice(self, invoice, tree, qty_factor):
        # EXTEND account_edi_ubl_cii
        logs = super()._import_fill_invoice(invoice, tree, qty_factor)

        vals = dict()
        if contract_document_reference := tree.findtext('./{*}ContractDocumentReference/{*}ID'):
            vals['peppol_contract_document_reference'] = contract_document_reference
        if originator_document_reference := tree.findtext('./{*}OriginatorDocumentReference/{*}ID'):
            vals['peppol_originator_document_reference'] = originator_document_reference
        if despatch_document_reference := tree.findtext('./{*}DespatchDocumentReference/{*}ID'):
            vals['peppol_despatch_document_reference'] = despatch_document_reference
        if additional_document_reference := tree.findtext('./{*}AdditionalDocumentReference/{*}ID'):
            vals['peppol_additional_document_reference'] = additional_document_reference
        if accounting_cost := tree.findtext('./{*}AccountingCost'):
            vals['peppol_accounting_cost'] = accounting_cost
        if project_reference := tree.findtext('./{*}ProjectReference/{*}ID'):
            vals['peppol_project_reference'] = project_reference
        if delivery_location := tree.findtext('./{*}Delivery/{*}DeliveryLocation/{*}ID'):
            vals['peppol_delivery_location_id'] = delivery_location

        if vals:
            invoice.write(vals)

        return logs
