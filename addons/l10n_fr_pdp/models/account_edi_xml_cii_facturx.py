from odoo import models


class AccountEdiXmlCII(models.AbstractModel):
    _inherit = "account.edi.xml.cii"

    def _import_attachments(self, invoice, tree):
        additional_docs = super()._import_attachments(invoice, tree)
        if invoice.company_id.country_code != "FR":
            return additional_docs
        return self._generate_pdf_attachment(invoice, additional_docs)

    def _get_exchanged_document_vals(self, invoice):
        # Extend `account_edi_xml_cii` to add mandatory default notes [BR-FR-05]
        result = super()._get_exchanged_document_vals(invoice)

        result['included_note_list'].extend([
            {
                'subject_code': code,
                'content': content,
            } for code, content in invoice._l10n_fr_pdp_get_default_notes().items()
        ])

        return result
