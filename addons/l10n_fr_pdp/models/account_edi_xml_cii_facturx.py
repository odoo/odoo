from odoo import models


class AccountEdiXmlCII(models.AbstractModel):
    _inherit = "account.edi.xml.cii"

    def _get_exchanged_document_vals(self, invoice):
        # Extend `account_edi_xml_cii` to add mandatory default notes [BR-FR-05]
        result = super()._get_exchanged_document_vals(invoice)

        result['included_note_list'].extend([
            {
                'subject_code': code,
                'content': content,
            } for code, content in invoice._l10n_fr_pdp_get_default_notes().items()
        ])
        if invoice._l10n_fr_pdp_is_document_type_262():
            result['type_code'] = '262'

        return result

    def _export_invoice_vals(self, invoice):
        vals = super()._export_invoice_vals(invoice)
        if not invoice._l10n_fr_pdp_is_document_type_262():
            return vals
        contract_ref = invoice._l10n_fr_pdp_get_contract_reference()
        if contract_ref:
            vals['contract_reference'] = contract_ref
        start, end = invoice._l10n_fr_pdp_get_invoicing_period()
        if start:
            vals['billing_start'] = start
        if end:
            vals['billing_end'] = end
        return vals
