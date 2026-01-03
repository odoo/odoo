# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models

PE_DOC_SUBTYPES = [
    ("l10n_pe.document_type01", "l10n_pe.document_type07", "l10n_pe.document_type08"),  # e-invoice
    ("l10n_pe.document_type02", "l10n_pe.document_type07b", "l10n_pe.document_type08b"),  # e-boleta
]


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_l10n_latam_documents_domain(self):
        self.ensure_one()
        result = super()._get_l10n_latam_documents_domain()
        if self.company_id.country_id.code != "PE" or not self.l10n_latam_use_documents or self.journal_id.type != "sale":
            return result
        if self.debit_origin_id:
            result.append(("internal_type", "=", "debit_note"))
        if (original_move := self.reversed_entry_id or self.debit_origin_id) and (doc_type := original_move.l10n_latam_document_type_id):
            doc_type_xml_id = doc_type.get_external_id().get(doc_type.id)
            for doc_subtype_group in PE_DOC_SUBTYPES:
                if doc_type_xml_id in doc_subtype_group:
                    doc_subtype_group_ids = tuple(self.env.ref(type).id for type in doc_subtype_group)
                    result.append(("id", "in", doc_subtype_group_ids))
                    break
        result.append(("code", "in", ("01", "03", "07", "08", "20", "40")))
        if self.partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code != '6' and self.move_type == 'out_invoice':
            result.append(('id', 'in', (
                self.env.ref('l10n_pe.document_type08b')
                | self.env.ref('l10n_pe.document_type02')
                | self.env.ref('l10n_pe.document_type07b')
            ).ids))
        return result

    @api.onchange('l10n_latam_document_type_id', 'l10n_latam_document_number', 'partner_id')
    def _inverse_l10n_latam_document_number(self):
        """Inherit to complete the l10n_latam_document_number with the expected 8 characters after that a '-'

        After formatting the document number with zfill(8), the name field is also synchronized
        to ensure both fields remain consistent.

        Example: Change F01-32 by F01-00000032, to avoid incorrect values on the reports
        """
        super()._inverse_l10n_latam_document_number()
        to_review = self.filtered(
            lambda x: x.journal_id.type == "purchase"
            and x.l10n_latam_document_type_id
            and x.l10n_latam_document_type_id.code in ("01", "03", "07", "08")
            and x.l10n_latam_document_number
            and "-" in x.l10n_latam_document_number
            and x.l10n_latam_document_type_id.country_id.code == "PE"
        )
        for rec in to_review:
            number = rec.l10n_latam_document_number.split("-")
            rec.l10n_latam_document_number = "%s-%s" % (number[0], number[1].zfill(8))

            # Synchronize the name field with the formatted document number
            # to ensure consistency between l10n_latam_document_number and name fields
            expected_name = (
                f"{rec.l10n_latam_document_type_id.doc_code_prefix} "
                f"{rec.l10n_latam_document_number}"
            )
            if rec.name != expected_name:
                rec.name = expected_name
