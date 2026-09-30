# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models

# Let us match the document types to properly suggest the DN and CN documents
# NOTE: this can be avoided if we have an extra subclassification of UY documents
UY_DOC_SUBTYPES = [
    ["0"],  # not electronic
    ["101", "102", "103", "201", "202", "203"],  # e-ticket
    ["111", "112", "113", "211", "212", "213"],  # e-invoice
    ["121", "122", "123", "221", "222", "223"],  # e-inv-expo
    ["151", "152", "153", "251", "252", "253"],  # e-boleta (not implemented yet)
]


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_starting_sequence(self):
        """ If use documents then will create a new starting sequence using the document type code prefix and the
        journal document number with a 8 padding number """
        if self.l10n_latam_use_documents and self.company_id.account_fiscal_country_id.code == "UY" and self.l10n_latam_document_type_id:
            return self._l10n_uy_get_formatted_sequence()
        return super()._get_starting_sequence()

    def _l10n_uy_get_formatted_sequence(self, number=0):
        return "%s A%07d" % (self.l10n_latam_document_type_id.doc_code_prefix, number)

    def _get_last_sequence_domain(self, relaxed=False):
        where_string, param = super(AccountMove, self)._get_last_sequence_domain(relaxed)
        if self.company_id.account_fiscal_country_id.code == "UY" and self.l10n_latam_use_documents:
            where_string += " AND l10n_latam_document_type_id = %(l10n_latam_document_type_id)s"
            param['l10n_latam_document_type_id'] = self.l10n_latam_document_type_id.id or 0
        return where_string, param

    def _get_l10n_latam_documents_domain(self):
        """ If this is a reversal or debit, suggest only related subtypes """
        self.ensure_one()
        domain = super()._get_l10n_latam_documents_domain()
        if self.country_code == "UY" and (original_move := self.reversed_entry_id or self.debit_origin_id):
            matching_subtype_codes = [
                subtype for subtype in UY_DOC_SUBTYPES
                if original_move.l10n_latam_document_type_id.code in subtype
            ]
            if matching_subtype_codes:
                # restrict to the codes from the subtype matching the one of the original_move (e.g. 'e-ticket')
                codes = self.env["l10n_latam.document.type"].search(domain).mapped('code')
                allowed_codes = set(codes).intersection(set(matching_subtype_codes[0]))
                domain += [("code", "in", tuple(allowed_codes))]
        return domain
