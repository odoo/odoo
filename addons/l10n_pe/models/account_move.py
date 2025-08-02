# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models, fields
from odoo.tools.sql import column_exists, create_column

PE_DOC_SUBTYPES = [
    ["l10n_pe.document_type01", "l10n_pe.document_type07", "l10n_pe.document_type08"],  # e-invoice
    ["l10n_pe.document_type02", "l10n_pe.document_type07b", "l10n_pe.document_type08b"],  # e-boleta
]


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_l10n_latam_documents_domain(self):
        self.ensure_one()
        result = super()._get_l10n_latam_documents_domain()
        if self.company_id.country_id.code != "PE" or not self.journal_id.l10n_latam_use_documents:
            return result
        original_move = self.reversed_entry_id or self.debit_origin_id
        if original_move:
            if self.debit_origin_id:
                result.append(("internal_type", "=", "debit_note"))
            doc_type = original_move.l10n_latam_document_type_id
            if doc_type:
                doc_type_xml_id = doc_type.get_external_id().get(doc_type.id)
                matching_subtype_ids = next(
                    (
                        [self.env.ref(sub_id).id for sub_id in group]
                        for group in PE_DOC_SUBTYPES
                        if doc_type_xml_id in group
                    ), []
                )
                if matching_subtype_ids:
                    result += [("id", "in", tuple(matching_subtype_ids))]
        if self.journal_id.type == "sale":
            result.append(("code", "in", ("01", "03", "07", "08", "20", "40")))
            if self.partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code != "6" and self.move_type == "out_invoice":
                doc_type_ids_RUC = [
                    self.env.ref(doc_type).id
                    for doc_type in ("l10n_pe.document_type08b", "l10n_pe.document_type02", "l10n_pe.document_type07b")
                ]
                result.append(("id", "in", doc_type_ids_RUC))
        return result

    @api.onchange('l10n_latam_document_type_id', 'l10n_latam_document_number', 'partner_id')
    def _inverse_l10n_latam_document_number(self):
        """Inherit to complete the l10n_latam_document_number with the expected 8 characters after that a '-'
        Example: Change FFF-32 by FFF-00000032, to avoid incorrect values on the reports"""
        super()._inverse_l10n_latam_document_number()
        to_review = self.filtered(
            lambda x: x.journal_id.type == "purchase"
            and x.l10n_latam_document_type_id.code in ("01", "03", "07", "08")
            and x.l10n_latam_document_number
            and "-" in x.l10n_latam_document_number
            and x.l10n_latam_document_type_id.country_id.code == "PE"
        )
        for rec in to_review:
            number = rec.l10n_latam_document_number.split("-")
            rec.l10n_latam_document_number = "%s-%s" % (number[0], number[1].zfill(8))


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    l10n_pe_group_id = fields.Many2one("account.group", related="account_id.group_id", store=True)

    def _auto_init(self):
        """
        Create column to stop ORM from computing it himself (too slow)
        """
        if not column_exists(self.env.cr, self._table, 'l10n_pe_group_id'):
            create_column(self.env.cr, self._table, 'l10n_pe_group_id', 'int4')
            self.env.cr.execute("""
                UPDATE account_move_line line
                SET l10n_pe_group_id = account.group_id
                FROM account_account account
                WHERE account.id = line.account_id
            """)
        return super()._auto_init()
