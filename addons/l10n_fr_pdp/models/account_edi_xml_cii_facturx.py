from odoo import models

from odoo.addons.l10n_fr_pdp.models.legal_notes import coded_note_codes


class AccountEdiXmlCII(models.AbstractModel):
    _inherit = "account.edi.xml.cii"

    def _get_exchanged_document_vals(self, invoice):
        # Extend `account_edi_xml_cii` to add mandatory default notes [BR-FR-05].
        # [BR-FR-06] a subject already present in the narration is not repeated.
        result = super()._get_exchanged_document_vals(invoice)
        seen = set(coded_note_codes(result.get('included_note')))
        deduped = []
        for note in result.get('included_note_list') or []:
            code = note.get('subject_code')
            if code and code in seen:
                continue
            if code:
                seen.add(code)
            seen.update(coded_note_codes(note.get('content')))
            deduped.append(note)
        for code, content in invoice._l10n_fr_pdp_get_default_notes().items():
            if code in seen:
                continue
            seen.add(code)
            deduped.append({
                'subject_code': code,
                'content': content,
            })
        result['included_note_list'] = deduped
        return result
